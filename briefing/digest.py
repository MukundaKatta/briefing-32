"""Digest renderer — turns top-N ranked items into a readable briefing."""
from __future__ import annotations

import json

from briefing.config import DIGEST_TOP_N
from briefing.rank import RankerConfig, _chat


_DIGEST_SYSTEM = "You write tight, useful AI-news briefings. No fluff."


_DIGEST_PROMPT = """Write a 2-hour AI-news briefing from the items below.

RULES:
- Group by theme if obvious (Models / Research / Tools / Industry); otherwise a flat list.
- Each item: 1-2 lines in plain English. End the item with the URL on its own line.
- Lead with WHAT CHANGED and WHY IT MATTERS — not the source name.
- No markdown headers, no bold asterisks. Optional bullet (•).
- Skip items that are obvious duplicates or hype with no concrete new info.
- Close with a one-line meta note ("3 from labs, 2 from research, 1 from tools" style).
- Target ~1500 chars total. Stay short. Skip filler.

Items (ranked by importance, highest first):
{items_json}
"""


def make_digest(ranked: list[dict], cfg: RankerConfig | None = None) -> str:
    """Render the top-N ranked items as a readable briefing."""
    if not ranked:
        return "_(no high-signal items in window)_"
    cfg = cfg or RankerConfig()
    top = ranked[:DIGEST_TOP_N]
    indexed = [
        {
            "source":  it.get("source", ""),
            "title":   (it.get("title") or "")[:200],
            "url":     it.get("url", ""),
            "summary": (it.get("summary") or "")[:300],
            "score":   it.get("score", 5),
            "reason":  it.get("reason", ""),
        }
        for it in top
    ]
    return _chat(
        cfg,
        _DIGEST_SYSTEM,
        _DIGEST_PROMPT.format(items_json=json.dumps(indexed, ensure_ascii=False, indent=2)),
        json_mode=False,
        temperature=0.3,
        max_tokens=2000,
    ).strip()
