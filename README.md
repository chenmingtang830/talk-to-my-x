[//]: # (ob:0f18a9a9)
# Talk to My X

[//]: # (ob:8afd4b32)
[![Proofpress: verifiable revision history](https://img.shields.io/badge/Proofpress-verifiable_revision_history-5FB3C4)](https://github.com/chenmingtang830/proofpress)

[//]: # (ob:6aa3992f)
Talk to your personal X through Codex and GPT-Live. Review your timeline,
bookmarks, priority accounts, and news; preserve reactions as they happen; turn
the accumulated thinking into posts in your voice; and take explicitly
confirmed actions without handing your X credentials to a hosted service.

[//]: # (ob:475e124a)
## What it does

[//]: # (ob:9203a311)
- Applies a configurable lens: topics, accounts, rationale, angles, good signal,
  and ignores.
- Keeps sources, raw reactions, questions, connections, drafts, Taste, and Voice
  in local plugin data.
- Restores useful context across Codex tasks without duplicating full chats or
  storing audio.
- Uses the official X Skill, `xurl`, and X MCP for every X read and write.
- Requires an exact, action-specific confirmation before Post, Reply, Follow,
  Like, or Bookmark.

[//]: # (ob:b384e121)
```text
ChatGPT Voice / iPhone Remote
            ↓
      Codex on your Mac
       ├── official X tools → X
       └── Talk to My X state MCP → local memory
```

[//]: # (ob:9055d828)
There is no custom voice room, model call, web service, hosted OAuth, or public
listener. Your Mac must remain online for Remote use.

[//]: # (ob:ab660985)
## Requirements

[//]: # (ob:f13daeb7)
- The latest ChatGPT desktop app with Codex on a Mac that remains awake and
  online
- The latest ChatGPT iOS app for [Remote](https://learn.chatgpt.com/docs/remote-connections)
  and [ChatGPT Voice](https://learn.chatgpt.com/docs/features/voice); availability
  depends on your plan, rollout, and workspace settings
- Python 3.10 or newer, and it must be the `python3` on your `PATH`. Check with
  `python3 -V`; the plugin's state server refuses to start on anything older
  and tells you so.
- An X Developer App with available API credits
- Official [`xurl`](https://docs.x.com/tools/xurl) authenticated with OAuth

[//]: # (ob:4fab8c9e)
X API usage is billed by X. Talk to My X cannot verify your remaining credits
locally.

[//]: # (ob:985b5f44)
## Install

[//]: # (ob:64954b01)
Do these in order. The plugin declares the official X tools as dependencies, so
installing it before `xurl` works leaves you with a server that cannot start.

[//]: # (ob:af430a5f)
**1. Install and authenticate the official X tools.** Create your own X
Developer App, install [`xurl`](https://docs.x.com/tools/xurl), and complete its
OAuth flow. Never paste tokens into ChatGPT or Codex — the plugin never asks for
credentials and never stores them.

[//]: # (ob:34629b2f)
```bash
xurl auth status   # must show an oauth1 or oauth2 identity before continuing
```

[//]: # (ob:8a3e3fd4)
**2. Install the official X Skill.**

[//]: # (ob:0f11f6f2)
```bash
npx skills add https://docs.x.com --global --agent codex --yes
```

[//]: # (ob:8c15d7d2)
**3. Install this plugin.** `v0.1.0` is not published yet; until it is, install
from a local clone:

[//]: # (ob:6a769bfa)
```bash
codex plugin marketplace add /absolute/path/to/talk-to-my-x
codex plugin add talk-to-my-x@talk-to-my-x
```

[//]: # (ob:57d9fd23)
Once `v0.1.0` ships, the released install will be:

[//]: # (ob:fd47afb3)
```bash
codex plugin marketplace add chenmingtang830/talk-to-my-x --ref v0.1.0
codex plugin add talk-to-my-x@talk-to-my-x
```

[//]: # (ob:995f2bc5)
The marketplace entry is marked `authentication: ON_INSTALL`, but there is no
install-time prompt to answer: all authentication is the manual `xurl` OAuth
flow from step 1.

[//]: # (ob:02d95abb)
**4. Start a new Codex task** — the plugin is not picked up by tasks that were
already running.

[//]: # (ob:d06ac297)
You do not need `pip install` to run the plugin. The state server loads its own
code directly; the `pip` step further down is only for the optional
human-facing recovery CLI.

[//]: # (ob:ce301b7d)
Then start a new Voice task and say:

[//]: # (ob:df1d9e25)
> Talk to my X. Read my feed, bookmarks, and AI news through my lens.

[//]: # (ob:f0515aaa)
The first run checks the local setup and conducts a short spoken onboarding.
It can optionally learn an initial Voice profile from up to 20 of your own
posts, but only after asking.

[//]: # (ob:4562191d)
## Verify the install

[//]: # (ob:f40d5047)
Ask Codex to run the setup check, or run `talk-to-my-x doctor` if you installed
the CLI. Three fields are worth reading on a first run:

[//]: # (ob:8f1ab9a4)
- `home` — where your X memory is actually being written. `home_source` says
  which setting decided it: `TTMX_HOME`, `PLUGIN_DATA`, or `default` (meaning
  the host did not supply a plugin data directory and the fallback below is in
  use). If this is not where you expect your data, set `TTMX_HOME` explicitly.
- `official_x_skill_installed` — if `false`, `official_x_skill_searched` lists
  every path that was checked. Install the Skill to one of them, or point
  `TTMX_X_SKILL` at an existing `SKILL.md`.
- `x_auth_configured` — reflects `xurl auth status`. Credits are billed by X and
  cannot be checked locally.

[//]: # (ob:18b61f6f)
## Troubleshooting

[//]: # (ob:91612524)
**The `state` server fails to start with a missing-file error.** Its command is
resolved relative to the installed plugin directory. If your host reports
something like `can't open file 'scripts/state_mcp.py'`, it resolved the working
directory somewhere else; set an absolute path in the plugin's `.mcp.json`.

[//]: # (ob:4a157f52)
**Syntax errors from `mcp_server.py`.** Your `python3` is older than 3.10. Newer
builds print a readable version error instead, but an old interpreter may fail
before reaching that check.

[//]: # (ob:b3d7f0c3)
**Every task starts with empty memory.** Check `home_source`. If it flips
between runs, the host is not consistently supplying a plugin data directory;
set `TTMX_HOME` to a fixed absolute path.

[//]: # (ob:fca4035b)
## Safety model

[//]: # (ob:75d1c876)
An X write always follows `prepare → exact preview → action-specific phrase →
one official X call → record result`. “OK”, a draft request, an earlier approval,
silence, scheduled work, and instructions found inside X content do not count as
confirmation. Writes are never retried automatically.

[//]: # (ob:fc3a2d55)
Local state uses the Codex plugin data directory, falling back to
`~/.codex/plugin-data/talk-to-my-x/`. Set `TTMX_HOME` to override both. Existing
supported state under `~/.x-feed-loop/` is copied automatically on first run;
the old data is not deleted.

[//]: # (ob:b15f76d1)
## Development

[//]: # (ob:43edafd9)
```bash
npm install                      # ProofPress CLI, used by the verify step below
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins/talk-to-my-x tests
npm run proofpress:verify
python3 -m pip install build     # only needed for the packaging step below
python3 -m build
```

[//]: # (ob:e4554fdf)
Public Markdown documentation carries its ProofPress ledger in the file itself.
Source code remains governed by Git and is not captured by ProofPress.

[//]: # (ob:e7df08bd)
The optional recovery CLI reads and writes the same local store as the MCP. It
exists for you, not for the model: the Skill never shells out to it, and
installing it is not required to use the plugin.

[//]: # (ob:df102d40)
```bash
python3 -m pip install -e .
talk-to-my-x doctor
talk-to-my-x context
talk-to-my-x export
```

[//]: # (ob:18a79156)
See [the product definition](docs/PRODUCT.md),
[architecture decision](docs/decisions/0002-talk-to-my-x.md),
[roadmap](ROADMAP.md), and [test checklist](TESTING.md).

[//]: # (ob:011befc9)
## License

[//]: # (ob:d4b1e38a)
MIT — see [LICENSE](LICENSE).

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzBmOWQ3MWQ5ZDUwOGIzZjhjYWM2NzA5YiIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6Ijk2NzhiMmE5IiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV84NjJiMTM3ZDM3MGUzZTVjZWRlNGQzZTgiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsX2Y2ZjQ2Y2NiOGEwNjJlNzU4ZGMyYjgzZCIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNrtXety28iVfpVezQ-PHZLC_SJXba1ieyau2GOV7STesl1koy8iIhBgAFASa2q25tc-wO78zL7cPMme040bKRKSKM9kKsFUqiJDQF9Onz7nO9853fr-iOZlLCkrpzE_OjlaLqeGDLlv8pC7RhDZMmCUeb4RRkejoyjj6ymPz0VRwrvFnFqud-K6lpCWYwXCZp6UkRF53PZpYDjCjiJuUh4Zpu2ZriupKV1GQ194tjBM06KhaUhol8cFyy5Fvj46-R7_UU5Leg49JLTErkbwQyQSePBnkccyplEiSC4u4yLOUjKH97N8TaI1OcuzTC5zURTwzZKyC3oucFIbj_PsrwKmu8qxwXlZLouT4-PzuJyvognLFsdsLtJFnJ6XND0PbON44-tc_G0Vw8_TVSHyKcvSQqQgizJfiR9GR3NBUYih5wcRTO5IP5mKS_USCFdMA8-KTNsHCRnCFi4TXDjcFgGOLMtLnNo0iVMBI69XJJlKTzoeY1FADc8SvhtwZkWBzfV0qtFNGV0WqwQmbOE4WZbz4ujk4_dHVfffH8EqZ3mBP-lfCz6NQOQfj1bpRZpdpUefYQ61PkDXb1-cPn_9YrLAfu6jJrQs8zhalbA604gWcYHKIhI5pQVIrRSqvVU5z3Icy0WcYpPFuijFAn6T0gUuWj2mEXxa4EIfnaSrJIERsjmsjNBzi5KMXcDbhjQDGiqRw6KU4hrH_54mF6TMyOs1-QC_qDqinAstOdAgcQVPviJbb5brJQ4BFw8U4eiHUdtRQCV3Its6qKOP__axVdETcrlfmz9_XWtmvDifFPNYtMNa0pxujMmj1A5DSx40pvq9dbbKyVLkRZbShHwg5TzPVudz8izj4prQlJNvz96PX8WXYkLeqo_JumdMju8K03Loxpj-MqcliUvCM1H0LshXZOvVnhUJLcOmtmke1NOYnMIGi0VBKIGvZXy-ytWCJCKFFSqzZcyKEaGMZau0hJ9yimpNEzEi7bASWLSNMUV24MD0DxvTbDbDLz6lz-ADEDr5cxYzQY5JfDbPUgHSX2Sl-JSSzn8___f_1g-eZe3AGCzeprAM1-WBFRw0sPdzkQsSFyTNCFuBni7IpRoa6PRiRBbQWUIYTZIRuRIRgb1-Cb8dkXmmjPg-VaGR5xlh4G6M6a02tAswXbepytarPaoiTZtTEfkH9TQmC8revCNX4CpgdwhSLw8XxQUoCqHLpdonasd8Ssf1esks79MVR9IoYKE4aFAfyOnZS7IqwF3gwkRxkgiOrvDDZMOowbKkaVZqk7PWm71nSWA1Ilc6zsaYXqZFCYur5r5cRUnMSCRKesvq7P-qZ6E8J3QdgA0P7f9UliIns0tjYk6MGUpIfVjMBT_p00jp2AZ15UO7h50M_m_-KWXKiC6T1XmcghrlF6JcJhR2DnxDtgEH9HIxLnt3cehKK2LuQ8f3rLJ4QisEuFvQlFqNAQstE1EK1WAmZcxicAzXgJvIm9NV34Y2LB66NIoeOrxvYONAk9ArBwyTZEvcDn3rxg2PMiv0f511O6ZRkSWrUhwvaTk_LjO9cj3rxoRtmJHPHzo-MMQpga_yEtxWCp5Ye4iSFhdq6Qq67hWTBNwmrAerz783JmahDM5b2Mn4oxSCj0iUZRcoMnSfMKbTlzjSosYVPcOThmu6lNIvICUi47woSb5KcZexi0J9r3WqEOWq1vSUr1iJGKAAUFqSYtk3PEYdw3Y3tfsdlaJcaxd4i0HcerXHCvouN1ngewf1dIp7-SqPYQPT5IquC_BDSZLBCszgJZiVANDwP0RcA6gn1WfqCfwbEM64VwI2tbjrHjSuV1r4JYR24LeEXpFn3X3GaUkJB--H4cp6RCSsO4iGRLRnTJHpSt_jmx7jeWs2blmUzTd71sSxBYcQIDykn8asLNcQ_KQ2GS_IKo1LDHJJHQOTMYgEHhRkfLnxZo9dET6XEIXxQwaFuyRbalBLMC7EOJw8e_WyXZ0CIjKCYQmokn7y-tnZLQYGfIBjfCkhLeMliSsDMBZk8imtfOR4sR5fA25FTdEPe6QEEaIfmq53yKjeCUE-KtuTZ2grwCPJGJYOxPb5a-i_OD57--b5n569h2j58ehT-pHmbA57j5XgXftcpWlGQrJNdXoFxjwtxC0q277Vo64Qq5rCDuh923_98j35-cefwEjCvF-9fPbiu3cvPn9d_fB4sj2jz6OaZTgC9cFAdspyQXWor35T8wZiaoS249i-5Vh-KExYEEYDT-NfQKiqzYoIIRURom33MovVGqHpwp6QDaj_hWTAZ2RQwC-sOy10WZVOI4qvOZBwKTJZTmHtz0W-zOOK1yki88Rj3Iq4GTJDCGaYtuk7jsEYxBvcjALXlYHlggpyeGZENo8MVzCfOcKVhk-pg5YLraLiZ_SCnFjhDyBopE8sw_LGhj-2gveGceI6J4b5O_jBwC1WSRw13OIsDEUEKtA-_f5LUDpKnzTlMofdiTrj8Sg0DUcYFHeUaqPDwlSqdhdqpWrQE55HjRDsBvPrBjtsS9XgQyiUhBeTODuOKD8Xx20r47aRad3ItGpk7H7ze_uZ87ht7E5M4eMdW76apgS5UcsKbWGzepodAmeLvTmElcFPynghUKvBFHVwGChsBohg3eEzsAnEZU8RA2DEjoLUEKCorP2azCEmEOlTAsYsBTMLZhAaWC1WyM9yeCVOL9BBw27IyDJD3wVuXI1D8QNPVS8lvRAAN5awReMyWSO4hugjX0ALdX8YWmerEvpLUTt0ExC75oLDJofwo0CZUEUowGcVwTDZL2zXjQxHeqZnuY2wO8xUraR3oZvq5ZNc2j7sT_AldYsdBqpq8SG0EihTIuDReZbBFONzeDpCbgdlCP8CL1xMkF34oxDLghQgIiZUC1ftyo3I31aAIfSPMIBU1M95TiV2-J6CCPXyq-ABe4BF09C4A8RUV2-F8v4FQgK5SkjlSmD8eVYUlTJi9NEuIV_hQsOsYBnhE_gGJFwQdNNEYQn8BV3xOFM9_KnGGk2g-YG8u4iRSpphyDnTQ_2AyEMRKkLBlA84Za5-paBuNVrN0cNjDW9HNaYtloLBTmekUj0ldIgjJEKbM1CqEXy8TABzfqOwspL7q_gCBAVd_r7aSJMdZE6lHZawPYtaHg09XmtHhwustOPBBB-KO6t22GvKmjd__unvP__0I_yvK8Yyy2DfILL_0Hnxp-rFDZJIo3IUMb6udWEBg8lht8Kgd2Crat4AYYS0qRM6tN0VLdVYG7UH8Iew3ZF1mKuV0AHgpxTFL1KRT8h_VqIgixXGe2JBQX-zFE2gUhctUtTfPmsR-lbogq0wpFvPokNOttbidsaxatF2ItdnhrR81rTYISEba_EAZrGamRYkzO-p1qbj6jm9pHFCozhBs88FmHFeNLqzTGham5YcNX5VYutnCnkTe2Iav8N_q1CyAsoQoIBp00Ot2gazhiQkWum4LPCDN7X2fdSbt_WeCJUn18p7Kr08xt8_JpgNQgvPlENRjavV3r_TGI0cbnEPMEOjcR0mtZLsQ-hRrURoppqZqR2RrHtUSDqREfqGG3gq-tEboSVTWxW6Fy1aQy4qASSwSIJONtChZUqrxu_JedYD56CmIqRMEy9a91satLVchxOaOlgbj3MhiR7dVjv4bffd_-j-41OaLq9JgT6hUG_eVClo-zzJItC78RhWPC2Jbn48XoviFgvmsygEQG6GQjSy7dCs1fwfQpjOiQSXMiHfoesiS_S_gKWyC0AEGjnVux42tdroE_KuQ_G1TpZQtcJVQIwKqpRIybBHNSNh-2DZPBo4UQPYW6a2muGdOdfa44UWDUMpXGE0rXZo2HvpzR5CtVGA-yhL72LzwAggCDP8IGh2aYebbd3VISxr1QcE9oGEMCq0W6DYIV6rPh5CoeJ7iCd71txBuxOZXmgIq_E_Lb3aTvRgohT1F_xJlNEczRUAsJclWtOGU0pwkDRPEY0pxgRa1IKEcEnG4DxkDlsXegAhWAZsnGZvfUpVMAFyAEAJznxdaT4sAHa1f9o0YEHEecgobzZzh7ZtrfDtXGwdnAYuExTQgWR23WKHnq1N7wM51wafLuc5LdTLn1J09B04hx5IfaNrOOD_ilVSzibk5x___uaPP__4f6ArGuUTLFYRCGoRCNMc4pEcjVWeXaqQogDhp4ivClhyvkLPeJXlF1rX0LrkqyoukxClqEcxFzgEhP8pBksEnaaKYWBRmohOweoJ-QsKAnQFZp0qm5eLMo8x3FsB9KPo7fudqe9LUwauSR3TaJex4Z5rNusBhDLDrQfG4r-OJ8q4HOsvxvjFhvE5BgG_uAYMgt8VqyVSRxiB6l5TLnLdyvUYd-44ybLlsfK9DEK97Skj_mr221PtLhKuh6nQMaAwUEhwJbxPyR2HUzuwfU800umw4K2S38pt11bRQDaSAT5lbbDc0t3bpvwgEht9JKidInL_Vq1PsQkQ1HcbH0WrOOG3mPTAF1SEAXfDoNnyHVq8Y-m-FNlddWx4ng02VlgsMjt2vua_e6R2D1a7eVhF3ltPxTXq4y0SYgHzBIOgzOdOPdAOJV6ncR5CdMPLTNFn1av1P4tjwzCscXfM9ed5RvmCLj9__fbN6fPXp2fqubJAH5VGKW-E4P_z1-9fvHv_8rtv8Y0-BB6AeXB813T8JgTvsOzttujlz2utklHkW4ZpcL_ZYx1KvWrsvmT5D9jDjqo8jDKamjxlj44-qwo_WIibz7dq-DrPldVvi_sgjv4lK_vm4Nyx_JAqE7C7uE-h8ba2T4_1bpV9d0-4gRcH56kGsDdR5riuI7k8JAV0pqO014DHOAJ_0PAVfqNJJEbzHPk-iBN1GeoZ8sAAffi5uFlqA8vEEhov9k715pSq3MgpjqvbQ2VB9Chw39RZjXE9wIokZ_oVQFkdZF-hvck-KW1JoxrEi2sA7XGKgGEeszmpVWhj6udoXBGdqtnW0v7-6Gq-riwxaiaCOWhH03lVINwMHMaKcgXc18zqpnBx7HfPPvmWy3nkBsyXniVp6NmhY5k-bSf3vOpdtKKsl7EryE4mqs27dPNR3_9LqfPdk3zbSS5z1E71xPxhdz7rtuTeF8ngicg1BQ8oGDzDBvMnqAFxEo08IxKuYzBpO4EfeJHBhekbnNvctGVoWQajwjEUCrt1cruyed6Jae3I5oGbcUOHD9m8IZs3ZPOGbN6QzRuyeUM2b8jmDdm8IZs3ZPOGbN6QzRuyeUM2b8jmDdm8IZu3Q8eZbYQcvnekuEs2L10uah_0i6f2sC-0TS3DcqKh2r2zfqZtMM-SkTDNBpF3SNFqkg-hOkHhSmVQwbTBGyKRYBTfqTBd4ZEKWNZ0t8aj38al3naF3lJ0idkx3lxRoXroUYYhmTkkM4dk5j9hMvMeFxDcTP_ooHl36rDT8N7U4as4xVRbgz40bkPtrNiFTbuoIGJCc9WKYm1GNa2gdRrhRbFEuJ93ZrAn39eQCG-WIgXou2WDNdRAE0XLhgQny-xK5MXNgTb2rSJD0SVfISGNo3xU1M5n1OWaR1W0qcdeA6fiftlD2w6ZD_G6I6PQsiwRhA5sHh61QtY3FAl-c9D55jI3ycMmzXN78vDLqM_dM6JNNmtfgq5NUf0qCboI7L3BGaVuZAR-FNmOgNAUhmD4YNMMH_ClYftW6HmRtELmScv08G2BfKZQWH_PlG6k5cwTwz6xvR1pOSNyoG1hDmm5IS03pOWGtNyQlhvSckNa7h-YlrPAQTqUBZbhOH1pOYyX9Y2SO1NyKk_VLDtVE1VwtI7wNcSEbYArrKeNO2FHs_Gbd6pJFMpHLZXWtyn-dII79XxZKhenwstcvTbu2JHHtUH6uKHCt7YkAbxC_Focq3V__HQja4ht7koc7sX2hSjRvhRDKnFIJQ6pxCGVOKQSh1TikEocUolDKnFIJQ6pxCGVOKQSh1TiL5xK3E4aJnTFMVKGddyROtz-7WYCcSsE-a3lEjuD_9Uyine897uvofve4d3X1r1u496d71wtIoGq8_HjEQST8MScHH3-vL8H2_GsMLJu6aHnrlIVy-HiKse_KgghX2mWDODwFcKsDH9rYginfrJI3HOuL6C2sCV37jueJ0-syQaBsE30Tp486buMVJqm9KR1sBgOCcT7xMBMl_vcur8Y7K4Y4johDLPfoD_QoTYUCFmL8ilZ9f6ZDd8LI0kPFs8Xvk0cHFYouWXfdzxvANu3cijm8RIiKdSWHKAlRBe88b5XsJQkEn1X_YKW-lRG9i8jlC97Nf69rE7fJfb3aqjvUvp7NeS4nmWG5uYtz3_WxCQuX3y71MG97_yg729mOAb4O8d_QK-nxUXNUmUKrSs8qcgDBWNUugGfz24CvR55BNKkUUidB4xsTGbzbCFmCqZcqcxJlQ7VGRm0EoAAVio4iwTGeBjFQ5A7gS97HKkZRB7a0s0_yZNnYG0EuIQMw8VbFurm231_BMf0TMu1nEP7e_IEQ4CZCltnKikEAYuksU4Ga65LU_tkEQMqSc_HKo4Red63RA41XV-61uHDercGSH-t-skLzQjNFmw51UOcLNcztOoqMzWrYghl27Ok77J4m_vSYPbhw3qhAiTF-Cnh6JwsEYslskZKd3Bcz1C9tY5NdRJ59mXu1b-LufiiNw3c-Yb5fSM7vG7tneJScEd38k_ImWfI-IFGnp2-_0O3vErXW2C8qmrE1BoA-FjA48k-uLu397eijMuajHy0JzvzCHdJ_ctHk304uKcT7fOw2VXaYJJx5ZGREqQLzKc1hwrhQZGljafGCCgH9wmmKd-6zaMDn_f2_1plNttcGxo6hWkhblkSU3WDBHQmdwOFndLtoOrd14icIlMPzd1Az-e44FXFAKpbnK4Ur7sHI-9vXQ3fIpXFVPnYnbB4Hwze3fLr7FIvVfX5thh01kb3PdmHaG8ZtK0zCUr11WUryVpnozVu2wlfJ_vg6u6-zkCjs2pnKUJ_zBLklOvZwBzU_lnlWJVIEJZO9gHQ3T28wj_buFtjYOPKFXIjk31wcneTWJDTq4OFWmWdD6hkpSDuZB9M3LspqltutNjffDd9-d2796evXm3sE6yEo6rWYgnSXGrTo1Q51iQZDGlVJ_tUmm8fyOzfm8rJqGqeGzm_tKn3IjrwFVqFJvtQ6N6enqlq30rPuixcpWyVieVdGFdnF_cA1f1aTncgUQAeKrEw2YdA9ygy_lEHTZyPsSZPXSwEjqHcBpqTffhxd7v1TUAE_fdxx4mPNnZ_IZDrU_ujyse9f__6w_TD9N0fX756NdmHC_tEs4VFdsulg_luGb8SgzIlFbLDdA5iuCb3obAeMpXKfAGckfH1ZB-Uu0NvWcLHsChYwCvKCkpi8whjJvuw2C3tdsEVYXRVaBocNsAK1Qfd4868zmQfyNq7EZou1UL-4c3rFzXnjcR4jsmu2pX0dXWn-7ywvKTGNxsXc9XmTFmUylNW2FsnNKo6HpGyrX47YO1WUFVtkg3OH7b7fAWdjyVlyuao8lXUm1rm-EntOTer_XPxV1WQj1zrc4HnB1CnSE1uVCs0zjMsqgFzo5YNlmwCoH7yV4Q0GIrVrZyonqqqfjBzNFXFx4WA0YEB1jnEVXpZF90rkKYYn1wssyLWab0igx6QVsbJoIfLY6yirKtGtRRU0rNM9E4onjaZHaEl31XgZpNUxh32So2QJsg56xMP37T2qDJvhWpFuSyiksBqzTOYBo-5srBCu5yTLVy3XJUdY1sjIxyB8iutHoz0blCSwnviOlnLVtrNTMGFZrqwShkHbbs6OFtD7CtQfWgyhT6Z4BNyphLWdXVJK2e1JSpMXOPWBeVKswtRpb4wt4mlzLUjU1fAXWUr0OZ5XN7vMEbPn1JuYLXOuWsXgOPbdhInWsItjBjVpV6_I-VuI4x1vbVZOO5a-o7KjNQ-Kli2xBRvvZ2wUqF78qM5SfCrnPwYaP6B5h9o_oHmH2j-geYfaP6B5h9o_oHm_0Vo_rufmb5xW66zcV2u8cPuc7e_ylljJiMeOi4zpcUki3zY5jY1A8MNLFuaLPIs6XFLclMEJvWp71NLBrZLHccUgvnibtO7ce7YOnGNE9vdce449Pwgsmg4nDsezh0P546Hc8fDuePh3PFw7vgfeO6YObbNmeFKh7rDueNf6dwxagi4NJFXp5FKrRSRJpjb2KDuY4bFIbNJBdFR1jiSWXPc4M-zpx1q_VGxmSfLwSIq41UHR-pepLVmsLNEne7RsioF0mHQJRjtyXA2-l5nowPJecAC03RD_y5no_tvA-B-5ABMZZ5n7z8L_Tyr0hJoSTADMFH7qfaNOnF1w2lpawvAqcm4xOidi-xT2jl0G5e119ELqZUaDzteCq0iVYhdKZna7JUslZb1iIpBKBNykE0Q9ZzGfvLEbJnRuiKhVpWdk1JRrEq0dA4wf0o39HfUEIZ31NDR5ulnpQ17DjyTvvPOirbp5L90LlIhEomYowsh21xlhWrgu0XfsRjXE1ZkBr7f6l4nT7B9TOmQDIAaW7m-WdB0i9-lECj7pkdlYFhtzNSkDJq1PigZUJ-ktC0ngKhacOl0Ar06P3DzaN8veNLeYoC1vSDg3G3G0skNNPM9nPUHwSe4PeNi1J5QVGQTrQCRqoC656n2TsLgt3mq3RFWAHI1AtNtTGInq1AN-ovkC6oeQ-EGUYT0QXumrpNC-C1cGtErMWlK5hqO61CL7r_04b2q72pHC-quuWT1kJPZZqXYSaeIbKbPrpctaG5ciM5OV-VkGBGnBcCdE6Js-Wbp2WaNWeVtlIUFtQYTq4lUXcPZZwOZKyPus9AN7f0XQDx54uy7eAK23paJrjdgzFAQq6UqGlEWW3k7mBBgWJpggLfGnEDaf27fxWOK1OYhmOX9l0lAnFAfPU8Fyr9TwzbbUbSmXP4G3ksyyvXxXXXLgDqVq4t7kvXTCmHGy5kWqVzluH5EHQRGLhprNJsS0-o07ad0o5SmW2fTM9_hHop_7nsoQjNyPFcA4HWaaXfyfi3ivWsar4aHUYB_r46bftSsaSezV99G8YBEXQ7OVQmgHo_gmjREhYYNlQtcKmRjVW0WQF_ASnlVf63i22Yh-y4dci2T2qGwIVxvoECbB2xC64ek9TrJGtwpBUZy-s9ZVqGnOrWNVVRxeUJmTc0PmO7Z2as_ffvyu-nz0_enMyWtGReS4nUb5OuFoKkCd6QpXmvqu_CCiET9OctdhYpN_RXeQ6HuoIgEWvEYcTG2B7HoYwA_UuOeysY2E0f-FRrSMsCWRziT7sg7DK2KUWc1VpxeTxWsmzaLqoUKSz2DwRQCJ33jZV34iu9ioKkEWP0dT6pOKaChh2BJ6RRWjnVRqi6dBf3Tt5gomK7pHyzmVTF6t7ZqhtW8ivKrrtqY6eLaBZ_pmVxP0TdOaz62ngCgg0SgQZhtI3fkBHSIqhS1E-XWVEsVkkWingG5GcpuR9iGBHhugGG1mWgvE2iSxO3GvlPat76giTpMMtPgLGhAZycT3Pjnw3O7OaLnl2XRnmCA1YToKUsuBd4kg39eFs88ZF1L1NQXdupfUTmV_im1x-LAHBWjgM2mSZMkvoBBgmgfgcWEIFpfh_GoYHm8LItjNfop1oIu149A6WJspBoGdl0VLn9K202Dbes9IBL8g1mo8xsVp6iMcbrJ8syaetNZH-wQmHNzfO7bTRqsk-tuBH949prr-F9zWxgRXyGlpMp7C6ISkrBcaD4VY1Sl_XRHdcmp9j7o0BJ18qSpuV5QXcwK7enIEzMIc124Scu6In7_tWC-QV0hechcs6W7m4x6M_nDc-RKW2CFZQKxBo6yvBKgEeAaqshDKVF980mWFooRxspVbUd1GelOU_oUdG7L9qnkkoyvMSXV1Y3huqh_9uuiZGCEkaBUGp74DVwX9e6mYjbHCqIMFLK5UApku-tGKXLghVIaqG3dKEX-ARdKyQgT5IZl-GFwvwulyM7_vuretgRAdLRxUKHip1XMpgDVb-RWqu4JK32gQ89FBRIYwOKBhiqcXIKK0XNVhb57Gv_CV1yZdmS7gesZRsgPueIK3WvRppk7111V4eXWpVfgtgCgKiSqDxsC4BmpoderpfzASQfnVoz0XCWJMIMOez7WKa_t1MGOs3ar6vjErTd5DnduDXdu3fvOrc8__D9vg_CD)
