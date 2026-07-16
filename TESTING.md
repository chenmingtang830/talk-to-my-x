# X-LiveCast manual test checklist (v1)

Use this before tagging a release. Check boxes as you go. **Do not commit `.env`.**

## Local basics

- [x] `cp .env.example .env` and set `GEMINI_API_KEY` (if not already).
- [x] `python3 scripts/voice_room.py` opens `http://localhost:8787`.
- [ ] **Start** → allow mic → host speaks / brief appears as a DM-style message.
- [ ] Barge-in: talk over the host; it yields and answers.
- [ ] **Hang up** keeps the transcript; **Continue** resumes the thread (new Live socket + history).
- [ ] **Synthesize** writes `drafts/latest.json` and shows an editable draft; **Copy** works.
- [ ] Synthesize does **not** post to X.

## Publish (Phase D) — confirm required

Requires `xurl` with **tweet.write** (often OAuth 1.0a Read and Write).

- [ ] Edit the draft textarea; **Publish to X** → **Cancel** confirm → nothing posted; no new `tweet_ids` on disk.
- [ ] **Publish to X** → **OK** → single post appears on X; `drafts/latest.json` has `published_at`, `tweet_ids`, `urls`.
- [ ] Thread draft (paragraphs separated by a line containing only `---`): publish → reply chain is correct on X.
- [ ] `python3 scripts/publish.py publish --confirm` without auth / without write scope → readable error (not silent success).
- [x] `POST /publish` without `"confirm": true` → 400 / refuses to post.
- [ ] Re-publish same draft without clearing `tweet_ids` → refused as already published.

## Always-on (when you have a stable HTTPS host)

See `references/always-on.setup.md`.

- [ ] Set `XLC_PUBLIC_URL` + `XLC_TUNNEL_MODE=named` (or `none` behind your own proxy).
- [ ] `python3 scripts/voice_room.py --share` does **not** print a new `*.trycloudflare.com` URL.
- [ ] `curl -fsS "$XLC_PUBLIC_URL/health"` returns ok.
- [ ] `bash scripts/ensure_room.sh --dm` DMs the **same** evergreen URL (not a random tunnel).
- [ ] Phone: open DM link over HTTPS, mic works, Start connects.
- [ ] With `XLC_ROOM_TOKEN` set: request without token → 401 on `/config`; with `?token=` → works.

## Demo path (no public URL)

- [ ] Unset `XLC_PUBLIC_URL` (or `XLC_TUNNEL_MODE=quick`).
- [ ] `python3 scripts/voice_room.py --share --dm` still DMs a temporary trycloudflare link (demo only).

## Feed bundle (Phase E) — host / CLI only (not in room UI)

- [x] `python3 scripts/bundle_tools.py export` → `bundles/latest.json` looks right (prompt + focus fields).
- [x] Change `prompt.md` slightly → `import bundles/latest.json` restores prior content and leaves `prompt.md.bak`.
- [ ] (Optional) Confirm-post a short intro tweet about the bundle — only after explicit confirm.

## Regression / safety

- [x] `GET /health` works without room token.
- [ ] With token on: `/config`, `/publish`, `/bundle`, `/session(s)`, `/draft(s)`, `/tool`, `/synthesize`, `/brief/generate` require token.
- [x] `git status` does not stage `.env` (`.gitignore` covers it).
- [x] Links in README / SKILL to `references/always-on.setup.md` and `TESTING.md` resolve.

## Render / cloud (Mode A)

See `references/render.setup.md`.

- [ ] `GET $XLC_PUBLIC_URL/health` → `ok` + public URL.
- [ ] Disk mounted at `/var/data`; env has `XLC_DATA_DIR`, `HOME=/var/data/home`, `XLC_TUNNEL_MODE=none`.
- [ ] Build installed `xurl`; Shell: `python3 scripts/x_tools.py check` shows a binary path.
- [ ] Room UI badge is **Sample brief** until generate; after **Generate today’s brief** → **Live · bookmarks** and `briefs/latest.json` on the disk.
- [ ] Session dropdown lists prior threads with title · time; **New** works from idle and mid-call.
- [ ] **Drafts library** lists Synthesize drafts; selecting one loads the draft panel.
- [ ] In-room tool call works (ask about a post / bookmark) once xurl is authed.
- [ ] With `XLC_ROOM_TOKEN`: `POST /brief/generate` without token → 401.

## Smoke commands

```bash
python3 -m py_compile scripts/voice_room.py scripts/publish.py scripts/bundle_tools.py scripts/x_tools.py scripts/generate_brief.py
python3 scripts/bundle_tools.py export
python3 scripts/publish.py publish          # should refuse without --confirm
python3 scripts/x_tools.py check
bash scripts/ensure_room.sh --help
```
