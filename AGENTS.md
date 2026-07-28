[//]: # (ob:ce3c9822)
# AGENTS.md

[//]: # (ob:ab2c3cb5)
This repository builds the **talk-to-my-x** Codex plugin.

[//]: # (ob:ce79c07b)
Read `plugins/talk-to-my-x/skills/talk-to-my-x/SKILL.md`; it is the workflow
source of truth.

[//]: # (ob:a0922a14)
- Use the official X Skill, xurl, or official X MCP for every X read and write.
- Never add raw X API calls, model calls, a chat runtime, or a web service.
- Keep local posts, Reaction Cards, drafts, actions, and memory in the bundled
  state engine only.
- Preserve source URLs and the user's transcribed raw reactions.
- Never perform an X write without exact preview and action-specific approval.
- Run all unit tests plus both Skill and plugin validators before release.

[//]: # (ob:81215557)
<!-- proofpress:setup:start -->

[//]: # (ob:71d7edab)
## Proofpress: ledger Markdown and static HTML knowledge artifacts

[//]: # (ob:5a57536d)
For accepted, meaningful revisions to Markdown or static HTML knowledge
artifacts—never source code—close this loop. Do not snapshot every
conversational turn.

[//]: # (ob:35c81ace)
Before editing an existing target, run
`npx --no-install proofpress capture --recorder codex-preflight <file>`. This
preserves any human drift as a separate version without guessing its author or
reason. Then:

[//]: # (ob:a3e2daec)
1. Read `npx --no-install proofpress policy <file>`. If the user asks for portability,
   run `policy <file> portable` once; it remains sticky. Use `ingest <file>` for
   Git history not yet represented in the ledger.
2. Preserve carrier-native block anchors while editing: Markdown uses invisible
   `ob` markers; static HTML uses `data-proofpress-id`. Then run `anchor <file>`
   and inspect inherited/new/gone IDs.
3. Write claims JSON with one honest item per touched or removed block. Do not
   enumerate untouched blocks.
4. Snapshot with `--why`, claims, and explicit actors:

   [//]: # (ob:fb0187c9)
   ```sh
   npx --no-install proofpress snapshot <file> --kind agent --author codex \
     --produced-by codex --recorded-by codex \
     --attribution-basis harness_attested --note "<changelog>" \
     --claims <claims.json> --why "<actual reason>" \
     --rejected "<consequential dead branch — reason>"
   ```

   [//]: # (ob:e8212944)
   Omit `--rejected` unless the dead branch matters later. Never infer it from
   casual discussion or capture raw prompts/transcripts.

   [//]: # (ob:03115feb)
5. Run `verify <file>` and report its output verbatim. Never re-snapshot just to
   force green.

[//]: # (ob:1bfb5541)
For an incoming file with a `proofpress:discovery` marker but no local CLI,
tell the user it carries verifiable revision history, show the marker's
canonical project URL, and ask whether to install `proofpress`. Never
download or execute it without explicit consent. If the CLI is available, run
`inspect` before trusting the capsule and then `import`.

[//]: # (ob:10e74dfc)
For parallel portable copies of the same artifact, keep every original and run
`merge-plan TARGET --from COPY...`. Apply compatible block changes, ask the
user only about reported semantic conflicts, then `anchor` the resolved target,
write merge-relative claims, run `merge TARGET --from COPY...` with explicit
actors/reason, and `verify`. Use `merge-lineage`, not `merge`, when artifact IDs
or portable lineages differ.

[//]: # (ob:df90cbac)
Fallback `capture` records only `recorded_by`; it cannot know authorship or
reasoning.

[//]: # (ob:8e231f54)
<!-- proofpress:setup:end -->

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzhhZWQzOTczN2Q1NjllNGNiMGY4OGUxOCIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6IjVhMzBiYzUzIiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV8yNjNlZWZjYTJhYzAxOTE3OTc1YzcxMmIiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsXzQ1ODhlNjIzYmVhZTk4OTQ1NzkzNmM3NSIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNq1We2O28YVfZWp8iOAK2n5IVKkYgRwnTZ14yRG7LQpokAczgwlRtSQ4ZC7KxgG-hB9wj5Jzx2SEte1ldq7Bow1Rc3cuZ_nnjt6PeF1k2dcNJtcTlaTqtpEXEk_XvpLGYSxWojUyaJIudFkOklLedzIfKtMg7Vmx70gXAkvDJ005K4bcS9b8DCKo3iRZnEWBZGz5AseR1HkhUEmQ8kD4apgEThKOpkrpQg55MrciPJa1cfJ6jV9aDYN3-KEgjd01BQPqSrw4u-qzrOcp4VitbrOTV5qtsP6sj6y9Mhe1GWZVbUyBnsqLvZ8q8ioO6_r8lcFc9uaBO6apjKrq6tt3uzadC7Kw5XYKX3I9bbhehv5ztWd3bX6rc3xvGmNqjei1EZp-KKpW_VmOtkpTk4MuO-kIvAn3ZuNuraL4Fy18UJfqUxwjwvHjd1lvAzE0vVS0qysGzJtU-RaQfMhIsVmESACoeeniitybrCM_VAsg86cXruN4JVpCxjskZ6irKWZrH5-PemPfz1BlMva0FP3tZKbFC7_edLqvS5v9OQX2DDkA45-8vWfv3v1cn6Qk-kHpQlvmjpP2wbR2aTc5IaSRRXZhht4rVFWXtvsypp02eeaRJqjadQB32h-oKANOk2x1VCgJyvdFgU0FDtERnW2pUUp9lgtlC_iyPOwHEFp1O3b-vencCnt8RWlj7rBm8_YeFlzrOhwChtSYPJmej6Cp57wRRp8-BGvkKLI16o0eZepbV5Iw5qdYo8eNbzYz5pydjjObh89Yk9LqW5ZVbTbXM_PClW85ne0EWoZC2eZfrg2P8A2lnQnmKvx8VdmnxfFW-9efvPs-XOITL5geXNBIe7EnsfdxYcrNGM_GmW9UWZZLnJesJ_YS1Jlym5RplNW1uOvvn36gmV4hbyuzwoVgIE7CkWu5wZBsPxwhR7_YTZj58JaGdW01co0qAE2m315wQlLVy6V5HejckalFSuU3KqafcvrvUR2M64lg-AmF-yvF7P0M_b_inn17XNGpWPXMOh8Oa0DHiwDP5QPrvJfECIuhKpQ8FN2UFzj6KwtTsiNCijPYrH6bMEFF_uBiFwu1IPr-yeFpFJMybyBotjG1C1yip4R-a1qpqxu9VonurpFGuhyhvpBqRSUKpcKw1ee5Eo8uMLunHW1_C6FeumsKotcHNnjLC_Ul8mcPctspV2omyx13Ggp4gfXlzGWJInZrTWeLulsNDrZrmx6rbFun58VFkDIOwqryHO9eLH4FAp_f8gblsxmtSLSoGTCWl2QjuRESd5Pa67Fjh3Q9FRtGFGWes6-u5AQju-6QaYeHiQCJESrWXJNLOkUc7udug_QK28MK9umahuGRSlEHqDr7wCpm2ZpECzcT4MQmuUatIvKjPRlN2BijKNBnQ840cMEbq73OCptL_jXddRyITPxSfSl04pCIV97tsZEWeUKbu0Ky4C9sIEsTdleqeqtRvU_-sosdkTKP4G-0BRy9ywBNWzaWiWs54Ws1MWRJSMaaNs7E1xr1B3axwV9I-X5bhY8fL29u-8q7H5H1_1lOhDbCdxL_WQjasU7dmm_GajqRdINc63MIZo992aYAsS-KnPd2FGiticRAR0-Ef_8hUg74etIwpjIj4TYEeEjOb4ps2aToUJUXdV5P0qY1F2BAMowjlS8CCPH96Jw4XgLfxF67lIsF2HsOI6PWct1fTeIFosodVMZ4ZMSqGfpOiQbcbEjQReOlRuCYdObied44cxZzrzoleOsAn8VxH_Eg0O7eo-PZ503o7evH2KKsOnWsfwdNzt7VhjEbub5nkMLrIwR8e8z8XcJfS8tjfwoixaZ60p_kDbi-L20h-Tu_cHLhe9HQSpjT4RnM050vj_4PjSd5Z2GN2W9z4ryZq1N2dZCWZCqMXld0E4pKTIvjEKVipNbzty-1-4-nP2IzzVZR7hwU-eNmq_1rGtDDGnIan6DJU9ePAMewVCQRzi2GD5w1CZviIuheyl7EGc3KmWYLa9z0Qn7hnAXCcQJqE2DbfCnoImUPeUAwCmTNc_offeWHqDNQR0oyLm2pqWtlsAy4itUJuCGGsFQFjztKS8AUzgUqN-598cfnhsrh3bTDcHniAP4gRGYh1VnWN3rYUZGV6qGcw7UDH_qPGLbIDo1OCiWsx4jrexu-8xUSuTwL-MVIPOaF1Ye9X9iU61GFtDliaF8NCwt0VVtfKyMLq0YduWS06UASzv2W6tCcaPm76ADfX5wmXqhDBUPQ2_Ij9Go1efHh49Qg3ieRX4cZwvXU4P40VQ11Pg9xiELQOYiNMSABJVFQSjSbFBiNCf1StxnwBnptNYnpf7zr39rmxB9PhHVxTtRlLbYUNVFWVZz9lXJqE2feLKtqjVolCYI5pQfSHx0_Esw5AE6fbWIYs5PgRwNV72R95qKBkLf0w9GPNoyjtqadjvD11mRb3fNeUAhwF3rqq8sKqcj27UHHCzBahvG8QqlTtagTPqWcyqXbUuXRVCOmG53xwTHrzWqzpSapCu9er9PglT4Pg-5dOQJmkfzW--T-wxehAqwYW8sHHZ0IC_y5ji1Y1FN_P3O1hPRTIA7Qll4r9WB40jkUy72x7nF4oT4gTk5ksRbiV9j_XBFSklzVLTf-hfcTQ5Y15UQMMSbn2FN8LrOVT3TSCl8tB2Z0bhDiHGzI7reJ8bqnOew0EAqlQC0tjokZTpQd_PFnSqwixNgEJ-dfTfLZdKFqvNHd-JgmZVIFQ4PAAPR7PROEWbKK61urrYlEPrZVwSv_pz9w4KpKHh-MOxvL7__rpsvaM0OfwyNROpAAIxabcHXJNUp_It5Q3YGD-Vmz1W6PSibeWg__YaOqOC8xZy9HErSHoPB8WZ3TKa9Al2PUbcVwouodNexq_dDreunAnNilHHvlI2j6bzPxnuN1dRPtkgEfOirxRYmW6-tOIb3kCBboeQsPfZfnsp49G60YXT9O7PXv2zHa0031DQjG0o6UhE-XE8ed5e5Rbn9cj0ZC-lD9rj7f_4rqpc0hjtpF1zXcgJaquq3dg6jupVOF_S_tTCQaMh4Xgesnrd3SZok77hk6EOxiEDX_NDJhDhRz9G9wzkUH31hYHE_1xn9bVhWlwerleCGLKURuLXX4JSfA54Sn0B4DlUDNtjzDDxfAP0oW8pl6vGF5KfONrqP6O24z0UCVsxOmfZriwprSmsJAAktbVsrpS_QC4UW5EgeRn5wYuWjC4hx6_3Im4MGxdxTw6fPnwF2G4U6OWGznYIJ9gy7fv-vTVMG-27srk7w52hamJ5LnVvO2f3IRISwK3ogPgBTYT0BDRuqc6Rr0vtvrQlFi5JbJFK3SrSolLwZMcIeP_pfn06tBdYQ8efXPC9I6aEz9ziZDBwPE0DfwHcE8fZHo4G1Iuj5gSKcXEginrqx8CPpRF5witH50mUUo4-9LTnC9hwMlXd0tbMDwLtVs6pA4F89-eHrP79CsVOdsKffv_jnfD6HB59gkiZEOlTISDqua1n9L0ZTGwacu9Y21PYShKfk1C6tARoGrVVTe4J3QU0EjQidX7oulFi9EbCyoA7Rc6C17lh7pyJIdNcwB9i3Xcx-9x7Nu9wdIgtGaFvDVQdQXQb1xZj03b47qb9FQIeh1t69xIcbUnhwKzXDtT6RjfMdhwGqZMCbC5GOFyII_Bj1Z9m3jfToumqI9D3umW56lmZ2eTViakjPC2oJHmYBsi10U36aQc63UhdnkPddJ73Bv_8CXoRl5A)
