# Model status

Single box, one RTX 3080 20 GB. Metric: median generate tok/s, 600 tokens, temperature 0, real visible text, n=3. Full experiment ledger: `decision.tsv` (h0-h38).

## Qwen3.8-27B (censored)

| Stack | tok/s | Notes |
|---|---|---|
| **turboq qwen35 fork `aaa66a5` SWA hybrid + q4_0 KV + draft-mtp at `-c 196608`** | **76.41** | current best (h76, 2026-09-23), the production config. Curve 76.41 fresh, 57.51 at 33k, 54.40 at 91k, 51.07 at 150k fill. Exact recall PASS at 111k and 150k, FAIL at 183k with literal corruption. SWA window 4096, 8 global layers. Resident 19331 MiB |
| turboq qwen35 fork `aaa66a5` + orcarouter uncensored IQ4_XS + draft-mtp + `-ub 256` at `-c 98304`, dense q8_0 KV | 74.00 | prior profile (h59, 2026-09-23). Curve 74.00 fresh, 50.42 at 33k, 40.81 at 91k. Superseded by the SWA profile at h76 |
| upstream llama-server b10809 + orcarouter uncensored IQ4_XS + draft-mtp + `-ub 256` at `-c 98304` | 72.68 | prior engine (h45, 2026-09-22). draft 404/580 accepted; default `-ub 512` crashes CUDA OOM in the speculative fattn alloc at this context |
| llama-server Qwen3.8-27B-UD-IQ4_XS (base Unsloth) + draft-mtp + `-ub 256` at `-c 98304` | 66.15 | h47, 2026-09-22. draft 400/597; base loses to the uncensored repack at production shape (-9%), inverting the h31 bench-ctx ordering |
| llama-server Qwen3.8-27B-MTP-IQ4_KS (base ubergarm) | n/a | h46, 2026-09-22. Upstream llama.cpp refuses the pack, `blk.0.attn_qkv.weight` ggml type 144 is ik_llama.cpp-only, so the h42 71.63 figure needs the ik engine |
| ik_llama.cpp IQ4_KS + MTP n-max 4 + GGML_CUDA_FORCE_MMQ=1 + K q8_0 | 71.63 | prior best (h42, 2026-09-20), bench ctx 4096. `ubergarm/Qwen3.8-27B-MTP-IQ4_KS.gguf` 15.75 GiB (PPL 6.9938 vs BF16 6.9540), `-ngl 99 -c 4096 -fa on -ctk q8_0 --spec-type mtp:n_max=4,p_min=0.0` |
| ik_llama.cpp IQ4_KS + MTP n-max 4 + GGML_CUDA_FORCE_MMQ=1 | 70.51 | prior best, superseded by K-only KV quant |
| ik_llama.cpp IQ4_KS + MTP n-max 4 | 69.34 | kept before MMQ arm |
| upstream llama.cpp UD-IQ4_XS + draft-mtp (harness b10809) | 67.9 | day-1 best; same-day control 67.2 |
| Ollama think-on | 49.3 | 600 tokens all into thinking, empty visible answer |

- n-max 5 (62.96) and 6 (59.70) reverted; n-max 4 confirmed optimum.
- q8_0 KV unlocks ctx 40960 on the ik stack (upstream f16 OOMed at 8k). At 27.8k fill: prefill 988.6, decode 80.4. Ceiling (h32, q8 K+V): clean through 61440, OOM at 63488 — MTP per-step checkpoint buffers, not KV, bind the growth (h42b). Speed config (q8 K, f16 V, h44) ceiling is lower: 40960 works (64.72 t/s decode), 49152 OOM — f16 V costs ~3 GiB at 41k ctx.
- Day-3 arms all reverted (h39-h41): UD-IQ4_XS on ik 64.27 (-8.8%), p_min 0.1 68.23 (-3.2%), full q8_0 KV 68.98 (-2.2%).

## Ternary-Bonsai-2-27B PQ2_0 (secondary)

64.1 median (-7.6% vs best), 7.2 GiB at 2.13 bpw, PrismML llama.cpp fork, needs `--single-turn`. No MTP head in the pack. Value: two-instance co-residency for parallel streams and ctx 131072 (59.3 t/s light fill) — the 120k-context option. Quality: PrismML's own 14-benchmark table (98.2% of FP16 avg), not independently verified.
Two instances co-resident (16.5 GiB) serve two parallel streams at ~30.4 t/s each = 60.7 aggregate — bandwidth-bound, no throughput multiplier (h33), but latency for two independent agents at once is real.

## Qwen3.8-27B uncensored (orcarouter abliterated, bartowski IQ4_XS)

60.2 median with draft-mtp default (60.0/60.2/60.4); 57.3 at forced n-max 2. **-11.4% vs censored same-class** (FP8-lineage abliteration + requant cost). Quality within ~1 point of stock per the independent Abliterlitics panel (MMLU-Pro -0.04, GSM8K -0.46, HumanEval -0.6, HarmBench ASR 82.2% rank 1/13). Runs on disk at `/home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf`. Production server at 98304 ctx runs the turboq fork at 74.00 median (h59, 2026-09-23). Upstream b10809 measured 72.68 (h45). Default `-ub 512` OOMs the card at this context.

## vLLM / HyperQwen (unblocked, this card runs it at 61440)

**Solved.** The stock stack was never the problem; the fork needed four patches to fit a 20 GB card. Half of this section used to read "a 24 GB-class card is assumed", and that is now false. See `docs/TROUBLESHOOTING.md` for the original OOM trail.

- Stock vLLM (PyPI cu132) still cannot serve these checkpoints: SergiioB GPTQ weights alone 18.61 GiB > fit; the leminkozey W4A16 pack uses HyperQwen's `weight_packed` format and dies in the loader with a ValueError.
- **Our four patches are published** at `github.com/JamieJ5926/HyperQwen-slim-20gb`, branch `slim-20gb`, a public Apache-2.0 fork of `syv-ai/HyperQwen`. They fix the duplicate target read, size the int4 scratch to the draft head instead of the target head, correct the draft attention scratch geometry, and guard the own-head path.
- **The series is 43 entries**, 39 upstream plus our four, pinned to `cpuchip/vllm` branch `qwen38/0.28` where each entry is one commit in series order with the base at `2cf0a6915`. `patches/` holds exactly those 43 files, no drift either direction. Apply order in `patches/series` is a hard requirement and both `verify.sh` and `patches/check_vllm_series.sh` fail on any disagreement.
- **Fit ladder on this card:** 6144 and 24576 fit at fp8; **61440 fits with `int4_per_token_head` and a 75,093-token pool**, which is the winning shape; 93184 does not fit.
- **The winning shape**, `MAX_LEN=61440 GPU_UTIL=0.95 --kv-cache-dtype int4_per_token_head --attention-backend TRITON_ATTN`, measures **84.69 tok/s fresh**. That is the highest fresh decode this card has produced, plus 10.8 percent over the llama.cpp SWA profile, at the cost of a 61440 window instead of 196608 and a depth collapse: 24.79 at 33k and 17.61 at 60k against llama.cpp's 57.51 at 33k.
- **What the fork buys:** it is the short-context speed machine, not the daily driver. It also proves the fit, which is the part worth publishing.
- **MTP precision is a live lever, unmeasured.** The vLLM checkpoint's MTP module is BF16, 810 MiB across 15 tensors at 849,398,784 bytes, while the production GGUF stores its whole MTP block at Q4_0. The fork therefore rereads roughly 3.5x the draft bytes per draft forward. `prepare/quant_mtp.py` already exists and its docstring records that int8 halves that traffic with acceptance unchanged. It was run once during the VRAM ladder for fitting (849 to 431 MB), did not make the stack fit, and was reverted to BF16, so **it has never been benchmarked for speed**.
- **Checkpoint provenance.** The uncensored pack on disk, `q38-lemin`, is a third-party AutoRound W4A16 of `JonathanColetti/Qwen3.8-27B-Uncensored`, made by following syv-ai's recipe: body group-128 W4A16, lm_head and embeddings INT8, and vision, MTP and all `in_proj_a`/`in_proj_b` kept in floating point. Its own card records 98-110 tok/s on a single RTX 3090 with the DFlash2 path.
- Their 3090 24 GB reference: 121 t/s MTP; naive 760 GB/s scaling ≈ 98 t/s here, so production sits at 86.4 percent of that estimate with 13.31 t/s of headroom. Community reputation caveat: some members flag syv-ai as over-promoted; treat headlines as 24 GB numbers.

## Models on the box (`/home/jamie/models/`)

`Qwen3.8-27B-MTP-IQ4_KS.gguf` (16G), `Qwen3.8-27B-UD-IQ4_XS.gguf` (14G), `Ternary-Bonsai-2-27B-PQ2_0.gguf` (7.2G), `orcarouter-uncensored-IQ4_XS.gguf` (14.5G), `qwen38-gptq-int4/` (19G, unusable — too heavy), `q38-lemin/` (16G W4A16, HyperQwen-format), DFlash2 + Q3 variants.
