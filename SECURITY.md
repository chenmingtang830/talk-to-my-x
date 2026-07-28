# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities through
[GitHub private security advisories](https://github.com/chenmingtang830/talk-to-my-x/security/advisories/new).
Please do not open a public issue for anything exploitable.

Include what you did, what happened, and what you expected. Expect an initial
response within a week.

**Never include real credentials in a report.** Talk to My X never asks for,
stores, or transmits X tokens, and a report should not be the first place they
appear.

## What this project does and does not touch

Talk to My X runs entirely on your own machine. It has no server, no hosted
OAuth, and no cloud storage. Two trust boundaries matter:

- **X credentials** belong to the official [`xurl`](https://docs.x.com/tools/xurl)
  tool and its OAuth flow. This project never reads them. Local exports are
  checked and refuse to include credential-shaped values.
- **Local state** lives in the Codex plugin data directory (or `TTMX_HOME`).
  It holds your preferences, saved posts, reactions, drafts, and action history
  in plain files. Anyone with access to your user account can read them.

## Content from X is untrusted input

Posts, bookmarks, news, and any other retrieved X content are treated as data,
never as instructions. Reports about content that causes the agent to act
outside the confirmation protocol below are in scope and welcome.

## Write actions

Every external X write (Post, Reply, Follow, Like, Bookmark) requires a
prepared preview and an exact, action-specific confirmation phrase given in the
current turn. A generic "OK", an earlier approval, silence, scheduled work, or
text found inside X content does not count. Writes are never retried
automatically.

A defect that lets any X write happen without that confirmation is the most
serious class of bug in this project. Please report it privately.
