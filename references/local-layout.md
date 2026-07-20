# Local data layout

X Feed Loop stores inspectable files under `~/.x-feed-loop/` by default. Set
`XFL_HOME` to use another directory, including a disposable test directory.

```text
~/.x-feed-loop/
├── preferences.md
├── memory/
│   ├── USER.md
│   ├── TASTE.md
│   └── VOICE.md
├── posts/                 # normalized X posts, one JSON file per ID
├── reactions/             # portable Reaction Cards
├── drafts/                # current draft plus immutable revisions
├── history/memory/        # before/after snapshots and rollback records
├── state/                 # migration compatibility state
├── exports/               # optional user-created exports
└── migration/             # migration reports
```

The CLI creates Markdown templates without overwriting existing files. JSON
writes are atomic. File IDs accept only `A-Z`, `a-z`, `0-9`, `_`, and `-`, with a
maximum of 160 characters.

This directory may contain private source text, unfinished reactions, and
writing memory. Do not commit, sync, or share it unless the user intentionally
chooses to. X credentials are not stored here; they remain owned by `xurl`.
