# Migrating from X-LiveCast

The legacy Voice Room implementation remains available in Git history and on
the `x-livecast-skill` branch. Run migration from a separate old checkout into
the new local data directory:

```bash
x-feed-loop migrate --from /path/to/old/x-livecast
```

The deterministic migration copies or adapts:

- `prompt.md` to `preferences.md`;
- `memory/USER.md` and `memory/TASTE.md`;
- legacy seen-state IDs;
- existing JSON drafts.

It does not convert briefs or full sessions. Those artifacts remain untouched
in the old checkout because converting them into Reaction Cards would require
semantic judgment. The command writes a report under
`~/.x-feed-loop/migration/`.

Review imported preferences and drafts before using them. Create `VOICE.md`
through normal use or edit its seeded template directly.
