# Local layout — where things live

Everything below is on the **host disk** (laptop / GCP VM), not on the phone.
Runtime JSON under `briefs/`, `sessions/`, `drafts/`, `bundles/` is gitignored.

## Conversations (UI + disk)

| | |
| --- | --- |
| **UI** | Top bar: thread dropdown + **New**. Pick a past thread → transcript reloads → button becomes **Continue** (new Live socket + history). Hang up keeps the thread; it does not delete it. |
| **Disk** | `sessions/<id>.json` (+ `sessions/latest.json` when written). Autosaved during the call; finalized on hang-up. |
| **Not stored in** | the browser (except optional `sessionStorage` for `?token=`). |

## Briefs

| | |
| --- | --- |
| **Current** | `briefs/latest.json` — what the host reads on a fresh Start |
| **History** | optional timestamped copies `briefs/YYYYMMDD….json` (harness may snapshot) |
| **Written by** | agent harness / brief recipe (not the room UI) |

## Post drafts (Synthesize)

| | |
| --- | --- |
| **Yes, local** | `drafts/<id>.json` and `drafts/latest.json` |
| **When** | each **Synthesize** writes a new id + updates `latest` |
| **After publish** | same files gain `published_at`, `tweet_ids`, `urls` |
| **UI** | draft panel is in-session; switching threads hides it — reopen via Synthesize or open the JSON on disk |

## Taste / user prefs — **not** auto-updated

| File | Role | Who updates |
| --- | --- | --- |
| `prompt.md` | What the brief covers + tone | **You** (or bundle import) |
| `recap_template.md` | How Synthesize should write posts | **You** |
| `memory/USER.md` | Who you are / durable prefs | **You** (Phase 1.5 scaffold) |
| `memory/TASTE.md` | Voice / depth / cite style | **You** (or bundle import) |

The room does **not** write these after a call. A future harness step may suggest edits; v1 is curated files. Transcripts stay in `sessions/` — don't dump them into `memory/`.

## Bundles (CLI / host)

`python3 scripts/bundle_tools.py export|import` → `bundles/latest.json` (+ timestamped). Packs `prompt.md` (+ optional taste). Not in the room UI.

## Seen-bookmark state

`.state/seen.json` — ids already briefed (`bookmarks-new` / `mark-seen`). Gitignored.

## Secrets

| | |
| --- | --- |
| **`.env`** | `GEMINI_API_KEY`, port, model, voice, always-on URL/token — see `.env.example` |
| **Not in `.env`** | X OAuth — `xurl` stores under `~/.xurl` |

## What belongs where

| Put in **`.env` / `.env.example`** | Keep as **editable docs / markdown** | Keep as **references/** |
| --- | --- | --- |
| API keys, ports, model ids, voice, `XLC_PUBLIC_URL`, tunnel mode, room token, synth model | `prompt.md`, `recap_template.md`, `memory/*` | schemas, always-on setup, this file, config encyclopedia |

Operational how-tos (xurl auth, Cloudflare tunnel, testing): `README.md`, `references/always-on.setup.md`, `TESTING.md`, `SKILL.md` — not env vars.
