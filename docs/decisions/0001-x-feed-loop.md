[//]: # (ob:95cd7af6)
# ADR 0001: Replace X-LiveCast with X Feed Loop

[//]: # (ob:e0d0d4d5)
## Status

[//]: # (ob:4107da7e)
Accepted — 2026-07-20

[//]: # (ob:2e754756)
## Context

[//]: # (ob:d1203a8a)
The original prototype combined a personalized X brief with a custom Gemini
Live voice room, web UI, public tunnel, DM delivery, cloud deployment, session
management, memory, drafts, and publishing. The prototype worked, but owning the
entire user journey created more UI, infrastructure, and security work than the
core problem required.

[//]: # (ob:ba3a6466)
The durable user problem is fragmented sensemaking: valuable reactions to X
posts disappear before they become notes or publishable ideas.

[//]: # (ob:ab72b092)
## Decision

[//]: # (ob:cfee4394)
Rebuild the project as X Feed Loop, a local, agent-native workflow.

[//]: # (ob:2ac7b4aa)
- Let the user's existing agent own conversation and reasoning.
- Let the official X skill own X reads and writes.
- Keep only deterministic local state and workflow instructions in this project.
- Persist Reaction Cards, drafts, and Taste/Voice memory instead of duplicate
  full transcripts.
- Keep daily scheduling optional and publishing explicitly confirmed.

[//]: # (ob:930c3b6b)
The legacy `x-livecast-skill` branch remains the Voice prototype. It is not part
of the active product or roadmap.

[//]: # (ob:b45a428e)
## Alternatives considered

[//]: # (ob:033077cc)
- The [official X skill](https://docs.x.com/tools/skill-md) is the upstream
  access layer. Reusing it avoids duplicating authentication, endpoint coverage,
  and publishing behavior.
- [x-bookmarks-digest](https://github.com/openclaw/skills/tree/main/skills/bearly-hodling/x-bookmarks-digest)
  turns saved posts into an actionable digest. It does not center a persistent,
  multi-turn reaction-to-draft feedback loop.
- [xint](https://github.com/0xNyk/xint) provides broad search, monitoring,
  analysis, and engagement tooling. Replacing the official access layer with
  another X client would expand rather than reduce this project's scope.
- [last30days](https://github.com/mvanhorn/last30days-skill) synthesizes recent
  signal across multiple public sources. Its unit of value is a research brief;
  this project's unit of value is the user's accumulated reaction and voice.

[//]: # (ob:52072355)
The missing layer is therefore not retrieval. It is local, inspectable state
that connects a user's lens, reactions, draft edits, Taste, and Voice over time.

[//]: # (ob:4a2f6bce)
## Consequences

[//]: # (ob:a7768a79)
The project loses its standalone phone/voice experience and provider-specific
demo. In return it has no hosted attack surface, no Gemini dependency, no custom
X API layer, and a much smaller cross-harness product surface.

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwX2E0YmEwZTU4Y2UxYmJhZTQ2MzMzODUxYiIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6IjU5OWJlNzMyIiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV9lNjBmMmFhOGVkZWU2MjczOTI1MmZjYTciLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsX2E2MzdkYWI5NmM1YjNiZmEyNmFiMWRlZSIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNq1WO2O27gVfRXC-6MNao_1LXv6K8iixaK7RZCmiwEygfeKpGzuSKIqUjPjBgH6EH3CPkkPKdmWk11nZ9ICQSBL5OX9OPfcw_kwo86qkrjdKDG7nrXthpKCApmuuAyLgmSSxXG8SsNiNp8VWuw3Qm2lsVhrdhSl2XVRlDISOQ_yoEiDSOYJz7I8lmkmE54WYSGiEmbKPErWa7GOaR2KdJ3KPMuygvIUdoUyXN_Lbj-7_uB-2I2lLU6oyLqj5ngoZIUXP8pOlYqKSrJO3iujdMN2WK-7PSv27HWnddl20hjsaYnf0Va6oM5ed_pniXD7zhncWdua6-Vyq-yuL664rpd8J5taNVtLzXYVB8uz3Z38R6_wvOmN7DZcN0Y2yIXtevlxPttJcklM1-tC5nE0G95s5L1fhOTKjcyCMiJaSSFlFuXxOkqjklPuPNOddaFtKtVIeH6oSLWhLM4FFesM-YyLkqKMihAGhnBG7zacWtNXCDhyfnLdCTO7fvdhNh7_YYYq6864p-GzFJsCKX8365u7Rj80s_eI4YAHHC00N0shuc-zWQZBEC4eF6WUYlFp3V7VYjZ_En7I2k4VvYW5TUFGGYciWZUbMkinld5eb3e6c07eqcaZNHtjZY0vDdWumgdn59hqnGez66avKrjOdyiZHIIuKs3vsHqdcpFTmWE5qmXlowvs5bdvmIvmmr2RbUVcspvF9-peviJj2QOgwG7Yn6R3Z3SChPA_Wwc7-YA337DfaoV9j2Rhr923zn8HCcBr9nF-8lIGIhCJSM-8_Jsl25uLPnzDjosuWE_CAPDJ5ROtv-RctigK-8-__s2iIMoWQb6IgtNZLXV0dhCaP03y9DzZr8any3GcVl0IRIRRENOKnmr_7U4y3amtaqhi6Bir3SEM3V6g1QQj1srOaHxV_8TPG1Z0SpZDDS-EW1BMWZJlz3FH9J2nMccjziU810wZVna0rdGvcAPUYmRNMLO9ZvdU9W7DBXeoyKMiWEdn7nw7tu8X0j9ZdiH_HL2fxOvkySe8kUWvKsEsIh8JmJGZ9sccRcApVOFhi_gXDVn0EnvQl_BGPC8Soif7s2DfS-u9cfn_nWHyEVME4Q6HM_AL0NFgJBlybMWoEZg4BIyokz8V9pz5s44DHhdZ8WR_HCIquSW-Zz89LioEzkEiC3OnquonoJEavsP5NanGeLd_1IrLAcqXAJqklESr88Z_WVnZDdk1LkijhOy-wHUgu1_ddQEvQRwHec75156_YC5B73RZKq7QwjfMZ-b97w_j202qq0c_vq3WlVn674tavGAXypVGQR7Fafq17jnnaoVZBPxUtEdDK1-lTpa6k6zRFrXD5JNo4iv2nXWfR6yrC9VLKCqzgstP6cVAg8iGS_NlSp0uvVAnyvNsRfn6WSe9nfR0pTGTmbKGGcgnQZVu8HGH_5f3HrHyEUyrnE3fUp9G_35-UCsz13tOJ3C03aAM_JeDzLiopJBxb3MUVGwUVAzSjt-1WjXW68POn-TEw-GX0w7vnRKrFN9PLEzV2cSI133PFG5Gl3ZTohKyazs16kNThNcoepAUSZytw3hFYS5X6ySMC7FOZJlGEV5CPWdpGSJ-zkkgchElIiZMo5Qi12xIvvU6b6jWdZhCHbk3s-MYX70Ngus0uQ7yP-AhcFN9zPhUwH6cvP3wf5WGHoqDdNuR2WF9npclLxPJo2KFBd7GRM2NKP2fyLDxRCAqjOSKojVfH06cKLPDiZdF12hLBAmJUMQiDI-2JjrsQDa_WWKNZhOKeYn6h9zTljc7UV0nFy_qqdFYWhQCIYsk4scMTyTWaOxrxBMx3uN2VrM_S1yp1G3jCsMGKsDFpZ6zB1mwv383Z21foOeY7ZtGghe__YEJ6eZgt58zXule4Hdb6b3TRnM2Kv_bpqYGDTe8rGWt3XLRUWnN3BOMN2t2CPyKjUQ1-v-guzsp5gzXETfuHXeDsm8bmMIFb9BlP-u-a-SejRzEakfnzlvVQKcZdD-3fSeHo4zkfafs3luGLWoGg9xtOii88f4orn69xKmkMpe4H6_WxaEqE6U5qcpzNaRTMtzJGkwpzW5um1YbUDYu3gRipY4Vw-CC-7hW46pY-yEGZtfdIaPeDkYjmQuhyIwDm1GYlkV4CGWiUk9ovSw_R2txKNZ5lJaBFMnB2kSRjta-Rmp2d2WlHy4EFMSl4DJYySQJju13EqGjC1-jLgHU2-Zk4FPJ4_feuMXC-G0PgJw0fs9fpGyZbqo9WgUaxjUcTuVDrG4g22HoHuIEigcIeyQoB1eAZ8yZt_jacT9Y9M2IF_aKOmHOO-wt-kAuBz06dKC3CwfhPCDaoq1x8m3DWIlJyyzErOGdau3Ea0EKbhuMVtFXLlG6defB7fMmdvoB9pTFamSwVF191ktHiTfWi5Jwla0wcCiIjzPkJNInvfRc9e0OPmg6J_SAGHvbIHK3zmXt3i8USLPrnk6TqKm9ADHo5TAOJQ_D_EjKEx1_6pknKfLReMQF51BK-erUQhORfsTv8-X2oHxZ3wJakmpXdsKQM2ZQxlfAUu-FskJbYhAAxgeM-AbpsRsMzH1jzJlshJdazP99EO0z9xbPQVHIHd0r3Xk8vXtcFFrf1dTdmcXwt8qT45M_8-kWKrSih8F3s4S7culKfHhRgAmr_WKnhUPk8nOzL5wr4H-AwtA9yGWgUXir4SEbWsbz5LDew0RoOQCFO4LuxukJ2LoR5gzWfWXVwpk90vTC6oVvOeYEVkH8jnmRNYSL834xwODxr_u7pfv8wiHwHvAwADMAiKlAHd9hYoJwLGZ7sx3TStUevgyNLZvtOFqZK7IfoYPCGmfliZymFfaDf7Cm3R0I6OGVclYedA9eRgd7uiP_0Y9JoLbn8ox-QJqGo0RDjBXaMQ4E7c0vRlrfU7PTXbM8rRua9wUz-wbnGCgTg2Nczp1rRm09t_BOw22f8RZlGjWIwdRHPK5chvXIkCMyNzulQzfBzpC_Qej80aPg3PXPNk1mAXLV40SvJw4F9vn2qugCl5UB7gHrsOShOA7TyQ12wmXPvYs2poX_HrF-Wtwid-RaD5qMWxf6GEMFVTE_qYhxIDAplJsKfiIMGBqI0rUus6qWF2gvTEXGgyJdZcFR9UwuwGfC9gu32oNcoIAnRRpzIcRRfJwuupN8Pff2OnZVt3B5U-iF20ZgAiKtDtO-hYEDuIO0sx3Iwalla13_mr7DzQhZwpdBGzt9C7aD8b1_Owjn2-aGvXz93VDKIacEwAJ8pqaqQl49hhc7glA15jhqRvufJfz9R_z7L-0GsE4)
