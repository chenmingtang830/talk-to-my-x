# My recap draft template

This file is **yours to edit**. It turns a finished voice session into something
I'd actually post — not a generic AI summary.

---

## The job (in order)

Write as **me**, first person. The post is about **my session**, not a press
recap of other people's tweets.

1. **What I dug into** — which posts/topics from the brief I actually spent time
   on (not the whole brief).
2. **What I asked / pushed on** — the questions or angles I brought. Smooth messy
   voice transcripts into clean narration; don't quote awkward ASR literally.
3. **My takeaway** — only what I actually concluded or reacted to in the
   conversation. If I didn't say a takeaway, don't invent one; end on the
   concrete finding instead.

## Links are mandatory

Every specific post you reference must include its full URL inline in the
post text, e.g. `https://x.com/<author>/status/<id>`.

Prefer links from:
- `AVAILABLE SOURCE LINKS` / brief grounding in the session payload
- `[tool]` results (`get_post`, `search_x`, etc.)

No bare name-drops without a URL. If you can't find a URL for something, omit
that claim rather than hand-wave.

Also fill `sources: [{id, author, url}, ...]` for every link you used.

## Shape

- **One clear rabbit hole** → single post (still with at least one source URL).
- **Two+ distinct digs** → thread:
  - Post 1: hook — “spent my LiveCast on X / Y…”
  - Later posts: one dig each — source link + what I asked + takeaway
  - Keep each post ≤260 characters when possible (hard max 280)
- Mostly listened, barely asked → short post; don't fake depth.

## Voice (anti-slop)

Sound like a sharp friend, not LinkedIn / product marketing.

**Do:** concrete nouns, numbers, tradeoffs, “I asked…”, “what clicked for me…”  
**Don't use** empty intensifiers or AI filler, including:
- “Super interesting / pretty eye-opening / sounds smart / really resonated”
- “It's all about…” / “In today's fast-paced…” / “dive deep” / “game-changer”
- Restating the same point twice with softer adjectives
- Emoji spam or hashtags unless I used them in-session

Name people by display name in prose; put the `@handle` only inside the URL path.

## What NOT to include

- Meta / debugging (“let me search”, “testing the tool”, room UI talk)
- Topics from the brief we never actually discussed
- Opinions I never expressed

## Output

JSON only, per `references/draft.schema.example.json`:
- either `"text": "..."` or `"thread": ["...", "..."]`
- always `"sources": [{"id","author","url"}, ...]`
