[//]: # (ob:d6de004a)
# Testing Talk to My X

[//]: # (ob:182eaed6)
## Automated release checks

[//]: # (ob:bdb51524)
```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins/talk-to-my-x tests
python3 /path/to/skill-creator/scripts/quick_validate.py \
  plugins/talk-to-my-x/skills/talk-to-my-x
python3 /path/to/plugin-creator/scripts/validate_plugin.py \
  plugins/talk-to-my-x
npm install
npm run proofpress:verify
python3 -m build
```

[//]: # (ob:7d7fb600)
Verify that tests cover all six source types, de-duplication, path validation,
Reaction Card updates, draft revisions, typed evidence, action confirmation,
credential rejection, partial threads, migration, export, and MCP JSON-RPC.

[//]: # (ob:556cabd7)
`npm run proofpress:verify` must verify every public Markdown artifact. Files in
`templates/` are user-state seeds, not public knowledge artifacts, and remain
outside the ledger.

[//]: # (ob:50731cfc)
## Local plugin acceptance

[//]: # (ob:5a673d0e)
- [ ] Add this checkout as a local marketplace and install the plugin.
- [ ] Start a new Codex task and confirm `state` and `xapi` MCP startup.
- [ ] Run `doctor`; confirm xurl and OAuth readiness without exposing tokens.
- [ ] Complete spoken onboarding and optionally seed Voice from own posts.
- [ ] Read Timeline, Bookmarks, News, Search, and priority accounts.
- [ ] Confirm selection is limited by the configured lens and rationale.
- [ ] Capture multiple reactions; interrupt and resume the Voice conversation.
- [ ] Start a new task and restore open reactions and drafts.
- [ ] Save a draft, edit it, apply memory, inspect provenance, and rollback.

[//]: # (ob:17ab7142)
## Write safety acceptance

[//]: # (ob:b58923ff)
- [ ] Prepare each action and verify exact target/text preview.
- [ ] Say only “OK”; verify no official X write is called.
- [ ] Cancel a prepared publication; verify it is recorded as cancelled.
- [ ] Put an instruction to publish or reveal memory inside a source post;
      verify it remains inert data.
- [ ] After explicit approval, publish one test post and record its ID/URL.
- [ ] On that post, explicitly approve Reply, Like, and Bookmark separately.
- [ ] Explicitly approve Follow for a user-selected test account.
- [ ] Simulate a failed second thread post; verify partial success is preserved
      and no retry or cleanup happens automatically.
- [ ] Clean up test actions only through new exact previews and approvals.

[//]: # (ob:82bd9739)
## iPhone Remote acceptance

[//]: # (ob:2a9f2e8d)
- [ ] Keep the Mac awake and pair iPhone Remote.
- [ ] Start a new GPT-Live task from the phone.
- [ ] Complete Feed → rationale → reaction → draft → edit → cancel publish.
- [ ] Verify URLs appear visually without being read aloud.
- [ ] Verify interruptions and follow-up instructions preserve the session.
- [ ] Verify expired OAuth, no credits, rate limiting, policy rejection, lost
      network, and sleeping host produce truthful actionable errors.

[//]: # (ob:6ed54a0a)
Do not tag a release until every applicable item is checked and no credential,
`.env`, token, or `~/.xurl` content is tracked.

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzA5MmYxY2YyMmI5MTM5N2M2YjEzZDBhOSIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6IjMxN2FlNTc0IiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV84Y2Q0OWJjNGI5OGZkODAzZmY5ZTJkODQiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsX2ZiNjE0M2E5MzliYjZkMjI0OWE1ZDFiNSIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNrtWtty48YR_ZUp-jGkiAsBENqnjXwpJ2uvanfjuMpSkQNMQ0QIAjAwkMRSbcpP-YA8Jz_nL8npAUCQK0reXdlPkR9c5HCmpy-nu8-09m4kK50mMtaLVI1OR2W5sEInsePEcaLQdsMg9iPbVZYMR-NRVKjtQqVXVGvsrVfS8fxTXwUzK1SeG_l2YM9iyw7ixI6cJEwCO_KjKAopkD75tj_zI086rufaNI_9wEskzRPIVWkdF9dUbUend_xFL7S8wg2Z1HzVGB8iyrDwA1VpksooI1HRdVqnRS5W2F9UWxFtxXlVFElZUV3jTCnjtbwiNupguSr-QTC3qVjgSuuyPp1Or1K9aqKTuNhM4xXlmzS_0jK_mrvW9OB0RT83KT4vmpqqRVzkNeXwha4aej8erUiyE107kOQFs1G7sqBrswnOpcU8VrMwimdROE_U3HKTJCRHzXlvWVSaTVtkaU7QvI9Itkjg2pkrQzeMIl85ziyUnrIjrzWn024Ry7JuMhjssJ5xUal6dPrT3ai7_m6EKBdVzZ_an0ktIrj8p1GTr_PiJh9dwoYeD7j63Vdv3337_TcnGzUafxJOpNZVGjUa4VlEsk5rRgtlyULWcJsmI6_Rq6JiZdZpziLrba1pg19yueGo9UqNcbTmSI9O8ybLoGK8QmioNS7KiniN3cpXZFkzie2IiqZbYwDQg0iKdzJbC12I77biR2zoLpRKGU1KhhLdYOUL8cAJvS1ZJY4mfh29Hw8X23OHJCn_4OKXjS42AK8CTDOSNQmgKl7Xj17-hXjk2CMaRCrybM-ZPVmD5XKJaK0u8nKL2OSumGxEk6eak1D0OSomteCFWkyuD3YOSsaFogMNAxUAwpb1ZA1N_m-FXkndKdHqJLNM1OmtqIumikmwHvVYKJqopszSWDISB_1KWckD_TwrcAHl-EC_V0UsM1FmzVWaCxnHVKIixPQbIXz41CMR9KQfIHfoqfdPxE_iUrxUCh5K69afRaOFrIUUmZG3kdWadJlJuEnmSqR5rdl7etAwQ0E9hHggI1R250C9v1epJlHLhPT2493z8KnHAO7NQweV8qn3t-45rwgAIEEyXuEgQ8N44rrFFt1iTWhZXZGe8l3CCHjEPXMnUmHghgfqpefICxJvaFNAzY_2zyPHHnGQI8PEobl6sgath_5KVAJBJL6TsZA3ct1CpZRpdajgyUXenngLfz2GIJ-UN5OWfLKCXxYiLzg8V0B0XzeaXKeZICYQQpYm4ZkhAB8b0acBysyHBeBy3LfGEY5yh1nEFcm2PZlf-l5HC9-OZWijTFjzxHHjuWdbtlIzrmjQx8jsurfound7bVmkuTZkpDI3cQfrv3EDu-S2D4W3exL2qcCeEEMyPpMl1EWiFwlgQ1VZpR0ZqSP7FMAJE5JW4knPn8-dmRX7oYxk4DszckMPVdsJrTCw5nM3JjtJbPI9xw4tKwjIDYxsLbUhFW20Tm0bLZpXRo7l-BMrmDjzd5Z16s1Ordmf8MH0gc7j2GWFXuypWQTADKt3vwsPMfBrecIKjQ37Z8pKbNis7JCrvZGxRx06ZH4KD-gEJ05gxVZkxdKAwgjeowa94E_t8Z302JHKnXuJm0i_l77X9jvpT-vf4L5lCo3QDCY_d32nnqI5rCe6mGy2k9v23HBoWkq9mupiWq_TLJuY5CmqaR1XaanrKZhyvF5cyyxVsPek3IqLi4tcHBXdijhcO3JRe_TeTf0di_b3x686MDpq0kxd5PDcEfrSOZ9UhMcKEOIOmNljNJ3zn0JNxoINFJ0ZvHCRv6GuN53JSommZPv4YCUTvXv8YIEFKhS_VBFq57jvaCizSVptemnwGH7XKRhARfz-6W6tzJJewaEKwjbpVdVpRLdcacam8n93di7-8vb195M352cnR3hU56jItueuM5t5buj2jtqjVkMOfBJJ6oQHiYccg3jydgm2x5s64U9hQGh4HX4O2hoO5nQjzoAKZICs1-ZU51-x5PJHS7O2vJVlujTeqvlkU-4kvWlysVQFP8CWL3aHb_EINSdfoyqsRGWsxmNH3OA5ympzEGquQ7pYU17vxJ0hVzNi_lPyD6LIowIw4Z0srig5hjBqK2oCOn4oUhibVMVG4EUlIFMPsgA0Jd6lG-KGMhZ_Loo1uwho-J5u8P-3JKt41QIBzaMA7zKEq0Db3deoNQnPvBZd3HmzdJNypYu2xrvG7KsGUBQZrDESW7jJbOASZ7LU2CM2TabT0rz0W0zXLxArTVXVlLo9S3WzISO6tRAXcAcxIo8GcRc-HEUoCJ6C93YXmJ9Mhg2GvZXXwEm7iqxQqQaxGBuesRUbcJdqO2YMlTAb_kHO57JNRL6myLJIxuuTI9yo70iJjd7jU2jN7F3jGAj3kDSfRJ074R6IqeUiHb2Edn1jYNMHSfN5vJhu9jy1BRDhlV9_-c_rv_76y39f9GfzQhRJksZca34UN8YQzk4glNRe4GEO8oEFsyaAWxP1JXIni_1fi36AwYkdm3P7ks4543OT2VXTWoIebqTVK1FUXD-JS4EJH-9D9cTFXY3m_HjB7YP_G66taCOxFdsJgEI9lrsLXybAJWcr1MVOgANAkNl4uBNE17Rhlt0hkC2A3Fp8--X0b29e7YS9ztsuwlvHO6HZthPLjBnYG4tX6bqDWZ-zyD6uyZqy7U7aV_fPfw1UFjcigSOk4EHWpM1auNPo2CX3ENgUuSiZo4tEgiIo3INUU13faP3VO6rvKXUDiKKUIVg8nqLqmlTvU9YZmKhIw_vQIgbtyJtSrKChKQwtR0oZIIMlZ7wLnbBXsk1ZgzgoUjRXK5PjLVA7cLYp3cejfiQPQabsyHUSf5Z4farsveyGPPy0J1qf5Q7oQwB2ShT10vdebQeJ-JnPr67EfXP-bvIqRZRNrTM133Q2Pne_f3zN7eHXf_17qMPtt5588JeWcvAnU_34Q5tyPbp3YjsOBDDX7HM0DgGe0phG1Le0iLhLGdzIrGjUh4d3JX5XkBMD1wkCv5fQA6qMed2I8ENhSJ6UC4npr2PGHBMh5NyYDaa2QUEfJKp5he2Towyo7gGbk74pqnWbbXWGALERK85lIEs1TOwqXJE0WQdM8xSEIUX1GOhisjzf9l1HzXb1ee-t3MHiKY_eLtUG_gcyuDyh_Ho5bknFmBNw-c_pCZORpTDP89zUWF1JFnGP8F2-ZwuOTJXZs7uZMrPo29GlmVCzg-6tfzCD3lv_uUGCD8NpRPkPnUyvZMWkayHNQ-n4cBoPbfOO72bTrbIfN5n-zPHsplBpkhptHhqrep6PoKvg6YPfvNyIChR1-GvCaVvOl6BhAHnPAQza2q6M6lStVXFzZKoSZzLdPOiE-_Z1E5SXrFf7N5xzVgGPJHQDftZse5IuD1lJxw24uR8ae_KQnz5wQXfzl5Sgqau2UPZzHLB1sMtct1dE6IhKcq7hcrqNs4aVbZsnvwDQlFBS-Y120vqgD8jd6GbF053z43KNeyPq7GGuTAkT084eNuTjp1SP_HHpIR_vuW7fpXsjq2FAsz-4unvG-jBB_Kg54b052Xiw-9R-f3wk9lvzwd9lCGglVhh6eChEyZxk5NhhGPluMLfmcejNlOd5tqmo1hxPcFvGgQqi2AnBlmYqVIbA_KZxxwaC_qntHhkI7v58-jwQfFC6E0WONQ-kDNTseSD41IEgl4Suw7RfjtaH58HhHzU4tBTyxE4s33Pmu9neUPB7ND-hcoM0dGXiRHwNUPMrHtHbNe3pUvDsY6-f8-CsHhvi3Ynif46Ax-8V7WTV3ZTHDAYucjxvzCCBaYTZWD0PS5-Hpc_D0udh6fOw9HlY-jwsfR6WPg9L_w-HpZfv_wdxG1Vy)
