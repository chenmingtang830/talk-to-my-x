# X Feed Loop

I read X in small pockets throughout the day. A post sparks a question, a
reaction, maybe the beginning of a take—then it is gone by the time I sit down
to write.

X Feed Loop keeps those threads alive. It is a local agent skill that creates a
continuous loop between what you read on X, how you think through it, and what
you publish—learning your taste and voice along the way.

## How it works

1. **Set the lens.** Configure topics and accounts, plus why they matter, which
   angles to notice, what good signal looks like, and what to ignore.
2. **Think through conversation.** Discuss a focused selection from your feed
   and bookmarks in the agent you already use. Sources and reactions stay tied
   together.
3. **Draft in your voice.** Shape accumulated reactions into a source-grounded
   post or thread—not a generic summary of the feed.
4. **Let the loop evolve.** What you select, skip, question, rewrite, and publish
   updates local Taste and Voice memory with a reversible audit trail.

X Feed Loop does not provide an X client, model, chat runtime, web UI, or hosted
service. It composes with the [official X skill](https://docs.x.com/tools/skill-md)
for X reads and writes, and with the user's agent for reasoning.

## Architecture

```text
User's agent
  ├─ official X skill / xurl  → timeline, bookmarks, search, post, reply
  └─ X Feed Loop skill
       └─ thin local CLI      → posts, Reaction Cards, drafts, Taste/Voice memory
                                (~/.x-feed-loop/)
```

Full chat history remains in the host agent. X Feed Loop stores only reusable
local artifacts, not a second copy of every conversation.

## Install

Requirements: Python 3.10+, `xurl`, and an agent that supports skills and local
commands.

```bash
# Add X's official skill and complete its xurl authentication flow.
npx skills add https://docs.x.com

# Clone and install the local state CLI.
gh repo clone chenmingtang830/x-feed-loop
cd x-feed-loop
python3 -m pip install -e .

x-feed-loop doctor
```

Add this repository as a skill using your harness's normal skill installation
flow. `AGENTS.md` and `CLAUDE.md` both route agents to `SKILL.md`.

The first CLI command creates `~/.x-feed-loop/`. Edit
`~/.x-feed-loop/preferences.md`, then ask your agent:

> Use X Feed Loop to review my new bookmarks and feed. Focus on why these posts
> matter to me, and capture my reactions as we talk.

## CLI boundary

The CLI never calls X, never calls a model, and never publishes. It only manages
local state supplied by the host agent:

```text
x-feed-loop doctor
x-feed-loop ingest --source timeline|bookmarks|search --stdin
x-feed-loop context --json
x-feed-loop signal --post ID --kind selected|skipped|explored
x-feed-loop capture --stdin
x-feed-loop draft save --stdin
x-feed-loop draft mark-published --id ID --stdin
x-feed-loop memory apply --stdin
x-feed-loop memory rollback --snapshot ID
x-feed-loop preferences export|import
x-feed-loop migrate --from /path/to/previous-checkout
```

Payload examples: [references/schemas.md](references/schemas.md). Local storage:
[references/local-layout.md](references/local-layout.md).

## Safety

- X credentials stay under `~/.xurl`; never paste them into an agent chat.
- All X writes use the official X skill.
- Drafting never implies approval to publish.
- Publishing requires an explicit confirmation after showing the exact text.
- Memory updates keep evidence and reversible snapshots.

## Project direction

The earlier prototype is preserved in Git history and on its legacy branch.
The active product is intentionally local and agent-native. Read
[the product definition](docs/PRODUCT.md),
[the architecture decision](docs/decisions/0001-x-feed-loop.md), and
[the roadmap](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).
