---
name: x-feed-loop
description: >-
  Think with a user's X feed and compound fragmented reactions into
  source-grounded post drafts in their own voice. Use when the user wants a
  personalized review of their X timeline or bookmarks, wants to discuss posts
  and preserve reactions across chats, asks to turn those reactions into an X
  post or thread, or wants the loop to learn their taste and writing voice.
  Compose with the official X skill for all X reads and writes; keep state local.
---

# X Feed Loop

Create a continuous local loop between what the user reads on X, how they think
through it, and what they publish. Use the host agent for reasoning and
conversation. Use the official X skill for X access. Use `x-feed-loop` only for
deterministic local state.

## Prerequisites

1. Install the official X skill: `npx skills add https://docs.x.com`.
2. Complete `xurl` authentication outside the agent chat; never read or expose
   `~/.xurl`.
3. Install this package and run `x-feed-loop doctor`.
4. Edit `~/.x-feed-loop/preferences.md` after the first run.

If the official X skill is unavailable, stop and point the user to
<https://docs.x.com/tools/skill-md>. Do not recreate X API calls in this skill.

## Core workflow

### 1. Build context

Run `x-feed-loop context --json`. Read the configured lens, USER/TASTE/VOICE
memory, unprocessed posts, and open Reaction Cards.

If fresh posts are needed, use the official X skill to fetch the requested
sources (timeline, bookmarks, priority accounts, or search). Normalize results
as described in [references/schemas.md](references/schemas.md), then ingest:

```bash
x-feed-loop ingest --source timeline --stdin
x-feed-loop ingest --source bookmarks --stdin
x-feed-loop ingest --source search --stdin
```

Run `context` again after ingestion.

### 2. Apply the user's lens

Select a small set of posts using all of:

- explicit preferences and rationale;
- current topics, accounts, angles, good-signal rules, and ignores;
- durable Taste memory;
- open questions and connections in Reaction Cards.

Explain why each selected post matters to this user. Do not produce a generic
feed summary. Record selection signals:

```bash
x-feed-loop signal --post POST_ID --kind selected
x-feed-loop signal --post POST_ID --kind skipped
```

### 3. Think through conversation

Discuss selected posts in the current host-agent chat. Let the user react, ask,
push back, connect ideas, or leave thoughts unfinished. Keep every claim tied to
the original post URL.

After each meaningful reaction, call `x-feed-loop capture --stdin`. Preserve the
user's raw wording; add summaries, stance, questions, and connections only when
grounded in what they said. Reuse a card ID when continuing the same line of
thought. Full chat history stays with the host agent; Reaction Cards are the
portable local memory.

### 4. Draft from the thinking

When the user asks to wrap up or draft, use the current conversation plus the
relevant Reaction Cards. Write as the user, not as a feed summarizer.

- Include only ideas the user expressed or explicitly approved.
- Preserve distinctive phrases from raw reactions.
- Include full source URLs for specific claims.
- Prefer one post; use a thread only for multiple distinct ideas.
- Keep every X post at 280 characters or fewer.

Save the result with `x-feed-loop draft save --stdin`. See
[references/schemas.md](references/schemas.md) for the payload.

### 5. Evolve Taste and Voice

Treat behavior as feedback: selected/skipped posts update Taste; reactions and
draft edits update Voice. After a substantive session, produce complete updated
`TASTE.md` and `VOICE.md` documents and call:

```bash
x-feed-loop memory apply --stdin
```

Every update must cite supporting Reaction Card IDs and give a short rationale.
Apply updates automatically, but keep them conservative and durable. Explicit
user corrections override inferred preferences. The CLI records before/after
snapshots; use `x-feed-loop memory rollback --snapshot ID` when needed.

### 6. Publish only after confirmation

Show the exact final post or thread. Ask for explicit confirmation. Before that
confirmation, do not call any X write command.

After confirmation, use the official X skill (`xurl post`, followed by
`xurl reply` for a thread). Record the successful X response with
`x-feed-loop draft mark-published --id ID --stdin`.

Never publish from a scheduler, memory update, draft request, or ambiguous
approval.

## Optional daily run

The core workflow is on demand. To schedule it, use the user's existing agent
automation or cron to invoke the skill; do not schedule `x-feed-loop` by itself,
because the host agent performs selection and synthesis. See
[references/automation.md](references/automation.md).

## Local data and migration

All state defaults to `~/.x-feed-loop/`; override with `XFL_HOME`. Read
[references/local-layout.md](references/local-layout.md) when diagnosing state
or privacy issues. For an earlier-version checkout, follow
[references/migration.md](references/migration.md).
