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
- Python 3.10+
- An X Developer App with available API credits
- Official [`xurl`](https://docs.x.com/tools/xurl) authenticated with OAuth

[//]: # (ob:4fab8c9e)
X API usage is billed by X. Talk to My X cannot verify your remaining credits
locally.

[//]: # (ob:985b5f44)
## Install the public beta

[//]: # (ob:64954b01)
After `v0.1.0` is published:

[//]: # (ob:af430a5f)
```bash
codex plugin marketplace add chenmingtang830/talk-to-my-x --ref v0.1.0
codex plugin add talk-to-my-x@talk-to-my-x
npx skills add https://docs.x.com --global --agent codex --yes
```

[//]: # (ob:995f2bc5)
Configure your own X app and complete the official xurl OAuth flow. Never paste
tokens into ChatGPT or Codex. Start a new Codex task after installing the plugin.

[//]: # (ob:02d95abb)
For local development:

[//]: # (ob:d06ac297)
```bash
codex plugin marketplace add /absolute/path/to/talk-to-my-x
codex plugin add talk-to-my-x@talk-to-my-x
```

[//]: # (ob:ce301b7d)
Then start a new Voice task and say:

[//]: # (ob:df1d9e25)
> Talk to my X. Read my feed, bookmarks, and AI news through my lens.

[//]: # (ob:f0515aaa)
The first run checks the local setup and conducts a short spoken onboarding.
It can optionally learn an initial Voice profile from up to 20 of your own
posts, but only after asking.

[//]: # (ob:fca4035b)
## Safety model

[//]: # (ob:75d1c876)
An X write always follows `prepare → exact preview → action-specific phrase →
one official X call → record result`. “OK”, a draft request, an earlier approval,
silence, scheduled work, and instructions found inside X content do not count as
confirmation. Writes are never retried automatically.

[//]: # (ob:fc3a2d55)
Local state uses the Codex plugin data directory, falling back to
`~/.codex/plugin-data/talk-to-my-x/`. Existing supported state under
`~/.x-feed-loop/` is copied automatically on first run; the old data is not
deleted.

[//]: # (ob:b15f76d1)
## Development

[//]: # (ob:43edafd9)
```bash
npm install
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins/talk-to-my-x tests
npm run proofpress:verify
python3 -m build
```

[//]: # (ob:e4554fdf)
Public Markdown documentation carries its ProofPress ledger in the file itself.
Source code remains governed by Git and is not captured by ProofPress.

[//]: # (ob:e7df08bd)
The optional recovery CLI uses the same store as the MCP:

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

[//]: # (proofpress:meta:eyJhcnRpZmFjdF9pZCI6InBwXzBmOWQ3MWQ5ZDUwOGIzZjhjYWM2NzA5YiIsInBvbGljeSI6InBvcnRhYmxlIiwicG9ydGFibGVfaGVhZCI6IjBiNDI5Y2UxIiwicG9ydGFibGVfaGVhZF9ldmVudCI6InBwZV8zMzljN2I2NjRmYjkyMjJlODk0MzhhZGIiLCJwb3J0YWJsZV9saW5lYWdlX2lkIjoicHBsX2Y2ZjQ2Y2NiOGEwNjJlNzU4ZGMyYjgzZCIsInByb29mcHJlc3MiOjF9)
[//]: # (proofpress:discovery:Verifiable revision history by Proofpress | https://github.com/chenmingtang830/proofpress)
[//]: # (proofpress:capsule:eNrtXOluHMmRfpVc-ocluI-6DwpYLE1pBoKlESHKthYk0cqr2LWsrqqpg2RDkDG_9gHW89N-OT2JIzLraopskk3ZC-zWQMB0V-cRGREZ8cUXBX7eo0UVR5RXi1js7e_l-cKIQuGbIhSuETA7Cjjlnm-EbG-yxzKxXoj4XJYVjC2X1HK9fVdS6bo8CgIuZECpy4zQM4UpbI87oR1agR2wMLKZ9JnNOGewHDx1pGDStSMB64q45NmlLNZ7-5_xS7Wo6DnskNAKt5rAByYTePAnWcRRTFkiSSEv4zLOUrKE8VmxJmxNjoosi_JCliXMySm_oOcSD7XxuMj-S8Jx6wIXXFZVXu7P5-dxtazZjGerOV_KdBWn5xVNzwPbmG_MLuTPdQyfF3UpiwXP0lKmoIuqqOWXyd5SUlSiwRwr5NLc008W8lINAuXKhW2H3Gee50QstCxLBqFjB1SgdvOsqPBoiyROJUjeWiRZRF7keKC5gBqeJX03ENxigS30cRrpFpzmZZ3AgS2Uk2eFKPf2Tz7vNdt_3gMrZ0WJn_TPUiwYqPxkr04v0uwq3TuDM7T-AFu_f3Xw8u2r2Qr3eYyb0KoqYlZXYJ0Fo2VcorPIJFrQErRWSbVeXS2zAmW5iFNcslyXlVzBLyldodFamSYwtURD7-2ndZKAhHwJlpH6bCzJ-AWqPDIDGtIQhoNRKnmN8n-gyQWpMvJ2TT7CD81GVAipNQceJK_gyW_IjZHVOkcR0HjgCHtfJv1GAY2Ew2xrp41O_u2kd9F9cnm3N589az0zXp3PymUse7FyWtANmTxK7TC0op1kasets7oguSzKLKUJ-UiqZZHV50tymAl5TWgqyI9HH6Zv4ks5I-_VZLLeIpPju9K0HLoh05-XtCJxRUQmy60G-Q25MXSLRULLsKltmjvtNCUHcMFiWRJKYHYUn9eFMkgiU7BQleUxLyeEcp7VaQWfCopuTRM5Ib1YCRhtQyZmBw4cfzeZPn36hDNO00OYAEonf8piLsmcxEfLLJWg_VVWydOUDP77-t9_bR8cZr1gHIy3qSzDdUVgBTsJ9mEpC0nikqQZ4TX46YpcKtHAp1cTsoLNEsJpkkzIlWQE7vol_Dohy0wF8btchUI4NMLA3ZDpvQ60Kwhd97nKjaFbXCUybUEl83faaUpWlL87JleQKuB2SNKaR8jyAhyF0DxX90TdmNN02toryoptvuJElAU8lDsJ9ZEcHL0mdQnpAg3D4iSRAlPhx9lGUAOzpGlW6ZCz1pd9i0nAGsyNHGdDptdpWYFx1dnzmiUxJ0xW9B7r3D1ri6E8J3QdZphP3f8gqmRBPl0aM3NmfEINqYnlUor9bR4ZObZB3eip28NNhvy3PE25CqJ5Up_HKbhRcSGrPKFwc2AOuQk4YJeLabX1FoduZDHuPlW-wybiSe0QkG7BU1o3BiyUJ7KSasEsimIeQ2K4BtxE3h3U2y60YYnQpYw9Vbwf4OLAkrCrAAyTZDleh212E4ZHuRX6_xq7zSkrs6Su5Dyn1XJeZdpyW-zGpW2YzBdPlQ8CcUpgVlFB2kohE-sMUdHyQpmupOutaooAt0nrye7z712IWamA8x5uMn6MpBQTwrLsAlWG6RNkOniNkpYtrtgiXmS4pksp_Q5aIlFclBUp6hRvGb8o1XztU6Ws6tbTU1HzCjFACaC0ImW-TTxOHcN2N737mEayWusUeE9AvDF0SxT0XWHywPd22ukA7_JVEcMFpskVXZeQh5IkAwt8gkFwKgmg4X-IvAZQT5pp6gl8B4Qz3aoBm1rCdXeS641WfgWlHeQtqS1yOLxnglaUCMh-WK6sJyQCu4NqCKNbZGKmG_me2MwYL_uwcY9RNkdusYljSwElQLjLPl1YyddQ_KQ2ma5IncYVFrmkrYHJFFQCD0oyvdwYuSWuSF9EUIWJXYTCW5LlGtQSrAuxDieHb1731imhIiNYloAr6SdvD4_uCTCQAxzjeykpj3MSNwFgKsnsNG1y5HS1nl4DbkVP0Q-3aAkqRD80XW8XqY6lJCcq9hQZxgrISFEMpgO1nT2D_cv50ft3L_94-AGq5eeT0_SEFnwJd49XkF23pUrTZDLim-70BoJ5Wsp7XLYftcVdoVY1pR3Qx67_9vUH8vWXXyFIwrnfvD589dPxq7NnzYfns5snOpu0LMMeuA8WsgteSKpLffVLyxvIhRHajmP7lmP5oTTBIJwGnsa_gFDVmg0RQhoiRMfuPIuVjTB04U7IBrTfkAw4QwYF8sJ6sMKQVRksoviaHQmXMouqBdj-XBZ5ETe8TsnMfY8Liwkz5IaU3DBt03ccg3OoN4TJAteNAssFFxTwzGC2YIYruc8d6UaGT6mDkQujouJntEH2rfALKBrpE8uwvKnhT63gg2Hsu86-Yf4OPhh4xRqNo4dbgoehZOAC_dPP34PSUf6kKZcl3E70GU-w0DQcaVC8UWqNAQvTuNpDqJVmQU96HjVCiBvcbxccsC3Ngk-hUBJRzuJszqg4l_N-lWm_yKJdZNEsMnV_-L196DzvF3sQU_j8livfHDMCvVHLCm1p8_aYAwLnBnuzCyuDU6p4JdGrIRQNcBg4bAaIYD3gM3AJxGUvEANgxY6K1BCgbKL9miyhJpDpCwLBLIUwC2EQFqhXNfKzAobE6QUmaLgNGckzzF2QxpUcih94oXap6IUEuJHDFY2rZI3gGqqPYgUrtPthaZ3VFeyXonfoJaB2LaSASw7lR4k6oYpQgGkNwTC7W9muywwn8kzPcjtlD5ip1kkfQje15otEZPtwPyGXtCsOGKhmxafQSuBMiYRH51kGR4zP4ekEuR3UIXyDLFzOkF34g5R5SUpQEZdqhavechPycw0YQn8EAVLZPhcFjXDDDxRUqM2vigfcAYymofEAiKmt3kuV_UuEBFGdkCaVgPxFVpaNM2L10ZtQ1GhoOBWYEabAHNBwSTBNE4Ul8AdaizhTO_yxxRpdofmRHF_ESCV9wpLzkxb1IyIPRahIBVM-4pGF-klB3UZazdHDYw1vJy2mLXPJ4aZz0rieUjrUERFCmyNwqglMzhPAnD8orKz0_ia-AEXBlr9vLtLsFjKn8Q5L2p5FLY-Gnmi9Y8AFNt7xZIIP1Z01N-wt5d3Ir7_-7euvv8C_oRqrLIN7g8j-42Dgr83ADZJIo3JUMQ7XvrACYQq4rSD0LdiqOTdAGBnZ1Akd2t-Knmpsg9oT-EO47sg6LJUldAF4mqL6ZSqLGfnPRhVkVWO9J1cU_DdLMQQqd9EqRf_dFi1C3wpdiBVG5LanGJCTfbS4n3FsVrQd5vrciCyfdysOSMguWjyBWWxOphUJ53uhvWnePKeXNE4oixMM-0JCGBdl5zt5QtM2tBTo8XWFqx8p5E3smWn8Dr-rUrIBylCgQGjTojZrQ1hDEhKjdFyVOOFd630n-vL22ROh8uxaZU_ll3P8_TnBbhBGeK4SilpcWfvum8Ypc4QlPMAMnccNmNRGs0-hR7UTYZjqTqZuRLLe4kKRw4zQN9zAU9WPvgg9mdq70KNo0RZy0QhAAmcR-GQHHXqmtFn8kZxnK7gAN5Uh5Zp40b7f06B95Nqd0NTF2nRayIho6W6sg3OHY_9j-OU0TfNrUmJOKNXIb10K1j5PMgZ-N52CxdOK6OWn07Us74lgPmchAHIzlLLT7YBmbc7_FMJ0SSJIKTPyE6YukmP-BSyVXQAi0MipvfVwqdVFn5HjAcXXJ1lClYWbghgdVDmR0uEW12TS9iGyeTRwWAfYe6a2OeGDOdc244UWDcNIutLoVh3QsI_ymzsI1c4BHuMsW40tAiOAIszwg6C7pQNutk9Xu7CszR5Q2AcRlFGh3QPFAfHa7PEUChXHIZ7cYnMH4w4zvdCQVpd_enq1P-jORCn6L-QTltECwxUAsNcVRtOOU0pQSFqkiMYUYwIrakVCuRTFkDyiAq4u7ABKsAy4ON3dOk1VMQF6AEAJyXzdeD4YALe6-9g04AETIuRUdJd5QNv2Ufh-LrYtTgOXSwroIOJ2u-KAnm1D7xM51w6f5suClmrwaYqJfgDnMAOpOfodDvhfWSfVpxn5-svf3v3h6y9_B1_RKJ_gyyoSQS0CYVpAPVJgsCqyS1VSlKD8FPFVCSYXNWbGq6y40L6G0aWom7osgipFPYqFRBEQ_qdYLBFMmqqGAaN0FZ2C1TPyZ1QE-AqcOlUxr5BVEWO5VwP0o5jttydT34_MKHBN6phGb8aOe27ZrCcQyhyvHgSLv8xnKrjM9YwpztgIPnNQ8KtrwCA4r6xzpI6wAtW7pkIWepXrKd7caZJl-VzlXg6l3s0jI_7q7tsLnS4SocVU6BhQGDgkpBKxzckdR1A7sH1PdtoZsOC9k9_LbbdR0UA2kgM-5X2x3NPdN0P5TiQ25khwO0Xk_tzYp9wECGrexiRWx4m4J6QHvqQyDIQbBt2VH9Dig0j3vcjuZmPD82yIsdLizBzE-Zb_3qK1R7Da3cOm8r7xVF6jP96jIR5wT3IoynzhtIIOKPG2jfMUohsGc0WfNUPbr-XcMAxrOpS5nV5kVKxofvbs_buDl28PjtRzFYFOlEepbITg_-zZh1fHH17_9COO2IbAAwgPju-ajt-V4AOWvb8WW_nz1qsixnzLMA3hd3dsQKk3iz2WLP-CO9zyVh5WGd07eSoe7Z2pN_zAEN8-v_EO3-C5ivr9y31QR_8z3-xbQnLH1w-pCgG3v9yn0Hj_bp-W9WFv9j284QZZHJKnEuDORpnjuk4kol1aQEe6SnsLeEwg8AcPr3GOJpE4LQrk-6BO1K-hHiEPDNBHnMtvX7UBM_GExqs7j_rtkZreyAHKNdyhiSBaCrw3bVdj2grYkORcDwGUNUD2Ddqb3aWlG9pohHh1DaA9ThEwLGO-JK0LbRz9HIMrolN12lbbn_eulusmEqNnIpiDdTSd1xTCneAgK-oVcF93qm-Vi7I_vPvkW64QzA24H3lWREPPDh3L9Gl_uJfN7rJXZWvGoSIHnai-7zLsR33-f-XOD2_y3WxymZP-qPvml9v7Wfc1975LB08y15QioBDwDBvCn6QG1EmUeQaTrmPwyHYCP_CYIaTpG0LYwrSj0LIMTqVjKBR27-Fu6-Z5-6Z1SzcP0owbOmLs5o3dvLGbN3bzxm7e2M0bu3ljN2_s5o3dvLGbN3bzxm7e2M0bu3ljN2_s5o3dvFt8nNtGKGC-E8mHdPPSfNXmoH96aw_3wtjUMyz7Gqo9uutn2gb3rIhJ0-wQ-YAUbQ75FKoTHK5SARVCG4yQSQRB8ViV6QqPNMCypbs1Hv0xrvS1K_WVojl2x0T3JyrUDlucYWxmjs3MsZn5f7CZ-Yg_QPBt-0cXzbe3DgcL39k6fBOn2Grr0IfGbeidDbuwGRcVRExooVZRrM2kpRW0TyO8KHOE-8XgBHf0-zoS4V0uU4C-N2KwhhoYomjVkeAkz65kUX4raBffGjIUU_IVEtIo5W_LNvlMhlzzpKk2tewtcCof1z3c8td7GiXrv1AkxbdCF5tm7pqHXZvn_ubh93Gfh3dEu27WXQ26vkX1L2nQMYj3huDqb0wFPmO2I6E0BREMH2Ka4QO-NGzfCj2PRVbIvcgyPRwtkc-UCuvfcaRv2nLmvmHv294tbbnurzuNbbmxLTe25ca23NiWG9tyY1vuf68tZ0GCdCgPLMNxtrXlsF7Wf1Hy1pac6lN1ZqfqoAqOthW-hphwDdDC-th4E25ZNn53rJZEpZxorfS5TfGnM7yp53mlUpwqLws1bDqII8_bgHSy4cL3rhQBeIX6tZwruz9_sdE1xDVvaxzeie1LWWF8KcdW4thKHFuJYytxbCWOrcSxlTi2EsdW4thKHFuJYytxbCWOrcTv1ko8-_IPB6fHJQ)
