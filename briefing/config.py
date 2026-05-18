"""Config — model defaults, source list, tunables.

Build Small Hackathon constraints: model must be ≤32B params and runnable on
a laptop. Default is Qwen3-32B routed through HF Inference Providers so the
HF Space talks to a real open-weight model with predictable cost.
"""
from __future__ import annotations

import os

# Default model — Apache 2.0, 32B dense, native JSON mode.
DEFAULT_MODEL = os.getenv("BRIEFING_MODEL", "Qwen/Qwen3-32B")

# HF Inference Providers OpenAI-compatible router.
DEFAULT_BASE_URL = os.getenv("BRIEFING_BASE_URL", "https://router.huggingface.co/v1")

# Smart-batch threshold for the digest section. Below this, the UI says
# "nothing high-signal in the window" rather than rendering noise.
MIN_NEW_ITEMS = int(os.getenv("MIN_NEW_ITEMS", "3"))

# Per-source cap to bound prompt size.
PER_SOURCE_CAP = int(os.getenv("PER_SOURCE_CAP", "20"))

# Minimum relevance score (0-10) to make it into the digest.
MIN_RELEVANCE = int(os.getenv("MIN_RELEVANCE", "6"))

# Top-N items to put into the digest prompt after ranking.
DIGEST_TOP_N = int(os.getenv("DIGEST_TOP_N", "12"))

# ArXiv categories pulled live.
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]

# GitHub trending topic filter.
GITHUB_TRENDING_TOPIC = "ai"

# RSS feeds — lab blogs + high-signal newsletters + YouTube channels.
RSS_FEEDS: list[tuple[str, str]] = [
    # AI labs
    ("Anthropic",                "https://www.anthropic.com/news/rss.xml"),
    ("OpenAI",                   "https://openai.com/news/rss.xml"),
    ("Google DeepMind",          "https://deepmind.google/blog/rss.xml"),
    ("Google AI",                "https://blog.google/technology/ai/rss/"),
    ("Meta AI",                  "https://ai.meta.com/blog/rss/"),
    ("Mistral",                  "https://mistral.ai/news/feed.xml"),
    ("xAI",                      "https://x.ai/blog/rss.xml"),
    ("HuggingFace",              "https://huggingface.co/blog/feed.xml"),
    # Newsletters / blogs
    ("Latent Space",             "https://www.latent.space/feed"),
    ("Import AI",                "https://importai.substack.com/feed"),
    ("The Rundown AI",           "https://www.therundown.ai/feed"),
    ("Stratechery",              "https://stratechery.com/feed/"),
    ("Simon Willison",           "https://simonwillison.net/atom/everything/"),
    ("Andrej Karpathy",          "https://karpathy.github.io/feed.xml"),
    ("One Useful Thing",         "https://www.oneusefulthing.org/feed"),
    ("AI Snake Oil",             "https://www.aisnakeoil.com/feed"),
    ("Last Week in AI",          "https://lastweekin.ai/feed"),
    ("AI Tidbits",               "https://aitidbits.substack.com/feed"),
    ("Linus Lee",                "https://thesephist.com/posts.xml"),
    ("Lilian Weng",              "https://lilianweng.github.io/index.xml"),
    # YouTube (Atom feeds, no key required)
    ("YT: Yannic Kilcher",       "https://www.youtube.com/feeds/videos.xml?channel_id=UCZHmQk67mSJgfCCTn7xBfew"),
]
