# memory/ (Phase 1.5 + Hermes-lite evolve)

Lightweight listener prefs. Brief + Synthesize **read** these. After a call,
**Synthesize** can propose updates (Hermes-lite).

| File | Role |
| --- | --- |
| `USER.md` | Who the listener is; durable prefs |
| `TASTE.md` | Voice, depth, cite / recap style |
| `proposals/` | Suggested rewrites (gitignored); Apply from room UI |

## Evolve modes (`XLC_MEMORY_EVOLVE`)

| Value | Behavior |
| --- | --- |
| `suggest` (default) | After Synthesize, show proposal in the room → **Apply to memory** |
| `auto` | Write USER/TASTE immediately (keeps `.bak`) |
| `off` | No evolve |

On Render / `XLC_DATA_DIR`, live copies live under `$XLC_DATA_DIR/memory/`
(seeded from this folder once) so updates survive redeploys.

Do not put secrets here. Full transcripts stay in `sessions/`.
