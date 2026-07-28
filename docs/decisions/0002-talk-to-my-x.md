[//]: # (ob:f716048a)
# ADR 0002: Package the loop as Talk to My X

[//]: # (ob:4351bab1)
## Status

[//]: # (ob:5d081d54)
Accepted — 2026-07-27

[//]: # (ob:f64f6cbb)
## Context

[//]: # (ob:d59f018c)
Codex now provides GPT-Live conversation and iPhone Remote access to the same
local projects, plugins, credentials, and tools. X provides an official Skill,
xurl CLI, and authenticated MCP bridge. Rebuilding either runtime would add
infrastructure without strengthening the personal feedback loop.

[//]: # (ob:fe98ec2a)
## Decision

[//]: # (ob:54462b10)
- Present the product as Talk to My X and target Codex v0.1.
- Package a workflow Skill, the official xurl MCP bridge, and a local state MCP
  in one installable plugin.
- Use official X tools exclusively; use simple xurl shortcuts for write actions
  not exposed by the current X MCP catalog.
- Keep plugin data local and migrate prior supported state without deletion.
- Record a ten-minute action preview and require an exact action-specific phrase
  before each X write.

[//]: # (ob:c9e49d05)
## Consequences

[//]: # (ob:92f7606c)
The product is usable from iPhone Voice while the paired Mac is online, with no
custom voice or web service. Public beta users must configure an X Developer App
and credits. Cloud-only hosts, Android, other agent providers, and automatic
publishing remain outside v0.1.

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzRhY2FiNDM2NGM5ZmViNjBlMjVlZWJiZSIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6IjQ0YjMxZTcyIiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV9lZTY3ZGMwNjQwMzFhMTYwODEzODhjNjMiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsX2M2NGFjOWU5ODU1MWJhMzQ5ZTIxODY1NCIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNq1V9uO2zYQ_RVCfay9q7sl9ynYAkXRBlikaRGgGxi8DC12ZVIlqc0aiwD9iH5hv6RDSr5s0DpNggJ-kKnh3M7hGeopodYrSbnfKJGsk2HYlJRTVhZ1yVsJrE4hrwAYg2SRMCP2G6G24Dzauo7mVb1e1UW2Em1e0CItKMvKVVOkYsWymjUVk7ko0jyvWVu3LIWKUijrgvKiyJpc1Lxp0K9QjpsHsPtk_RT--I2nW4zQUx9CLfCBQY8Lv4BVUlHWA7HwoJwymnRob-yesD25tcbIwYJzuGeg_J5uIRT1bNma3wDLHW1w2Hk_uPX19Vb5bmRX3OyueQd6p_TWU73FSq6f7bbw-6jweTM6sBtutAONvfB2hPeLpAMamliWrMhglSfTygYeohE2FzYA9UrwtC7TIqNZnTZZ0TS8LkJmxvpQ2qZXGjDzAyL9htcISgttU1UZo0XZQp41dVVO5czZbTgd3NhjwXnIkxsrXLL-9SmZwz8liLKxLjxNr0FsGLb812TU99q808lbrOHABwwtDHfXAnjss7tO0zRfetrfL71Z7vbLx6udSBafRCDqvVVs9Ohvw6hTLtAIermhDvvpIfobfWdsyPJe6eDS7Z2HHb7RdBfgPGS7wK0upJas9dj3mDvvEDOYqma94fdoLVfY5bKhaI5weXgMlb349hUJ5azJ7cQS4jsgvTEDoY68xhqJN-TlHjfNSVAhYnZD4B28w5WvyH_1Qt7gRr8fQvKBEEiu5P3ilGJZBFhZ9izFnzz1o7uYwFfkaHTBeyWQZCKS5VO8v-AcBkSE_PXHnyRP83qZrpb56hRroJY-CyTrUtacsWeBbuany3WcrC4UIqpWplnDP9X_jRHwSJAyBA_LgxLgyHe3r5c_qgcg6Ah1x9HASEK1IOq2MxrIK9gZD4ReKhfPI_D8ObG-nU_LR-o9M7uEXFnWOcvST46wRCWEoEyRkFi1GLn_kJOxXE_tFjyZWvSQXmVXp5R6FNZn-aAEla1Iqw8BcCiKoDm4j6N8bnqh8jaXqzqt-WdFen1Ws3JkdHFeSGt2B3R_MYoDedepfjqyA0VNF-Ql5R_i_XZxkM8k8CToFrdAJ6WKbw6yd1HaNZIpWM0KT2aFJzhr-P1glPZxYNkYKYjZ4V_QsrdhNPSK7888nI-LMydxEH3mJHFG-o1EJMAOVs0Dy7FsLZqMyrRIZU1X7arMq5LnpUzrNhWiqmRd54Kt0lQUOWtZjraNaCrO67phdVE0MvhGuYmDZ0Jr3aJYh4XkKCzN6zRdV-U6bb7GhzRwfm74-UB9f7b69P-OqkjFaZR01HVoD1WTVc2qymUWjkD0cTZdZpZ--Vg4hKvTLIeG5i1vD-HOJsUh3OUhMPtKGSvqRrZZ1hx9nc2Fw1T8z5I_uy1pwWXVVhmvTh05TYFTihf1fXaGl8ECyiKTBZMHZ2eSfxSBzxdzLM-50PuAh8PLxJ1GkGlP5juhW5ChH7dK4wOecoHnT9Ee_0SlNKZ3Vyibx7hUEyOl4mhDfrpXeGjv9CNeK8nNj99Pe8JVJjjhQTDIy5tbwqwSW7jClNio-tACAnj1BEvsiIY7VCUz9rhTiDuttLTU4ZHmfrT4Bg3N6AmuAF5P0XPYHvULqzYa05AAgiHpItuu_h04qDkgkbNKRi5NwJ3m2Qm4y4Nq9ibzBjWgWOFwoEd2nWbX7O1LhtKdXh4PE8UW2XvZIwWmrkd_RyQiAqdWz0CQCeigQxDe3mlCFOKH7EC4USn6qMsT_DHcz-7M6ZsJfgKPvB8dcq3ff4ODBVmkdgPui0EdXls9H70j0ljyzqrIuUBGF8LhDMD9g3FIBfxWCUnz0QaRR_chYWQJ7c02Rv8BYJizIQLX5_xDLTu1taEKFGkM48YhqD36nGo7kERADyF09PYqXvexCx70Er9txmNmZB6b0fP8cROIDY80gBNtlm5AFmAnyNAhHyEUwwBrBAKUd5h9rPWfbg4zQbIKD3fKqqZO2YEgZ5eJZzrxkRvCwSMr8oo2LaPZUdDOLg2zxy-5CYQNRocBuohNRfzuNB_xW3NHHuKuADIwgh8uD_j3ityODKc0tgbhCp-HjuzQPKiSVNtx6usbPFHIHoMnlrwYhjsd-h60RnkUl5vejGKJUfekMy7o0QstrFFiQUwUCeQ_0mVWIOuOKmN2KHr8Tg8hBdcFXbCwo4HhyEe0_fBuN99u3uPvb1LMO68)
