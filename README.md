---
title: briefing-32
emoji: 📰
colorFrom: orange
colorTo: gray
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: A 32B-class AI-news briefing the maker runs every 2 hours.
---

# briefing-32

A small-model AI-news briefing agent. Submission for the **Hugging Face
Build Small Hackathon** ([huggingface.co/build-small-hackathon](https://huggingface.co/build-small-hackathon))
in the **Backyard AI** track.

## What it is

This is a deliberate down-port of [`ai-news-agent`](https://github.com/MukundaKatta/ai-news-agent),
a personal cron that already runs every two hours on the maker's laptop to
deliver an AI-news digest to WhatsApp. The production cron uses Groq
Llama-3.3-70B for relevance scoring. Build Small forces the same workflow
under 32B parameters.

The honest story for the Backyard AI track:

> "I have used a personal AI-news briefing every two hours since spring 2026.
> The original uses a 70B model on a free Groq tier. Build Small asked me to
> live under 32B, on a laptop. So I split the single 70B scoring pass into
> two cheaper passes on Qwen3-32B — a binary relevance filter, then a graded
> ranker — and the digest quality holds up."

## Pipeline

```
fetch (RSS · HN · arXiv · GitHub)
        │
        ▼
pass 1 — binary relevance filter on Qwen3-32B
        │
        ▼
pass 2 — graded 0–10 ranker on Qwen3-32B
        │
        ▼
digest renderer on Qwen3-32B
```

Two small-model calls do the work one big-model call did before.

## Sources (no Reddit / Bluesky)

- **RSS / Atom**: Anthropic, OpenAI, DeepMind, Google AI, Meta AI, Mistral,
  xAI, HuggingFace, Latent Space, Import AI, The Rundown AI, Stratechery,
  Simon Willison, Karpathy, Lilian Weng, Linus Lee, and several more
  high-signal blogs and newsletters.
- **Hacker News**: AI-tagged stories via the Algolia public API.
- **arXiv**: newest `cs.AI` / `cs.CL` / `cs.LG` submissions.
- **GitHub**: repos with `topic:ai` created in the last 14 days, sorted by stars.

Reddit and Bluesky public endpoints both 403-block traffic in 2026, so the
port drops them. The production cron has the same scars in its logs.

## Run locally

```sh
pip install -r requirements.txt
HF_TOKEN=hf_xxx python app.py
```

Then open the Gradio URL it prints. Click **Run briefing**.

## Run as an HF Space

The repo is shaped like a standard Hugging Face Space. The `README.md`
front-matter wires `app.py` as the entry point and pins the Gradio SDK.
After deploy, the Space's "Settings → Variables and secrets" gets one
secret: `HF_TOKEN` (a read-permission token is plenty).

## Model

Default model: **Qwen/Qwen3-32B** (Apache 2.0, 32B dense, native JSON mode),
routed through HF Inference Providers.

Alternatives that fit Build Small's ≤32B cap and were considered:
`Qwen/Qwen3-30B-A3B`, `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`,
`mistralai/Mistral-Small-24B-Instruct-2501`. Swap in the sidebar.

## Targeted bonus quests

The hackathon has six optional bonus quests. This submission targets:

- **Field Notes** — a write-up about the 70B → 32B down-port and what
  surprised me (see `docs/down-port-notes.md` after the build window).
- **Sharing is Caring** — a captured agent trace published alongside the
  Space (see `docs/sample-trace.md`).
- **Off-Brand** — custom Gradio theme + layout (see `app.py`).

Optional stretch: **Llama Champion** (a llama.cpp variant for the same
pipeline) + **Off the Grid** (the llama.cpp variant doubles for that badge).

## License

Apache 2.0.

## Credit

Built by [Mukunda Katta](https://github.com/MukundaKatta) as an independent
project for Build Small. The production cron it down-ports is
[`MukundaKatta/ai-news-agent`](https://github.com/MukundaKatta/ai-news-agent).
