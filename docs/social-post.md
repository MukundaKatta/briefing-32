# Social post drafts — Build Small entry

The hackathon requires "a social post" alongside the Space + demo video.
Drafts below. Hold for explicit user confirmation before publishing on
LinkedIn (per the user's preference).

---

## Draft A — LinkedIn (long-form, 1200 chars)

I built a small-model version of an AI-news briefing I already run every two
hours on my laptop, for the Hugging Face Build Small Hackathon (Backyard AI
track).

The production cron uses Groq Llama-3.3-70B for relevance scoring. Build
Small forced the question: can the same workflow fit under 32B parameters
on a laptop? The answer was yes, with one change to the prompt structure.
I split the single 70B scoring pass into two cheaper passes on Qwen3-32B:
a binary KEEP/DROP filter first, then a graded 0-10 ranker. Same end
signal, half the prompt tokens at the expensive step.

briefing-32 fetches RSS + Hacker News + arXiv + GitHub, runs the two-pass
agent on Qwen3-32B through Hugging Face Inference Providers, and renders a
~1500-char digest grouped by theme. Three bonus quest badges targeted:
Off-Brand (custom Gradio theme), Sharing is Caring (full agent trace per
run), Field Notes (blog post on the down-port).

Apache 2.0. Try it:

Space: huggingface.co/spaces/build-small-hackathon/briefing-32
Code:  github.com/MukundaKatta/briefing-32
Demo:  youtu.be/7VQf_6mSDCw

#BuildSmall #HuggingFace #Gradio #Qwen3 #AIagents

---

## Draft B — X/Twitter (~270 chars)

Built briefing-32 for the @huggingface Build Small Hackathon (Backyard AI):
a 32B-class port of an AI-news briefing I already run every 2 hours.

Two passes on Qwen3-32B replace the single 70B scoring pass. Same signal,
half the tokens.

Space + demo + code: huggingface.co/spaces/build-small-hackathon/briefing-32

---

## Post-time checklist

When the user confirms "post it":
1. LinkedIn: paste Draft A into the composer, attach demo video link, click Post.
2. X: paste Draft B, click Post.
3. Capture the post URL(s) — they are part of the official Build Small
   submission ("Drop your Space link, a short demo video, and a social post").
4. Add the post URL(s) to the official submission form once the form goes
   live (between May 29 and Jun 8).
