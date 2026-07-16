# Local layout — where things live

Everything below is on the **host disk** (laptop / Render Disk / VPS), not on the phone.
Runtime JSON under `briefs/`, `sessions/`, `drafts/`, `bundles/` is gitignored.

On Render, set `XLC_DATA_DIR=/var/data` (and preferably `HOME=/var/data/home`). Then the
paths below are under that root instead of the repo checkout.

## Conversations (UI + disk)

| | |
| --- | --- |
| **UI** | Top bar: thread dropdown + **New**. Labels show title · time · turn count. Pick a past thread → transcript reloads → **Continue**. Hang up keeps the thread. |
| **Disk** | `sessions/<id>.json` (+ `sessions/latest.json` when written). Autosaved during the call; finalized on hang-up. |
| **Not stored in** | the browser (except optional `sessionStorage` for `?token=`). |

## Briefs

| | |
| --- | --- |
| **Current** | `briefs/latest.json` — what the host reads on a fresh Start |
| **History** | timestamped copies `briefs/YYYYMMDD….json` (generate snapshots the previous latest) |
| **Written by** | room **Generate today’s brief** (`POST /brief/generate`), `python3 scripts/generate_brief.py`, or the harness recipe in `SKILL.md` |
| **Fallback** | if no `latest.json`, room serves `assets/sample-brief.md` (UI badge: Sample brief) |

## Post drafts (Synthesize)

| | |
| --- | --- |
| **Yes, on disk** | `drafts/<id>.json` and `drafts/latest.json` |
| **When** | each **Synthesize** writes a new id + updates `latest` |
| **After publish** | same files gain `published_at`, `tweet_ids`, `urls` |
| **UI** | **Drafts library** dropdown (`GET /drafts`) → load into the draft panel; or Synthesize in-session |

## Taste / user prefs — **not** auto-updated (this release)

| File | Role | Who updates |
| --- | --- | --- |
| `prompt.md` | What the brief covers + tone | **You** (or bundle import) |
| `recap_template.md` | How Synthesize should write posts | **You** |
| `memory/USER.md` | Who you are / durable prefs | **You** (scaffold) |
| `memory/TASTE.md` | Voice / depth / cite style | **You** (or bundle import) |

The room does **not** rewrite these after a call. Evolving taste memory is a later PR.
Transcripts stay in `sessions/` — don't dump them into `memory/`.

## Bundles (CLI / host)

`python3 scripts/bundle_tools.py export|import` → `bundles/latest.json` (+ timestamped). Packs `prompt.md` (+ optional taste). Not in the room UI.

## Seen-bookmark state

`.state/seen.json` — ids already briefed (`bookmarks-new` / `mark-seen` / generate brief).
Under `XLC_DATA_DIR` when set (same volume as briefs). Gitignored.

## Secrets

| | |
| --- | --- |
| **`.env`** | `GEMINI_API_KEY`, port, model, voice, always-on URL/token — see `.env.example` |
| **Not in `.env`** | X OAuth — `xurl` stores under `~/.xurl` (on Render: `$HOME` → `/var/data/home`) |

## What belongs where

| Put in **`.env` / `.env.example`** | Keep as **editable docs / markdown** | Keep as **references/** |
| --- | --- | --- |
| API keys, ports, model ids, voice, `XLC_PUBLIC_URL`, tunnel mode, room token, data dir, `XLC_XURL_*` | `prompt.md`, `recap_template.md`, `memory/*` | schemas, always-on / Render setup, this file |

Operational how-tos: `README.md`, `references/render.setup.md`, `references/always-on.setup.md`, `TESTING.md`, `SKILL.md`.
