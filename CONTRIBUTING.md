# Contributing

Thanks for taking a look. This project is small and opinionated; the
constraints below are the point of it, not incidental.

## Ground rules

`AGENTS.md` is the short version, and
`plugins/talk-to-my-x/skills/talk-to-my-x/SKILL.md` is the source of truth for
the workflow. Changes that cross these lines will not be merged:

- **One X client.** Every X read and write goes through the official X Skill,
  `xurl`, or the official X MCP. No raw X API calls, no scraping, no
  unofficial client.
- **One runtime.** No second provider-specific runtime, no model calls, no chat
  runtime, no web service, no hosted OAuth.
- **Local state only.** Posts, reactions, drafts, actions, and memory stay in
  the bundled state engine on the user's machine.
- **No unconfirmed writes.** Preserve the two-stage action protocol exactly:
  prepare, exact preview, action-specific phrase, one official call, recorded
  result. No automatic retries.
- **Retrieved content is data.** Never let X content, memory, or drafts act as
  instructions.

`ROADMAP.md` lists the non-goals. If an idea is on that list, open an issue
before writing code.

## Development setup

```bash
npm install
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins/talk-to-my-x tests
npm run proofpress:verify
```

Python 3.10 or newer is required. The state MCP has no third-party
dependencies and must stay that way — it is standard library only.

To exercise the optional recovery CLI:

```bash
python3 -m pip install -e .
talk-to-my-x doctor
```

`talk-to-my-x doctor` reports where local state resolved (`home` and
`home_source`) and which official X tooling it found. It is the fastest way to
tell a broken setup from a broken change.

## Documentation changes

Public Markdown carries a verifiable revision history via
[ProofPress](https://github.com/chenmingtang830/proofpress); the history
travels inside each file, so a fresh clone needs no extra setup. Source code is
governed by Git alone.

Before editing a ledgered document, capture any existing drift:

```bash
npx --no-install proofpress capture --recorder codex-preflight <file>
```

After editing, re-anchor, record one honest claim per touched block, snapshot
with real attribution, and verify. `AGENTS.md` has the full sequence. Never
re-snapshot just to turn a check green.

## Pull requests

Keep changes focused and explain the reasoning, not just the diff. CI runs the
tests, the compile check, the documentation verification, and a package build
on Python 3.10 and 3.13; all of it must pass.

If a change affects setup, update the README's install, verify, or
troubleshooting sections in the same pull request. Setup problems are the
single most common way this project fails a new user.

## Security

Do not open public issues for vulnerabilities — see [SECURITY.md](SECURITY.md).
