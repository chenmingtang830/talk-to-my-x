# CLI payload contracts

All commands that accept `--stdin` read one JSON value from standard input and
return JSON on standard output.

## Normalized post ingestion

```json
{
  "posts": [
    {
      "id": "1900000000000000000",
      "text": "Post text",
      "author": "alice",
      "name": "Alice",
      "url": "https://x.com/alice/status/1900000000000000000",
      "source": "timeline",
      "created_at": "2026-07-20T12:00:00Z",
      "metrics": {"like_count": 12}
    }
  ]
}
```

Required per post: `id`, `text`, `author`, an HTTPS `url`, and `source`. The
source must match the command's `--source timeline|bookmarks|search` value.

## Reaction Card capture

```json
{
  "id": "reaction_optional_existing_id",
  "sources": ["1900000000000000000"],
  "raw_reaction": "The user's wording, preserved before interpretation.",
  "summary": "Optional grounded summary",
  "stance": "Optional stance",
  "questions": ["What assumption changes here?"],
  "connections": ["Connects to the user's earlier distribution thesis"],
  "status": "developing"
}
```

`sources` and `raw_reaction` are required. Sources may be ingested post IDs or
objects containing at least `id` and an HTTPS `url`. Reuse `id` to extend a
card. Status is `open`, `developing`, `ready`, `drafted`, or `archived`.

## Draft save

Single post:

```json
{
  "id": "draft_optional_existing_id",
  "text": "A post of at most 280 characters.",
  "sources": ["1900000000000000000"],
  "card_ids": ["reaction_optional_existing_id"]
}
```

Thread:

```json
{
  "thread": ["First post", "Second post"],
  "sources": ["1900000000000000000"],
  "card_ids": ["reaction_optional_existing_id"]
}
```

Exactly one of `text` or `thread` is required. Every post is at most 280 Unicode
code points. Saving an existing draft ID appends a revision.

## Published result

After an explicitly confirmed write succeeds through the official X skill:

```json
{
  "tweet_ids": ["1900000000000000001"],
  "urls": ["https://x.com/alice/status/1900000000000000001"],
  "text": "The exact final published text",
  "published_at": "2026-07-20T14:00:00Z"
}
```

For a thread, pass `thread` instead of `text`. This command records a result; it
does not publish.

## Memory apply

```json
{
  "taste_md": "# Taste\n\nComplete updated document.\n",
  "voice_md": "# Voice\n\nComplete updated document.\n",
  "evidence_card_ids": ["reaction_optional_existing_id"],
  "rationale": ["The user repeatedly selected first-principles critiques."]
}
```

Both complete Markdown documents, at least one existing evidence card, and at
least one rationale are required. The returned snapshot ID can be passed to
`x-feed-loop memory rollback --snapshot ID`.

## Preferences export/import

`preferences export` returns a versioned JSON bundle containing
`preferences_md`, `user_md`, `taste_md`, and `voice_md`. Pipe that value to
`preferences import --stdin`; the CLI backs up files before overwriting them.
