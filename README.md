# RTX 3080 20 GB

Serving benchmarks for a modded GeForce RTX 3080 (20480 MiB, GA102) on CUDA Linux. Not a distro project. Weights are not in this repo.

## Two profiles, two jobs

Pick by prompt length, not by preference. The fast profile wins on near-empty prompts and loses badly once the prompt grows.

| | Long-context profile | Max-speed profile |
|---|---|---|
| job | daily driver, agent work, anything past ~7k prompt | shortest prompts, fastest useful answer |
| engine | turboq qwen35 fork `aaa66a5` (llama.cpp) | HyperQwen `slim-20gb` fork (vLLM 0.28.0) |
| weights | `orcarouter-uncensored-IQ4_XS.gguf`, 15.57 GB | `q38-lemin` W4A16 AutoRound, uncensored |
| usable window | **196608** | 61440 |
| fresh decode | 76.41 | **84.69** |
| 33k decode | **57.51** | 24.79 |

The two profiles run different engines on different checkpoints. The numbers compare profiles, not engines.

## The curve: decode tok/s by prompt fill

Same protocol on both, 600 completion tokens, temperature 0, median of n=5 plus a discarded warmup, real visible text in the answer.

| prompt fill | long-context (h76) | max-speed k=3 (h95) | max-speed k=4 (h98) |
|---|---|---|---|
| fresh | 76.41 | **84.69** | 81.68 |
| ~33k (33355) | **57.51** | 24.79 | 25.30 |
| ~60k (60000) | not measured | 17.61 | 22.65 |
| ~91k (91655) | **54.40** | past window | past window |
| ~111k | **55.54** | — | — |
| ~150k | **51.07** | — | — |

**Crossover near 7k prompt tokens.** The max-speed profile leads only on a near-empty prompt. By 33k the long-context profile is 2.3x faster. Interpolating the two measured curves, they cross around 6.7k fill at k=3 and 4.7k at k=4 [INFERENCE, from the two measured endpoints]. Below the crossover use the fast profile, above it use the long-context profile.

**Why the fast profile collapses with depth.** Its decode falls 84.69 to 24.79 to 17.61 as the prompt grows. The suspicion was draft-chain starvation rather than a hard kernel limit, so the draft chain length `DRAFT_TOKENS` was swept at a fixed winning shape. Every arm is one window, five timed runs plus a discarded warmup, 600 tokens, temperature 0.

| arm | fresh | 33k | 60k | verdict |
|---|---|---|---|---|
| k=2 (h97) | 79.65 | 26.11 | 17.44 | reverted, fresh fails the floor and 33k misses the bar |
| **k=3 (h95)** | **84.69** | 24.79 | 17.61 | baseline |
| k=4 (h98) | 81.68 | 25.30 | **22.65** | **best candidate**, plus 28.6 percent at 60k |
| k=7 (h99) | 72.88 | **26.54** | not measured | reverted, fresh drops 13.9 percent |

The trend is the finding. **Fresh falls as the chain grows while depth rises at every step out to k=7**, which is what draft-chain starvation predicts and a hard kernel limit does not. At k=4 the gain is entirely at depth, 17.61 to 22.65 on runs of 22.61/22.65/22.65/22.65/22.65, at a cost of 3.55 percent fresh. At k=7 the depth gain holds, plus 7.06 percent at 33k, but fresh falls past the 2 percent floor.

The k=7 arm is also where the sweep stops: a 60k fill under a 7-wide verification did not complete inside the measurement budget, so that arm carries no 60k point and no quality probe. **k=4 is the largest chain that pays and still fits the protocol**, so it is the candidate and k=3 remains the production setting.

## Long-context profile: 76.41 tok/s at a 196k window

turboq qwen35 fork, build `aaa66a5`, uncensored IQ4_XS, SWA hybrid profile (h76).

```
-ngl 99 -c 196608 --parallel 1 -fa on -ub 256 --spec-type draft-mtp
-ctk q4_0 -ctv q4_0
--override-kv qwen35.attention.sliding_window=int:4096,qwen35.attention.swa_global_layers=int:8
```

Resident 19331 MiB. Beats the dense 98k profile at every point and doubles the window.

Recall frontier, exact literal retrieval on a synthetic fill. Pass at 111k and 150k. Fail at 183k, where a literal came back corrupted. The q4_0 cache is the context lever and it is also where the frontier ends.

## Max-speed profile: 84.69 tok/s in a 61k window

HyperQwen `slim-20gb` fork of vLLM 0.28.0, four patches on a 42-patch stack, uncensored `q38-lemin` W4A16.

```
MODEL=q38-lemin SPEC=mtp CTX=long MAX_LEN=61440 GPU_UTIL=0.95
--kv-cache-dtype int4_per_token_head --attention-backend TRITON_ATTN
DRAFT_TOKENS=3
```

This is the best fresh decode this card has produced, plus 10.8 percent over the long-context profile. Quality is clean: recall 4 of 4 at a 60k fill, the fixed prompt byte-identical to the long-context profile's answer, tool-call check pass. It also boots with 1.33 GiB free where the unpatched fork died at the draft marlin repack, which is the whole reason the fork exists. Its usable window is 61440 tokens against 196608.

## Max window without speculation

For when the window matters more than speed and quality can take the hit. Drop speculative decoding and hold the q4_0 cache (h77).

| prompt fill | decode |
|---|---|
| fresh | 39.03 |
| ~91k | 27.83 |
| ~250k | 18.87 |

Window 262144 boots at resident 18615 MiB, the trained limit. Minus 49 percent fresh, and recall fails at 250k with a corrupted literal. Not a default. Kept as the ceiling probe that showed the trained 262k is reachable without MTP.

## Reference: how we got here

| Stack | tok/s fresh | Note |
|---|---|---|
| upstream b10809 + uncensored IQ4_XS + draft-mtp + ub 256 | 72.68 | previous engine (h45) |
| turboq fork + uncensored IQ4_XS + draft-mtp + ub 256 | 74.00 | former daily driver, 98304 window (h59) |
| ik IQ4_KS MTP n4 + MMQ | 70.51 | censored bench best (h29) |
| upstream llama.cpp IQ4_XS | 67.9 | reference harness |
| llama-server + UD-IQ4_XS + draft-mtp + ub 256 | 66.15 | censored pack at production shape (h47) |
| Bonsai PQ2_0 ternary | 64.1 | co-residency, 2 instances, ctx 131072 |
| orcarouter uncensored IQ4_XS, no speculation | 60.2 | uncensored non-MTP baseline |
| llama-bench tg128, no speculation | 37.98 | raw bandwidth row (h48) |

The h47 row is not a clean censorship comparison. That pack is 14.25 GB against 15.57 GB for the uncensored repack, so censorship and quantizer layout are mixed inside the 9 percent gap.

## Repo map

- `docs/HARDWARE.md` — card and host facts, VRAM ceiling, bandwidth (~760 GB/s at 320-bit)
- `docs/MODEL-STATUS.md` — per-model kept stacks, secondaries, blocked paths (vLLM/HyperQwen)
- `docs/BENCHMARKS.md` — protocol, full results tables, unconverted leads
- `docs/card-tuning-playbook.md` — how to tune a new card from scratch, ceiling math first
- `docs/community-intel.md` — field reports, forum findings, and what transferred
- `docs/overnight-rungs.md` — the rung queue, one attempt per rung
- `docs/TROUBLESHOOTING.md` — gotchas: llama.cpp flags, SSH quoting, the vLLM OOM debugging trail
- `decision.tsv` — the experiment ledger, one row per hillclimb attempt (h0-h98)
- `results/` — raw arm outputs, per-arm receipts, burn CSVs, day notes
- `scripts/` — measurement helpers (`measure_gen.py`)

Protocol: median generate tok/s, 600 tokens, temperature 0, real visible text, n=5 plus a discarded warmup for a kept row, n=3 for a probe. A row is rejected on any crash, CPU fallback, missing draft counters, or quality failure. See `docs/BENCHMARKS.md`.
