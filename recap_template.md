# My recap draft template

This file is **yours to edit**. It tells the agent how to turn a finished voice
session (`sessions/latest.json`) into something shareable. Unlike the brief
(`prompt.md`), there's no fixed shape here — it really depends on the session:
sometimes a single quick post is right, sometimes a full thread with sources.
Let the content decide; use this file to describe your taste and defaults.

---

## What the source material is

Not just "a summary of posts." The full value is in **my participation**: what
I chose to dig into, the questions I actually asked, what the host found when I
asked it to look something up, and what I took away. Use all of it:

- The original brief text.
- The full back-and-forth (what I asked, what the host said).
- Every tool call result (posts the host actually looked up while we talked) —
  these have real links; use them as sources, don't paraphrase without a link
  when a specific post is being referenced.

## Decide the shape, don't force one

- If the session was short / one clear thread of thought → **a single post**.
  Something like: "Did my X-LiveCast run this morning — went deep on
  [topic]. Turns out [key point]. Sources: [links]."
- If we covered multiple distinct things, or I dug into several posts →
  **a thread**. First post = the hook / what this is. Each following post =
  one thing we discussed: the source (linked), what I asked or noticed, my
  takeaway. Keep each post under ~260 characters.
- If it was mostly me listening with no real interrogation → keep it minimal,
  don't manufacture a takeaway that wasn't actually said.

## Voice

- First person, casual, like I'm telling a friend what I found interesting —
  not a press release, not a listicle.
- It's OK to have opinions if I expressed one in the conversation. Don't invent
  ones I didn't.
- Always link the actual source post when referencing something specific
  (use the `id`/`author` from the tool_call results to build the link:
  `https://x.com/<author>/status/<id>`).

## What NOT to include

- Don't quote my questions verbatim if they're awkward as written (voice
  transcripts are messy) — smooth them into narration.
- Don't include anything that sounds like debugging/meta talk ("testing the
  tool", "let me search that") — that's not part of the story.

## Output

Write the draft to `drafts/latest.json` per the schema in
`references/draft.schema.example.json` — either a single `text`, or a `thread`
array of post texts, plus a `sources` list of `{id, author, url}` referenced.
