# Testing X Feed Loop

## Automated checks

Run from the repository root with Python 3.10 or newer:

```bash
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m py_compile src/x_feed_loop/*.py
python3 -m pip install --no-build-isolation -e .
x-feed-loop --version
x-feed-loop doctor
```

`doctor` is expected to return a non-zero exit code until the official X skill,
`xurl`, and X authentication are available. That is a setup result, not a local
state failure.

## CLI contract smoke test

Use a disposable home:

```bash
export XFL_HOME="$(mktemp -d)"
printf '%s\n' '[{"id":"1","text":"A useful post","author":"alice","url":"https://x.com/alice/status/1","source":"timeline"}]' \
  | x-feed-loop ingest --source timeline --stdin
x-feed-loop signal --post 1 --kind selected
printf '%s\n' '{"sources":["1"],"raw_reaction":"This changes how I think about the problem."}' \
  | x-feed-loop capture --stdin
x-feed-loop context --json
```

The fixture is normalized output from the official X skill. Tests never mock or
reimplement X endpoints.

## Manual host-agent acceptance

Complete this checklist in at least two supported host agents before v0.1.0:

- [ ] Load both the official X skill and X Feed Loop.
- [ ] Use the official X skill to read Timeline and Bookmarks.
- [ ] Ingest normalized posts and apply the configured lens.
- [ ] Record selected, skipped, and explored signals.
- [ ] Discuss multiple posts and preserve meaningful reactions as cards.
- [ ] Start a new chat and restore the lens, open cards, and unprocessed posts
      with `x-feed-loop context --json`.
- [ ] Generate a source-grounded draft from the user's actual reactions.
- [ ] Save an edited version and verify a new draft revision is created.
- [ ] Apply a Taste/Voice update with evidence card IDs and rationale.
- [ ] Roll back the memory snapshot and verify the previous files are restored.
- [ ] Ask to publish, then cancel; verify no X write command is called.
- [ ] After showing exact final text and receiving explicit confirmation, publish
      one disposable test post through the official X skill.
- [ ] Record returned tweet IDs, URLs, and final text with `mark-published`.
- [ ] Delete the test post through the official X skill only after a separate
      explicit confirmation.

## Release checks

- [ ] `git diff --check` passes.
- [ ] Active docs contain no legacy product or removed runtime/provider
      instructions; historical details appear only in migration/decision docs.
- [ ] No credentials, `.env`, X tokens, or contents of `~/.xurl` are tracked.
- [ ] `SKILL.md` and `agents/openai.yaml` pass the skill validator.
- [ ] The repository homepage, clone command, package name, and skill slug all use
      `x-feed-loop` after the GitHub repository rename.
