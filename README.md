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
- Starts with a fast timeline-only scan of at most two high-signal items; news,
  bookmarks, and search remain available when explicitly requested.
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
> Talk to my X. Quick-scan my recent timeline through my lens: surface at most two high-signal items, and only open bookmarks, news, or search when I ask.

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

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzBmOWQ3MWQ5ZDUwOGIzZjhjYWM2NzA5YiIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6ImQwZGE4NjEwIiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV9iNjA3OTRjMTMyYjY5NmE2ZWRjNjYwMTYiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsX2Y2ZjQ2Y2NiOGEwNjJlNzU4ZGMyYjgzZCIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNrtXdtyG0eS_ZVa-kGWBgD7fqEiNpYjyR7FSJZW0ni0ISmA6roQbTa6Md0NkQiHNvy0H7Drx9mf85dsZlXfAAJNEpRs70wrHGES7K5LVlbmyZNZhR-PaF7GkrJyGvOjk6PlcmrIkPsmD7lrBJEtA0aZ5xthdDQ6ijK-nvL4TBQlPFvMqeV6J5Q6jmVaEZVWGFqO4XHhcCtinkndyDA5NQLGbEbNkPqu60uXGa4XSMcygtCQjEK7PC5Y9lHk66OTH_GXclrSM-ghoSV2NYIfIpHAB9-LPJYxjRJBcvExLuIsJXN4PsvXJFqTl3mWyWUuigLeWVJ2Ts8ETmrj4zz7QcB0Vzk2OC_LZXFyfHwWl_NVNGHZ4pjNRbqI07OSpmeBbRxvvJ2Lv61i-Hm6KkQ-ZVlaiBRkUeYr8Wl0NBcUhcgNTgPPNI70J1PxUT0EwhXTyDP80GGmbUVe6FFPcOZ5hunhyLK8xKlNkzgVMPJ6RZKp9KTjMRYF1PAs4bsBZ1YU2FxPpxrdlNFlsUpgwhaOk2U5L45O3v14VHX_4xGscpYX-JP-s-DTCET-7miVnqfZRXr0AeZQ6wN0_erJ6ePnTyYL7Oc2akLLMo-jVQmrM41oEReoLCKRU1qA1Eqh2luV8yzHsZzHKTZZrItSLOAvKV3gotVjGsGrBS700Um6ShIYIZvDygg9tyjJ2Dk8bUgzoCEN4XFYlFJc4vjf0OSclBl5viZv4Q9VR5RzoSUHGiQu4JOvyNaT5XqJQ8DFA0U4-jRqOwqo5E5kWwd19O5f3rUqekI-7tfmD1_XmhkvzibFPBbtsJY0pxtj8ii1YevJg8ZUP7fOVjlZirzIUpqQt6Sc59nqbE4eZVxcEppy8u3LN-Nn8UcxIa_Uy2TdMybHd4VpOXRjTH-d05LEJeGZKHoX5Cuy9WjPioSWYVPbNA_qaUxOYYPFoiCUwNsyPlvlakESkcIKldkyZsWIUMayVVrCTzlFtaaJGJF2WAks2saYIjtwYPqHjWk2m-Eb79NH8AIInXyfxUyQYxK_nGepAOkvslK8T0nn3y__9T_1B4-ydmAMFm9TWIbr8sAKDhrYm7nIBYkLkmaErUBPF-SjGhro9GJEFtBZQhhNkhG5EBGBvf4R_joi80wZ8X2qQiOwgGHgbozplTa0CzBd16nK1qM9qiJNm1MR-Qf1NCYLyl68JhfgKmB3CFIvDxfFOSgKocul2idqx7xPx_V6ySzv0xVH0ihgoThoUG_J6cunZFWAu8CFieIkERxd4dvJhlGDZUnTrNQmZ603e8-SwGpErnScjTE9TYsSFlfNfbmKkpiRSJT0mtXZ_1bPQnlO6DoAHu7a_6ksRU5mH42JOTFmKCH1YjEX_KRPI6VjG9SVd-0edjL4v_n7lCkjukxWZ3EKapSfi3KZUNg58A7ZBhzQy_m47N3FoSsBYbl3Hd-jyuIJrRDgbkFTajUGLLRMRClUg5mUMYvBMVwCbiIvTld9G9qweOjSKLrr8L6BjQNNQq8cMEySLXE79K0bNzzKrND_ddbtmEZFlqxKcbyk5fy4zPTK9awbE7ZhRj6_6_jAEKcE3spLcFspeGLtIUpanKulK-i6V0wScJuw7qw-_9qYmIUyOK9gJ-OPUgg-IlGWnaPI0H3CmE6f4kiLGlf0DE8arulSSj-DlIiM86Ik-SrFXcbOC_W-1qlClKta01O-YiVigAJAaUmKZd_wGHUM293U7tdUinKtXeA1BnHr0R4r6LvcZIHvHdTTKe7lizyGDUyTC7ouwA8lSQYrMIOHYFYCQMN_E3EJoJ5Ur6lP4HdAOONeCdjU4q570LieaeGXENqB3xJ6RR519xmnJSUcvB-GK-sRkbDuIBoS0Z4xRaYrfY9veozHrdm4ZlE2n-xZE8cWHEKA8JB-GrOyXEPwk9pkvCCrNC4xyCV1DEzGIBL4oCDjjxtP9tgV4XMJURg_ZFC4S7KlBrUE40KMw8mjZ0_b1SkgIiMYloAq6U-eP3p5jYEBH-AYn0tIy3hJ4soAjAWZvE8rHzlerMeXgFtRU_SHPVKCCNEPTdc7ZFSvhSDvlO3JM7QV4JFkDEsHYvvwNfRfHL989eLxXx69gWj5_uh9-o7mbA57j5XgXftcpWlGQrJNdXoGxjwtxDUq2z7Vo64Qq5rCDuht23_-9A355aefwUjCvJ89ffTku9dPPnxd_XB_sj2jD6OaZTgC9cFAdspyQXWor_5S8wZiaoS249i-5Vh-KExYEEYDT-NfQKiqzYoIIRURom33MovVGqHpwp6QDah_QzLgAzIo4BfWnRa6rEqnEcXXHEi4FJksp7D2ZyJf5nHF6xSReeIxbkXcDJkhBDNM2_Qdx2AM4g1uRoHrysByQQU5fGZENo8MVzCfOcKVhk-pg5YLraLiZ_SCnFjhJxA00ieWYXljwx9bwRvDOHGdE8P8A_xg4BarJI4abnEWhiICFWg__fFzUDpKnzTlMofdiTrj8Sg0DUcYFHeUaqPDwlSqdhNqpWrQE55HjRDsBvPrBjtsS9XgXSiUhBeTODuOKD8Tx20r47aRad3ItGpk7H7zR_uRc79t7EZM4f0dW76apgS5UcsKbWGzepodAmeLvTmElcFXynghUKvBFHVwGChsBohg3eEzsAnEZQ8RA2DEjoLUEKCorP2azCEmEOlDAsYsBTMLZhAaWC1WyM9yeCROz9FBw27IyDJD3wVuXI1D8QMPVS8lPRcAN5awReMyWSO4hugjX0ALdX8YWmerEvpLUTt0ExC75oLDJofwo0CZUEUowGsVwTDZL2zXjQxHeqZnuY2wO8xUraQ3oZvq5ZNc2j7sT_AldYsdBqpq8S60EihTIuCjsyyDKcZn8OkIuR2UIfwGXriYILvwZyGWBSlAREyoFi7alRuRv60AQ-gfYQCpqD_nOZXY4RsKItTLr4IH7AEWTUPjDhBTXb0SyvsXCAnkKiGVK4Hx51lRVMqI0Ue7hHyFCw2zgmWEV-AdkHBB0E0ThSXwD3TF40z18JcaazSB5lvy-jxGKmmGIedMD_UtIg9FqAgFU97ilLn6k4K61Wg1Rw8fa3g7qjFtsRQMdjojleopoUMcIRHavASlGsHLywQw5zcKKyu5P4vPQVDQ5R-rjTTZQeZU2mEJ27Oo5dHQ47V2dLjASjvuTPChuLNqhz2nrHnyl5___svPP8F_XTGWWQb7BpH9286DP1cPbpBEGpWjiPFxrQsLGEwOuxUGvQNbVfMGCCOkTZ3Qoe2uaKnG2qjdgT-E7Y6sw1ythA4A36cofpGKfEL-oxIFWaww3hMLCvqbpWgClbpokaL-9lmL0LdCF2yFId16Fh1ysrUW1zOOVYu2E7k-M6Tls6bFDgnZWIs7MIvVzLQgYX4PtTYdV5_TjzROaBQnaPa5ADPOi0Z3lglNa9OSo8avSmz9pULexJ6Yxh_wdxVKVkAZAhQwbXqoVdtg1pCERCsdlwW-8KLWvnd687beE6Hy5FJ5T6WXx_j3-wSzQWjhmXIoqnG12vt3GqORwy3uAWZoNK7DpFaSvQs9qpUIzVQzM7UjknWPCkknMkLfcANPRT96I7RkaqtCt6JFa8hFJYAEFknQyQY6tExp1fgtOc964BzUVISUaeJF635Lg7aW63BCUwdr43EuJNGj22oH3-0--2_dX96n6fKSFOgTCvXkVZWCts-SLAK9G49hxdOS6ObH47UorrFgPotCAORmKEQj2w7NWs3_LoTpnEhwKRPyHbouskT_C1gqOwdEoJFTvethU6uNPiGvOxRf62QJVStcBcSooEqJlAx7VDMStg-WzaOBEzWAvWVqqxnemHOtPV5o0TCUwhVG02qHhr2V3uwhVBsFuI2y9C42D4wAgjDDD4Jml3a42dZdHcKyVn1AYB9ICKNCuwWKHeK16uMuFCo-h3iyZ80dtDuR6YWGsBr_09Kr7UQPJkpRf8GfRBnN0VwBAHtaojVtOKUEB0nzFNGYYkygRS1ICJdkDM5D5rB1oQcQgmXAxmn21vtUBRMgBwCU4MzXlebDAmBX-6dNAxZEnIeM8mYzd2jb1gpfz8XWwWngMkEBHUhm1y126Nna9N6Rc23w6XKe00I9_D5FR9-Bc-iB1Du6hgP-V6yScjYhv_z09xd__uWn_wVd0SifYLGKQFCLQJjmEI_kaKzy7KMKKQoQfor4qoAl5yv0jBdZfq51Da1LvqriMglRivoo5gKHgPA_xWCJoNNUMQwsShPRKVg9IX9FQYCuwKxTZfNyUeYxhnsrgH4UvX2_M_V9acrANaljGu0yNtxzzWbdgVBmuPXAWPzn8UQZl2P9xhjf2DA-xyDgJ5eAQfC9YrVE6ggjUN1rykWuW7kc484dJ1m2PFa-l0Gotz1lxF_Nfnuo3UXC9TAVOgYUBgoJroT3KbnjcGoHtu-JRjodFrxV8mu57doqGshGMsCnrA2WW7p725QfRGKjjwS1U0Tu36r1KTYBgnpv46VoFSf8GpMe-IKKMOBuGDRbvkOLdyzd5yK7q44Nz7PBxgqLRWbHztf8d4_UbsFqNx9WkffWp-IS9fEaCbGAeYJBUOZzpx5ohxKv0zh3IbrhYabos-rR-tfi2DAMa9wdc_16nlG-oMsPX796cfr4-elL9bmyQO-URilvhOD_w9dvnrx-8_S7b_GJPgQegHlwfNd0_CYE77Ds7bbo5c9rrZJR5FuGaXC_2WMdSr1q7LZk-SfsYUdVHkYZTU2eskdHH1SFHyzE1c-3avg6nyur3xb3QRz9JSv75uDcsfyQKhOwu7hPofG2tk-P9WaVfTdPuIEXB-epBrA3Uea4riO5PCQF9FJHac8Bj3EE_qDhK3xHk0iM5jnyfRAn6jLUl8gDA_ThZ-JqqQ0sE0tovNg71atTqnIjpziubg-VBdGjwH1TZzXG9QArkpzpRwBldZB9hfYm-6S0JY1qEE8uAbTHKQKGeczmpFahjamfoXFFdKpmW0v7x6OL-bqyxKiZCOagHU3nVYFwM3AYK8oVcF8zq6vCxbHfPPvkWy7nkRswX3qWpKFnh45l-rSd3OOqd9GKsl7GriA7mag279LNR_34T6XON0_ybSe5zFE71RPz0-581nXJvc-SwRORawoeUDB4hg3mT1AD4iQaeUYkXMdg0nYCP_AigwvTNzi3uWnL0LIMRoVjKBR27eR2ZfO8E9Pakc0DN-OGDh-yeUM2b8jmDdm8IZs3ZPOGbN6QzRuyeUM2b8jmDdm8IZs3ZPOGbN6QzRuyeUM2b4eOM9sIObzvSHGTbF66XNQ-6Iun9rAvtE0tw3Kiodqts36mbTDPkpEwzQaRd0jRapJ3oTpB4UplUMG0wRMikWAUX6swXeGRCljWdLfGo9_Gpd52hd5SdInZMd5cUaF66FGGIZk5JDOHZOY_YDLzFhcQXE3_6KB5d-qw0_De1OGzOMVUW4M-NG5D7azYhU27qCBiQnPVimJtRjWtoHUa4UWxRLifd2awJ9_XkAgvliIF6LtlgzXUQBNFy4YEJ8vsQuTF1YE29q0iQ9ElXyAhjaO8V9TOZ9TlmkdVtKnHXgOn4nbZQ9sOmQ_xuiOj0LIsEYQObB4etULWNxQJfnXQ-eYyN8nDJs1zffLw86jPzTOiTTZrX4KuTVH9Kgm6COy9wRnFi6UCP4psR0BoCkMwfLBphg_40rB9K_S8SFoh86Rlevi0QD5TKKy_Z0pX0nLmiWGf2N6OtJwROdC2MIe03JCWG9JyQ1puSMsNabkhLfcbpuUscJAOZYFlOE5fWg7jZX2j5M6UnMpTNctO1UQVHK0jfA0xYRvgCutp407Y0Wz84rVqEoXyTkul9W2KP53gTj1blsrFqfAyV4-NO3bkfm2Q3m2o8LUtSQCvEL8Wx2rd7z_cyBpim7sSh3uxfSFKtC_FkEocUolDKnFIJQ6pxCGVOKQSh1TikEocUolDKnFIJQ6pxCGV-IVTidtJw4SuOEbKsI47Uofbf91MIG6FIL-3XGJn8L9aRvGG9373NXTbO7z72rrVbdy7852rRSRQdd69O4JgEj4xJ0cfPuzvwXY8K4ysa3rouatUxXK4uMrxrwpCyFeaJQM4fIEwK8O_mhjCqZ8sEvec6wuoLWzJnduO58EDa7JBIGwTvZMHD_ouI5WmKT1pHSyGQwLxPjEw0-U-t24vBrsrhrhOCMPsN-gPdKgNBULWonxIVr1fs-F7YSTpweL5zLeJg8MKJbfs247nBWD7Vg7FPF5CJIXakgO0hOiCN973ApaSRKLvql_QUp_KyP4yQvm8V-Pfyur0XWJ_q4b6LqW_VUOO61lmaG7e8vy9JiZx-eLrpQ7ufecLfd-Z4Rjg7xz_Dr2eFuc1S5UptK7wpCIPFIxR6Qb8fHYV6PXII5AmjULq3GFkYzKbZwsxUzDlQmVOqnSozsiglQAEsFLBWSQwxsMoHoLcCbzZ40jNIPLQlm5-JU-egbUR4BIyDBevWairT_d9CY7pmZZrOYf29-ABhgAzFbbOVFIIAhZJY50M1lyXpvbJIgZUkp6NVRwj8rxviRxq4jd-WYcP6_UaIP2l6icvNCM0W7DlVA9xslzP0KqrzNSsiiGUbc-Svsvibe5Lg9mHD-uJCpAU46eEo3OyRCyWyBop3cFxPUL11jo21Unk2ee5V_8m5uKz3jRw4xvm943s8Lq114pLwR3dyT8hZ54h4wca-fL0zZ-65VW63gLjVVUjptYAwMcCPp7sg7t7e38lyrisych7e7Iz93CX1H-8N9mHg3s60T4Pm12lDSYZVx4ZKUG6wHxac6gQPiiytPHUGAHl4D7BNOVbt3l04PPe_p-rzGaba0NDpzAtxC1LYqpukIDO5G6gsFO6HVS9-xqRU2Tqobkr6PkMF7yqGEB1i9OV4nX3YOT9ravhW6SymCofuxMW74PBu1t-nn3US1W9vi0GnbXRfU_2IdprBm3rTIJSfXXZSrLW2WiN23bC18k-uLq7r5eg0Vm1sxShP2YJcsr1bGAOav-scqxKJAhLJ_sA6O4enuHXNu7WGNi4coXcyGQfnNzdJBbk9OpgoVZZ5wMqWSmIO9kHE_duiuqWGy32F99Nn373-s3ps2cb-wQr4aiqtViCNJfa9ChVjjVJBkNa1ck-lebbBzL796ZyMqqa50rOL23qvYgOfIVWock-FLq3p0eq2rfSsy4LVylbZWJ5F8bV2cU9QHW_ltMdSBSAh0osTPYh0D2KjF_qoInzMdbkqYuFwDGU20Bzsg8_7m63vgmIoP8-7jjx0cbuLwRyfWp_VPm4N2-ev52-nb7-89Nnzyb7cGGfaLawyG65dDDfNeNXYlCmpEJ2mM5BDNfkPhTWQ6ZSmS-AMzK-nOyDcjfoLUv4GBYFC3hFWUFJbB5hzGQfFrum3S64IoyuCk2DwwZYofqge9yZ15nsA1l7N0LTpVrIP714_qTmvJEYzzHZVbuSvq5udJ8XlpfU-GbjYq7anCmLUnnKCnvrhEZVxyNSttVvB6xdC6qqTbLB-cN2n6-g87GkTNkcVb6KelPLHF-pPedmtX8uflAF-ci1PhZ4fgB1itTkRrVC4zzDohowN2rZYMkmAOonPyCkwVCsbuVE9VRV9YOZo6kqPi4EjA4MsM4hrtKPddG9AmmK8cnFMitindYrMugBaWWcDHq4PMYqyrpqVEtBJT3LRO-E4mGT2RFa8l0FbjZJZdxhr9QIaYKcsz7x8E1rjyrzVqhWlMsiKgms1jyDafCYKwsrtMs52cJ1y1XZMbY1MsIRKL_S6sFI7wYlKbwnrpO1bKXdzBRcaKYLq5Rx0Larg7M1xL4A1YcmU-iTCT4hL1XCuq4uaeWstkSFiWvcuqBcaXYhqtQX5jaxlLl2ZOoKuItsBdo8j8vbHcYIPCsybZ_bviFs4cLghMNtEXRhtc65axeA49t2Eidawi2MGNWlXn8g5W4jjHW9tVk47lr6jsqM1D4qWLbEFG-9nbBSoXvyozlJ8Kuc_Bho_oHmH2j-geYfaP6B5h9o_oHmH2j-geb_IjT_zc9MX7kt19m4Ltf4tPvc7a9y1pjJiIeOy0xpMckiH7a5Tc3AcAPLliaLPEt63JLcFIFJfer71JKB7VLHMYVgvrjZ9K6cO7ZOXOPEdnecOw49P4gsGg7njodzx8O54-Hc8XDueDh3PJw7_g3PHTPHtjkzXOlQdzh3_CudO0YNAZcm8uo0UqmVItIEcxsb1H3MsDhkNqkgOsoaRzJrjht8P3vYodbvFZt5shwsojJedXCk7kVaawY7S9TpHi2rUiAdBl2C0Z4MZ6NvdTY6kJwHLDBNN_Rvcja6_zYA7kcOwFTmefb-s9CPsyotgZYEMwATtZ9q36gTV1eclra2AJyajEuM3rnI3qedQ7dxWXsdvZBaqfGw40ehVaQKsSslU5u9kqXSsh5RMQhlQg6yCaKe09gPHpgtM1pXJNSqsnNSKopViZbOAeb36Yb-jhrC8IYaOto8_ay0Yc-BZ9J33lnRNp38l85FKkQiEXN0IWSbq6xQDby36DsW43rCiszA91vd6-QJto8pHZIBUGMr11cLmq7xuxQCZd_0qAwMq42ZmpRBs9YHJQPqk5S25QQQVQsunU6gV-cHrh7t-4In7S0GWNsLAs7dZiyd3EAz38NZfxB8gtszLkbtCUVFNtEKEKkKqFueau8kDH6fp9odYQUgVyMw3cYkdrIK1aA_S76g6jEUbhBFSB-0Z-o6KYTfw6URvRKTpmSu4bgOtej-Sx_eqPqudrSg7ppLVh9yMtusFDvpFJHN9Nn1sgXNjQvR2emqnAwj4rQAuHNClC3fLD3brDGrvI2ysKDWYGI1kaprOPtsIHNlxH0WuqG9_wKIBw-cfRdPwNbbMtH1BowZCmK1VEUjymIrbwcTAgxLEwzw1pgTSPvP7bt4TJHaPASzvP8yCYgT6qPnqUD5d2rYZjuK1pTL38B7SUa5Pr6rbhlQp3J1cU-yflghzHg50yKVqxzXj6iDwMhFY41mU2JanaZ9n26U0nTrbHrmO9xD8Y99D0VoRo7nCgC8TjPtTt6vRbw3TePV8DAK8PvquOlHzZp2Mnv1bRR3SNTl4FyVAOrxCK5JQ1Ro2FC5wKVCNlbVZgH0BayUV_XXKr5tFrLv0iHXMqkdChvC9QYKtHnAJrS-S1qvk6zBnVJgJKe_zrIKPdWpbayiissTMmtqfsB0z14--8u3T7-bPj59czpT0ppxISlet0G-XgiaKnBHmuK1pr4LL4hI1NdZ7ipUbOqv8B4KdQdFJNCKx4iLsT2IRe8D-JEa91Q2tpk48q_QkJYBtjzCmXRH3mFoVYw6q7Hi9HKqYN20WVQtVFjqGQymEDjpKw_rwld8FgNNJcDqezypOqWAhh6CJaVTWDnWRam6dBb0T99iomC6pn-wmFfF6N3aqhlW8yrKr7pqY6aLaxd8pmdyOUXfOK352HoCgA4SgQZhto3ckRPQIapS1E6UW1MtVUgWiXoG5Gooux1hGxLguQGG1WaivUygSRK3G_tGad_6gibqMMlMg7OgAZ2dTHDjnw_P7eaInp-WRXuCAVYToqcs-SjwJhn8elk885B1LVFTX9ipf0XlVPqn1B6LA3NUjAI2myZNkvgcBgmivQcWE4JofR3GvYLl8bIsjtXop1gLulzfA6WLsZFqGNh1Vbj8Pm03Dbat94BI8AuzUOc3Kk5RGeN0k-WZNfWmsz7YITDn5vjct5s0WCfX3Qj-8Ow11_G_5rYwIr5ASkmV9xZEJSRhudB8KsaoSvvpjuqSU-190KEl6uRJU3O9oLqYFdrTkSdmEOa6cJOWdUX8_mvBfIO6QvKQuWZLdzcZ9Wbyh-fIlbbACssEYg0cZXkhQCPANVSRh1Ki-uaTLC0UI4yVq9qO6jLSnab0Iejclu1TySUZX2JKqqsbw3VR_-jXRcnACCNBqTQ88Tu4Lur1VcVsjhVEGShkc6EUyHbXjVLkwAulNFDbulGK_AYXSskIE-SGZfhhcLsLpcjOf191b1sCIDraOKhQ8dMqZlOA6ndyK1X3hJU-0KHnogIJDGDxQEMVTi5BxeiZqkLfPY1_4iuuTDuy3cD1DCPkh1xxhe61aNPMneuuqvBy69IrcFsAUBUS1YcNAfCM1NDr1VJ-4KSDcytGeq6SRJhBhz0f65TXdupgx1m7VXV84tqbPIc7t4Y7t77QnVv9X9Tz__YLeTrVPW3B41a90M3P1XToswNqwHffkNAZ4fXnFZvzfHWmLLsAX4F-qg79yotsDFsEYu26imyseUuKOSyIyyb7ZnSjywv0-Sr0fZpCA4iK2b_23gLsZ4z9VAz3nq8LQmutzobpEBLsoLhkuJ4QhTZfD4TVDylb64Arwt2raoYQHAIy1d-DXF__hhme-GyOcVFF1dzusFnkAVhxmGlbkRd61BOceZ5henvOvypx1hJWcq277R4Aa0o6rz8A9jtT1JsfxdvxhTvWp911rb9KXa-ACDYMXVeYvs0tTxpYustpAIgBpeI4ITfd0DMdYYa-lBAiRGCiAuGIwHVDy98_pe1aXss4ccIT19pRy8sN6NEzjaGWd6jlHWp5v0gtb8D8EMy0RX3b_W1reV93WDG66Rm071XuIZNIcS-Q8QIfDXvjbD7WjRL017DuuPqqg62sW3X_RFUX2daXXWB6sF3H1hcOFcZDhfFQYTxUGA8VxkOF8VBhPFQYDxXGQ4XxUGE8VBgPFcZDhfFQYTxUGH-uCmMRGNIG90IDIW5eYfzvK1hSnSJYIGnBFKdeU-lbpcUnpFjlUm3kPvJE4wQlPlV01mFQFKuCzrSiURRr8hR9_1C2PJQtD2XLQ9nyULY8lC0PZctD2fJQtjyULQ9ly0PZ8lC2PJQtD2XLQ9nyULb8W5Ytf_j0fzaF81I)
