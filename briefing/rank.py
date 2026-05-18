"""Two-pass ranker on a ≤32B open-weight model via HF Inference Providers.

Pass 1: cheap relevance filter — for each item, "is this AI news worth a
        senior engineer's two minutes?" Yes/no.
Pass 2: structured 0-10 ranking on the survivors. Surfaces the top items.

The down-port story for Build Small: the production ai-news-agent runs a
single 70B-Groq scoring pass over the full batch. That works but it spends
70B-class budget on items that are obviously noise (HN posts about
non-AI scams that hit the AI keyword set). At 32B we split the work — a
cheap binary filter first to drop obvious junk, then a graded score on the
real candidates. Same end signal, half the prompt tokens at the expensive
step.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import httpx

from briefing.config import DEFAULT_BASE_URL, DEFAULT_MODEL, MIN_RELEVANCE


# ---------------------------------------------------------------------------
# Provider client
# ---------------------------------------------------------------------------


@dataclass
class RankerConfig:
    base_url: str = DEFAULT_BASE_URL
    model:    str = DEFAULT_MODEL
    api_key:  str = ""           # populated from HF_TOKEN at call time if blank
    timeout:  float = 90.0


def _client(cfg: RankerConfig) -> httpx.Client:
    api_key = cfg.api_key or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN", "")
    if not api_key:
        raise RuntimeError(
            "HF_TOKEN missing — set it in the environment or pass api_key= explicitly."
        )
    return httpx.Client(
        base_url=cfg.base_url,
        timeout=cfg.timeout,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )


def _chat(cfg: RankerConfig, system: str, user: str, *, json_mode: bool = True,
          temperature: float = 0.2, max_tokens: int = 4000) -> str:
    payload = {
        "model":       cfg.model,
        "messages":    [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    with _client(cfg) as cli:
        r = cli.post("/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Pass 1 — binary relevance filter
# ---------------------------------------------------------------------------


_FILTER_SYSTEM = "You are a precise JSON-only classifier. No prose."


_FILTER_PROMPT = """You are pre-filtering items for a 2-hour AI-news briefing for a senior AI engineer.

Mark each item KEEP if it is AI/ML news that a senior engineer would care about (model releases, capability shifts, key research, important industry moves, notable benchmarks, infrastructure changes). Mark DROP if it is noise, off-topic, hype-with-no-substance, repeat news from earlier today, or non-AI items.

Return JSON only:
  {{"verdicts": [{{"i": 0, "v": "KEEP"}}, {{"i": 1, "v": "DROP"}}, ...]}}

Items:
{items_json}
"""


def filter_relevant(items: list[dict], cfg: RankerConfig | None = None) -> list[dict]:
    """Pass 1 — drop obvious noise. Returns items that survived."""
    if not items:
        return []
    cfg = cfg or RankerConfig()
    indexed = [
        {"i": i, "source": it.get("source", ""), "title": (it.get("title") or "")[:200]}
        for i, it in enumerate(items)
    ]
    raw = _chat(
        cfg,
        _FILTER_SYSTEM,
        _FILTER_PROMPT.format(items_json=json.dumps(indexed, ensure_ascii=False)),
    )
    try:
        data = json.loads(raw)
        keep = {entry["i"] for entry in data.get("verdicts", []) if entry.get("v") == "KEEP"}
    except Exception as e:
        print(f"[filter] parse failed, keeping all: {e}")
        keep = set(range(len(items)))
    return [items[i] for i in range(len(items)) if i in keep]


# ---------------------------------------------------------------------------
# Pass 2 — graded ranker
# ---------------------------------------------------------------------------


_RANKER_SYSTEM = "You are a precise JSON-only scorer. No prose."


_RANKER_PROMPT = """You are an AI-news editor scoring items for a 2-hour briefing for a senior AI engineer.

Score each item 0-10 on importance and novelty. High scores (8-10) = major model releases, significant research breakthroughs, capability shifts, key industry moves, notable benchmarks. Medium (5-7) = relevant but smaller updates, useful tools, interesting research. Low (0-4) = noise, hype with no substance, repackaged news, off-topic.

Return JSON only:
  {{"scores": [{{"i": 0, "score": 8, "reason": "short why"}}, ...]}}

Items:
{items_json}
"""


def rank_items(items: list[dict], cfg: RankerConfig | None = None) -> list[dict]:
    """Pass 2 — graded score 0-10. Items below MIN_RELEVANCE are dropped.

    Returns sorted descending by score, each item gets a `score` and
    `reason` field added.
    """
    if not items:
        return []
    cfg = cfg or RankerConfig()
    indexed = [
        {"i": i, "source": it.get("source", ""), "title": (it.get("title") or "")[:200]}
        for i, it in enumerate(items)
    ]
    raw = _chat(
        cfg,
        _RANKER_SYSTEM,
        _RANKER_PROMPT.format(items_json=json.dumps(indexed, ensure_ascii=False)),
    )
    try:
        data = json.loads(raw)
        score_map = {entry["i"]: (int(entry["score"]), entry.get("reason", ""))
                     for entry in data.get("scores", [])}
    except Exception as e:
        print(f"[rank] parse failed, defaulting all to 5: {e}")
        score_map = {i: (5, "parse error") for i in range(len(items))}

    out: list[dict] = []
    for i, item in enumerate(items):
        score, reason = score_map.get(i, (5, ""))
        if score < MIN_RELEVANCE:
            continue
        out.append({**item, "score": score, "reason": reason})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Combined pipeline
# ---------------------------------------------------------------------------


@dataclass
class RankResult:
    raw_count:      int
    after_filter:   int
    after_rank:     int
    items:          list[dict]
    filter_latency: float
    rank_latency:   float


def rank_pipeline(items: list[dict], cfg: RankerConfig | None = None) -> RankResult:
    """Filter then rank. Returns the surviving items plus per-stage latency."""
    cfg = cfg or RankerConfig()
    t0 = time.perf_counter()
    filtered = filter_relevant(items, cfg)
    t1 = time.perf_counter()
    ranked = rank_items(filtered, cfg)
    t2 = time.perf_counter()
    return RankResult(
        raw_count=      len(items),
        after_filter=   len(filtered),
        after_rank=     len(ranked),
        items=          ranked,
        filter_latency= t1 - t0,
        rank_latency=   t2 - t1,
    )
