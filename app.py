"""briefing-32 — Gradio app entry for Hugging Face Spaces.

Build Small Hackathon submission (Backyard AI track):
A small-model down-port of ~/ai-news-agent. The production version uses
Groq Llama-3.3-70B; this version fits the same workflow under 32B params
using Qwen3-32B via Hugging Face Inference Providers.

Same pipeline as the every-2-hours cron the maker has running on a laptop:
fetch RSS / HN / arXiv / GitHub -> two-pass relevance filter + ranker ->
readable digest. Gradio is the delivery surface here instead of WhatsApp.
"""
from __future__ import annotations

import os
import time
from typing import Any

import gradio as gr
import pandas as pd

from briefing.config import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    MIN_NEW_ITEMS,
    PER_SOURCE_CAP,
)
from briefing.digest import make_digest
from briefing.fetch import fetch_all
from briefing.rank import RankerConfig, rank_pipeline


# ---------------------------------------------------------------------------
# Core pipeline (callable from Gradio + scripts/cli.py)
# ---------------------------------------------------------------------------


def run_briefing(
    window_hours: int,
    enabled_sources: list[str],
    model: str,
    hf_token: str,
) -> dict[str, Any]:
    """Fetch -> filter -> rank -> digest. Returns everything for the UI."""
    since_ts = time.time() - window_hours * 3600
    enabled = set(enabled_sources) if enabled_sources else {"rss", "hn", "arxiv", "github"}

    t0 = time.perf_counter()
    raw = fetch_all(since_ts, enabled=enabled)
    fetch_latency = time.perf_counter() - t0

    cfg = RankerConfig(
        base_url=DEFAULT_BASE_URL,
        model=model or DEFAULT_MODEL,
        api_key=hf_token or "",
    )
    result = rank_pipeline(raw, cfg=cfg)

    digest = ""
    if result.after_rank >= MIN_NEW_ITEMS:
        digest = make_digest(result.items, cfg=cfg)
    elif result.after_rank > 0:
        digest = make_digest(result.items, cfg=cfg)

    return {
        "digest":         digest or "_(no high-signal items in window)_",
        "items":          result.items,
        "raw_count":      result.raw_count,
        "after_filter":   result.after_filter,
        "after_rank":     result.after_rank,
        "fetch_latency":  fetch_latency,
        "filter_latency": result.filter_latency,
        "rank_latency":   result.rank_latency,
        "model":          cfg.model,
    }


# ---------------------------------------------------------------------------
# Gradio glue
# ---------------------------------------------------------------------------


def _items_to_df(items: list[dict]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["score", "source", "title", "reason", "url"])
    rows = [
        {
            "score":  it.get("score", 0),
            "source": it.get("source", ""),
            "title":  it.get("title", ""),
            "reason": it.get("reason", ""),
            "url":    it.get("url", ""),
        }
        for it in items
    ]
    return pd.DataFrame(rows)


def _stats_md(result: dict[str, Any]) -> str:
    return (
        f"**Model:** `{result['model']}`  \n"
        f"**Raw items fetched:** {result['raw_count']}  \n"
        f"**Survived filter:** {result['after_filter']}  \n"
        f"**Survived rank (score ≥ 6):** {result['after_rank']}  \n"
        f"**Fetch latency:** {result['fetch_latency']:.1f}s  \n"
        f"**Filter latency:** {result['filter_latency']:.1f}s  \n"
        f"**Rank latency:** {result['rank_latency']:.1f}s  \n"
        f"**Total LLM time:** {result['filter_latency'] + result['rank_latency']:.1f}s"
    )


def _gradio_handler(window_hours, sources, model, hf_token):
    try:
        result = run_briefing(
            window_hours=int(window_hours),
            enabled_sources=list(sources or []),
            model=(model or DEFAULT_MODEL).strip(),
            hf_token=(hf_token or "").strip(),
        )
    except Exception as e:
        return (
            f"**Error:** `{e}`\n\nMake sure `HF_TOKEN` is set in Space secrets "
            f"or pasted into the sidebar.",
            pd.DataFrame(),
            "_no run yet_",
        )
    return result["digest"], _items_to_df(result["items"]), _stats_md(result)


# Custom theme — "Off-Brand" bonus badge target.
THEME = gr.themes.Soft(
    primary_hue="orange",
    secondary_hue="slate",
    neutral_hue="zinc",
).set(
    body_background_fill="#0b1220",
    body_text_color="#e2e8f0",
    block_background_fill="#111827",
    block_border_width="1px",
    block_border_color="#1f2937",
    button_primary_background_fill="#f97316",
    button_primary_text_color="#0b1220",
)


with gr.Blocks(theme=THEME, title="briefing-32 · Build Small entry") as demo:
    gr.Markdown(
        """
        # briefing-32
        **A 32B-class AI-news briefing the maker runs every 2 hours.**

        Build Small Hackathon entry (Backyard AI track). Down-ported from the
        production `ai-news-agent` cron (Groq Llama-3.3-70B → WhatsApp) onto
        Qwen3-32B served by Hugging Face Inference Providers.

        Pipeline: RSS + HN + arXiv + GitHub  →  cheap relevance filter  →
        graded 0–10 ranker  →  readable digest. Two open-weight model calls,
        no 70B cloud round-trip required.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Controls")
            window_hours = gr.Slider(
                minimum=1, maximum=72, value=2, step=1,
                label="Window (hours back)",
                info="Production runs every 2hr — match that for the authentic story.",
            )
            sources = gr.CheckboxGroup(
                choices=["rss", "hn", "arxiv", "github"],
                value=["rss", "hn", "arxiv", "github"],
                label="Sources",
            )
            model = gr.Textbox(
                value=DEFAULT_MODEL,
                label="Model (≤32B params)",
                info="Default Qwen3-32B. Swap to Qwen3-30B-A3B for faster MoE inference.",
            )
            hf_token = gr.Textbox(
                label="HF_TOKEN (optional — reads env if blank)",
                placeholder="hf_…",
                type="password",
            )
            run_btn = gr.Button("Run briefing", variant="primary")

            gr.Markdown("### Run stats")
            stats = gr.Markdown("_no run yet_")

        with gr.Column(scale=2):
            gr.Markdown("### Digest")
            digest = gr.Markdown(
                value="_Click **Run briefing** to fetch the last N hours of AI news, "
                      "rank it on a ≤32B model, and render a readable briefing._"
            )
            gr.Markdown("### Ranked items")
            items_df = gr.Dataframe(
                headers=["score", "source", "title", "reason", "url"],
                value=pd.DataFrame(columns=["score", "source", "title", "reason", "url"]),
                wrap=True,
                interactive=False,
            )

    run_btn.click(
        _gradio_handler,
        inputs=[window_hours, sources, model, hf_token],
        outputs=[digest, items_df, stats],
    )

    gr.Markdown(
        """
        ---
        *Build Small Hackathon · Backyard AI track. Apache 2.0.*
        Code: [github.com/MukundaKatta/briefing-32](https://github.com/MukundaKatta/briefing-32)
        """
    )


if __name__ == "__main__":
    demo.queue(max_size=8).launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", "7860")),
    )
