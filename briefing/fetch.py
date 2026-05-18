"""Fetchers — RSS, Hacker News, ArXiv, GitHub.

All return a uniform `Item` shape so the ranker doesn't care about origin:
    {source, title, url, summary, published_ts}

Ported from `~/ai-news-agent/sources/` with two changes:
  1. No external config.py import — everything lives in briefing.config
  2. Reddit + Bluesky removed (both 403-block public traffic in 2026)
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Iterable
from xml.etree import ElementTree as ET

import feedparser
import httpx

from briefing.config import (
    ARXIV_CATEGORIES,
    GITHUB_TRENDING_TOPIC,
    PER_SOURCE_CAP,
    RSS_FEEDS,
)


# ---------------------------------------------------------------------------
# RSS / Atom
# ---------------------------------------------------------------------------


def fetch_rss(since_ts: float, feeds: Iterable[tuple[str, str]] = RSS_FEEDS) -> list[dict]:
    items: list[dict] = []
    for label, url in feeds:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[rss] {label} failed: {e}")
            continue
        for entry in feed.entries[:PER_SOURCE_CAP]:
            published = _entry_time(entry)
            if published and published < since_ts:
                continue
            items.append(
                {
                    "source":       f"rss:{label}",
                    "title":        (entry.get("title") or "").strip(),
                    "url":          entry.get("link") or "",
                    "summary":      (entry.get("summary") or "")[:500],
                    "published_ts": published or time.time(),
                }
            )
    return items


def _entry_time(entry) -> float | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return time.mktime(t)
    return None


# ---------------------------------------------------------------------------
# Hacker News via Algolia (no key)
# ---------------------------------------------------------------------------


_ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"
_HN_TERMS = ["AI", "LLM", "Anthropic", "OpenAI", "Claude", "Gemini", "Llama", "agent"]


def fetch_hn(since_ts: float) -> list[dict]:
    items: list[dict] = []
    seen: set[int] = set()
    cutoff = int(since_ts)
    with httpx.Client(timeout=15) as client:
        for term in _HN_TERMS:
            try:
                r = client.get(
                    _ALGOLIA,
                    params={
                        "query": term,
                        "tags": "story",
                        "numericFilters": f"created_at_i>{cutoff},points>10",
                        "hitsPerPage": PER_SOURCE_CAP,
                    },
                )
                r.raise_for_status()
                for hit in r.json().get("hits", []):
                    obj_id = hit.get("objectID")
                    if obj_id in seen:
                        continue
                    seen.add(obj_id)
                    items.append(
                        {
                            "source":       "hn",
                            "title":        hit.get("title") or hit.get("story_title") or "",
                            "url":          hit.get("url")
                                            or f"https://news.ycombinator.com/item?id={obj_id}",
                            "summary":      f"{hit.get('points', 0)} pts, "
                                            f"{hit.get('num_comments', 0)} comments",
                            "published_ts": hit.get("created_at_i") or time.time(),
                        }
                    )
            except Exception as e:
                print(f"[hn] term={term} failed: {e}")
    return items


# ---------------------------------------------------------------------------
# ArXiv
# ---------------------------------------------------------------------------


_NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_arxiv(since_ts: float) -> list[dict]:
    items: list[dict] = []
    cat_query = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    with httpx.Client(timeout=20) as client:
        try:
            r = client.get(
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": cat_query,
                    "sortBy":       "submittedDate",
                    "sortOrder":    "descending",
                    "max_results":  PER_SOURCE_CAP,
                },
            )
            r.raise_for_status()
            root = ET.fromstring(r.text)
            for entry in root.findall("a:entry", _NS):
                title = (entry.findtext("a:title", default="", namespaces=_NS) or "").strip()
                summary = (entry.findtext("a:summary", default="", namespaces=_NS) or "").strip()
                published = entry.findtext("a:published", default="", namespaces=_NS) or ""
                link_el = entry.find("a:link[@rel='alternate']", _NS)
                url = link_el.get("href") if link_el is not None else ""
                ts = _iso_ts(published)
                if ts < since_ts:
                    continue
                items.append(
                    {
                        "source":       "arxiv",
                        "title":        title.replace("\n", " "),
                        "url":          url,
                        "summary":      summary[:500].replace("\n", " "),
                        "published_ts": ts or time.time(),
                    }
                )
        except Exception as e:
            print(f"[arxiv] failed: {e}")
    return items


def _iso_ts(s: str) -> float:
    try:
        return time.mktime(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# GitHub trending (topic:ai)
# ---------------------------------------------------------------------------


_GH = "https://api.github.com"


def fetch_github(since_ts: float) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    items: list[dict] = []
    with httpx.Client(timeout=15, headers=headers) as client:
        try:
            r = client.get(
                f"{_GH}/search/repositories",
                params={
                    "q":        f"topic:{GITHUB_TRENDING_TOPIC} created:>{cutoff}",
                    "sort":     "stars",
                    "order":    "desc",
                    "per_page": PER_SOURCE_CAP,
                },
            )
            r.raise_for_status()
            for repo in r.json().get("items", []):
                ts = _iso_ts(repo.get("pushed_at", ""))
                if ts < since_ts:
                    continue
                items.append(
                    {
                        "source":       "github",
                        "title":        f"{repo['full_name']} — "
                                        f"{repo.get('description') or ''}".strip(),
                        "url":          repo["html_url"],
                        "summary":      f"{repo.get('stargazers_count', 0)} stars, "
                                        f"language={repo.get('language', '?')}",
                        "published_ts": ts or time.time(),
                    }
                )
        except Exception as e:
            print(f"[github] failed: {e}")
    return items


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


def fetch_all(since_ts: float, *, enabled: set[str] | None = None) -> list[dict]:
    """Run every enabled fetcher. `enabled` is a set like {'rss', 'hn'}.

    `None` means run all. Returns a flat list of Items.
    """
    fetchers: dict[str, callable] = {
        "rss":    fetch_rss,
        "hn":     fetch_hn,
        "arxiv":  fetch_arxiv,
        "github": fetch_github,
    }
    if enabled is None:
        enabled = set(fetchers.keys())
    out: list[dict] = []
    for name, fn in fetchers.items():
        if name not in enabled:
            continue
        try:
            chunk = fn(since_ts)
            print(f"[fetch] {name}: {len(chunk)} items")
            out.extend(chunk)
        except Exception as e:
            print(f"[fetch] {name} crashed: {e}")
    return out
