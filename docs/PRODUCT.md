# Product definition

## The problem

X contains a lot of signal, but reading and reacting happen in fragmented
pockets throughout the day. Questions, connections, and half-formed takes end
up scattered across memory, notes, and unrelated AI chats. By the time someone
sits down to write, the original reaction is often gone and the thinking must be
reconstructed.

## The product

X Feed Loop is a local agent skill that preserves the path from reading to
thinking to publishing.

- **Configurable lens:** select posts using explicit topics, rationale, angles,
  definitions of good signal, and ignores.
- **Reaction memory:** keep raw reactions, sources, questions, and connections
  in portable Reaction Cards rather than another full chat archive.
- **Conversation-to-draft:** produce posts from the user's actual thinking, not
  generic feed summaries.
- **Self-evolving loop:** use selection behavior and draft edits to update
  reversible Taste and Voice memory.

The visible output is a post draft. The compounding asset is the local model of
what the user notices, how they think, and how they write.

## Product principles

1. The feed is input; the user's reaction is the product material.
2. Preserve raw wording before summarizing it.
3. Keep every reaction grounded in its original source.
4. Reduce note-taking work; do not create another inbox to maintain.
5. Prefer explicit preferences over inferred memory.
6. Keep state local, inspectable, and reversible.
7. Draft automatically; publish only after explicit approval.

## Ecosystem boundary

The [official X skill](https://docs.x.com/tools/skill-md) already supplies
Timeline, Bookmarks, Search, Read, Post, and Reply. Projects such as
[x-bookmarks-digest](https://github.com/openclaw/skills/tree/main/skills/bearly-hodling/x-bookmarks-digest)
focus on actionable bookmark digests;
[xint](https://github.com/0xNyk/xint) is a broad X intelligence CLI; and
[last30days](https://github.com/mvanhorn/last30days-skill) performs recent,
multi-source research. X Feed Loop does not replace those primitives. It
supplies the personal feedback layer between feed interaction and authored
output.
