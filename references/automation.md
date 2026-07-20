# Optional automation

X Feed Loop is on demand in v0.1. The local CLI cannot independently produce a
feed review because it intentionally has no X or model access. Any schedule
must invoke a host agent with both the official X skill and X Feed Loop loaded.

A scheduled prompt can say:

> Use the official X skill to fetch my latest Timeline and Bookmarks. Then use
> X Feed Loop to ingest them, apply my configured lens, and present a small set
> with a rationale for each. Do not publish anything.

Use the host's supported scheduler:

- Codex: create an automation that runs the prompt in this repository.
- OpenClaw: schedule an agent turn with both skills available.
- cron: invoke a non-interactive host-agent command, not `x-feed-loop` alone.

Keep scheduled runs read-only with respect to X. Drafting, memory changes, and
all publishing should remain visible agent turns. Never place tokens or X
credentials in a crontab or prompt.
