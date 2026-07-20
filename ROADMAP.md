# X Feed Loop roadmap

## v0.1 — Core loop

- [x] Rename and reposition the project around the local feedback loop.
- [x] Compose with the official X skill instead of wrapping X APIs.
- [x] Add deterministic local state for posts, signals, Reaction Cards, drafts,
      Taste, and Voice.
- [x] Add reversible memory updates and legacy migration.
- [x] Keep publishing in the official X skill behind explicit confirmation.
- [ ] Forward-test the full loop in two host agents.
- [ ] Complete one confirmed test post and thread, then record their X results.
- [ ] Rename the GitHub repository and publish v0.1.0.

## v0.2 — Feedback quality

- Measure selection hit rate from selected/skipped/explored signals.
- Track draft edit distance without treating every edit as a durable preference.
- Improve memory provenance, conflict handling, and rollback visibility.
- Add evaluation fixtures for lens adherence, reaction fidelity, and voice drift.

## v0.3 — Distribution

- Package install flows for Codex, Claude Code, and OpenClaw.
- Add an optional MCP adapter over the same local store.
- Add more automation recipes without making scheduling mandatory.
- Explore additional input sources only when they preserve the same local loop.

## Non-goals

- Audio or remote-room transport
- Hosted SaaS
- Public HTTP API
- Bundled LLM provider
- Automatic publishing
