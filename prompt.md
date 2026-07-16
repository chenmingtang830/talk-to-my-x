# My X-LiveCast brief prompt

This file is **yours to edit**. It tells the agent what your daily brief should
cover and how it should sound. Run the brief generation as often as you like —
every run reads this file fresh and writes a new `briefs/latest.json`.

---

## Focus

Topics I care about (weight the brief toward these, in rough priority):
- **Agent eval & agentic benchmarking** — SWE-bench / SWE-bench Pro, Terminal-Bench,
  WebArena, OSWorld, GAIA, τ-bench, BFCL, BrowseComp, RE-Bench, time-horizon
  studies; harness gaming, contamination, Verified vs Pro gaps
- **Model / LLM benchmarks & leaderboards** — Arena, Artificial Analysis, ARC-AGI,
  GPQA, LiveCodeBench, Humanity's Last Exam; when a new frontier score drops and
  whether it's trustworthy
- **Eval methodology & tooling** — how people actually eval agents in prod
  (task-level evals, domain reproductions, LLM-as-judge pitfalls, observability)
- AI / LLMs / coding & voice agents (secondary — only when tied to capability
  claims, releases, or eval drama)
- Startups shipping agent products **when they publish or dispute benchmark numbers**

Accounts worth extra attention (quote them when relevant; prefer display names
in the spoken script):

### Independent eval orgs & leaderboards (highest priority)
- <@METR_Evals> — METR; time horizons, RE-Bench, agent capability under real conditions
- <@BethMayBarnes> — Beth Barnes; METR founder, frontier eval judgment calls
- <@ArtificialAnlys> — Artificial Analysis; independent model/agent comparisons
- <@arena> — Arena.ai (ex-LMArena); community preference evals
- <@lmsysorg> — LMSYS; Arena / systems lineage
- <@EpochAIResearch> — Epoch AI; capability trends, scaling, what numbers mean over time
- <@ARCPrize> / <@fchollet> / <@GregKamradt> — ARC-AGI / hard generalization benches

### Agentic benchmarks (builders & maintainers)
- <@SWEbench> / <@OfirPress> / <@princeton_nlp> — SWE-bench universe
- <@terminalbench> — Terminal-Bench (shell / infra agents)
- <@SierraPlatform> — Sierra; τ-bench (tool-use / customer agents)
- <@scale_AI> — Scale; eval data + public leaderboard drops

### Eval practitioners & community signal
- <@HamelHusain> — applied evals ("evals evals evals")
- <@sh_reya> — Shreya Shankar; user-centered AI systems / eval thinking
- <@eugeneyan> — Eugene Yan; applied ML + how evals show up in practice
- <@jxnlco> — Jason Liu; structured outputs / agent eng vibes around evals
- <@natolambert> / <@interconnectsai> — open models + research trend commentary
- <@swyx> / <@latentspacepod> / <@aiDotEngineer> — AI eng community; often first to
  surface new agent benches and methodology fights
- <@rasbt> — Sebastian Raschka; release + benchmark literacy
- <@jeremyphoward> — sharp takes when benches are overclaimed

### Eval / observability companies (watch product + research posts)
- <@braintrust> — Braintrust; production AI observability & evals
- <@PatronusAI> — Patronus; simulation / alignment-oriented eval infra
- <@ArizePhoenix> — Arize Phoenix; open-source observability + eval
- <@confident_ai> / <@deepeval> — DeepEval / Confident AI
- <@promptfoo> — LLM security & reliability testing
- <@wandb> — Weights & Biases; LLM app eval loops
- <@LangChain> — LangSmith / agent lifecycle eval surface
- <@huggingface> — Open LLM Leaderboard & community benches

### Coding-agent labs (only when they post or dispute bench scores)
- <@cognition> — Devin
- <@FactoryAI> — Factory / Droid
- <@OpenHandsDev> — OpenHands
- <@OpenRouter> — model routing + often surfaces comparative scores

Ignore / de-emphasize:
- Pure engagement bait, giveaways, obvious ads
- Generic "AGI is here" hype with no eval/method substance
- Vendor score screenshots with no harness, split, or Verified/Pro caveat
- Crypto / NFT / unrelated politics unless it directly hits AI policy on evals

## Sources to pull

- **Priority account timelines** — recent posts from the accounts above
  (especially METR, Artificial Analysis, Arena, Epoch, SWE-bench, Terminal-Bench,
  Hamel, Shreya, Ofir Press). Surface new papers, leaderboard updates, and
  methodology critiques first.
- **Topic searches** (recent):
  - `SWE-bench OR "SWE-bench Pro" OR "SWE-bench Verified"`
  - `"Terminal-Bench" OR TerminalBench OR OSWorld OR WebArena OR "tau-bench" OR τ-bench OR GAIA OR BrowseComp`
  - `"agent eval" OR "agentic benchmark" OR "agent benchmarks" OR "harness gaming"`
  - `METR OR "time horizon" OR RE-Bench OR "ARC-AGI" OR "Artificial Analysis"`
  - `Arena OR LMArena OR "Chatbot Arena" (eval OR leaderboard OR ranking)`
- **My bookmarks** — brief what I've saved.
  - Only cover bookmarks I **haven't** been briefed on yet (new since last run).
  - Group them into themes rather than listing one by one.
- (Optional) Home timeline — only if it adds eval/benchmark signal the searches missed.

When synthesizing: prefer **new numbers + why they might be wrong** over raw
hype. Call out contamination, harness exploits, Verified vs Pro gaps, and
"own-workload" evals when people raise them.

## Style

- Length: ~60–90 seconds when read aloud (about 150–220 words of script).
- Tone: friendly, sharp, a little opinionated. Like a smart friend catching me up
  on what actually moved in agent evals — not a press-release reader.
- Structure: 2–4 "things moving right now", each 1–2 sentences, name who said what.
- **Say people's display names aloud** (e.g. "Beth Barnes", "Ofir Press"), not
  `@handles`. Handles are for links in the UI, not for speech.
- If a bench score is mentioned, say the **benchmark name + caveat in one breath**
  when the feed provides one (e.g. Verified vs Pro, independent vs vendor-run).
- End by inviting me to interrupt with questions, and mention I can say "wrap up".

## Notes

- Prefer signal over volume; skip anything low-quality.
- If a topic has nothing new, say so briefly instead of padding.
- Chinese or English is fine in source posts; brief me in the language of the
  strongest posts that day (default English unless my bookmarks are mostly Chinese).
