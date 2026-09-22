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

## vLLM / HyperQwen (blocked on this card)

- Stock vLLM (PyPI cu132) cannot serve these checkpoints: SergiioB GPTQ weights alone 18.61 GiB > fit; leminkozey W4A16 uses HyperQwen's `weight_packed` format (loader ValueError).
- HyperQwen patched vLLM 0.28.0 bare-metal: 38/38 patches apply, torch 2.13.0+cu130 matches their pin, dummy and real-weight loads pass at GPU_UTIL 0.60. At 0.90 the card fills completely during load (allocator free 33 MiB) and the final MTP-module marlin repack `aten::empty` dies with no OOM text. Quantizing the BF16 MTP module (849→431 MB via their `prepare/quant_mtp.py`) was not enough. Verdict: checkpoint + patched stack needs >19.2 GiB; a 24 GB-class card is assumed. See `docs/TROUBLESHOOTING.md`.
- Their 3090 24 GB reference: 121 t/s MTP; naive 760 GB/s scaling ≈ 98 t/s here. Community reputation caveat: some members flag syv-ai as over-promoted; treat headlines as 24 GB numbers.

## Models on the box (`/home/jamie/models/`)

`Qwen3.8-27B-MTP-IQ4_KS.gguf` (16G), `Qwen3.8-27B-UD-IQ4_XS.gguf` (14G), `Ternary-Bonsai-2-27B-PQ2_0.gguf` (7.2G), `orcarouter-uncensored-IQ4_XS.gguf` (14.5G), `qwen38-gptq-int4/` (19G, unusable — too heavy), `q38-lemin/` (16G W4A16, HyperQwen-format), DFlash2 + Q3 variants.
