# ADR 0001: Replace X-LiveCast with X Feed Loop

## Status

Accepted — 2026-07-20

## Context

The original prototype combined a personalized X brief with a custom Gemini
Live voice room, web UI, public tunnel, DM delivery, cloud deployment, session
management, memory, drafts, and publishing. The prototype worked, but owning the
entire user journey created more UI, infrastructure, and security work than the
core problem required.

The durable user problem is fragmented sensemaking: valuable reactions to X
posts disappear before they become notes or publishable ideas.

## Decision

Rebuild the project as X Feed Loop, a local, agent-native workflow.

- Let the user's existing agent own conversation and reasoning.
- Let the official X skill own X reads and writes.
- Keep only deterministic local state and workflow instructions in this project.
- Persist Reaction Cards, drafts, and Taste/Voice memory instead of duplicate
  full transcripts.
- Keep daily scheduling optional and publishing explicitly confirmed.

The legacy `x-livecast-skill` branch remains the Voice prototype. It is not part
of the active product or roadmap.

## Alternatives considered

- The [official X skill](https://docs.x.com/tools/skill-md) is the upstream
  access layer. Reusing it avoids duplicating authentication, endpoint coverage,
  and publishing behavior.
- [x-bookmarks-digest](https://github.com/openclaw/skills/tree/main/skills/bearly-hodling/x-bookmarks-digest)
  turns saved posts into an actionable digest. It does not center a persistent,
  multi-turn reaction-to-draft feedback loop.
- [xint](https://github.com/0xNyk/xint) provides broad search, monitoring,
  analysis, and engagement tooling. Replacing the official access layer with
  another X client would expand rather than reduce this project's scope.
- [last30days](https://github.com/mvanhorn/last30days-skill) synthesizes recent
  signal across multiple public sources. Its unit of value is a research brief;
  this project's unit of value is the user's accumulated reaction and voice.

The missing layer is therefore not retrieval. It is local, inspectable state
that connects a user's lens, reactions, draft edits, Taste, and Voice over time.

## Consequences

The project loses its standalone phone/voice experience and provider-specific
demo. In return it has no hosted attack surface, no Gemini dependency, no custom
X API layer, and a much smaller cross-harness product surface.
