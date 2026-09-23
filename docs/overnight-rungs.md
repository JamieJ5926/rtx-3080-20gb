# Overnight rung queue

Assembled 2026-09-23 from the fork knob sweep and the card class playbook. One rung per attempt, keep or revert against the frozen protocol, decision rows appended per attempt. Production at queue time is the turboq qwen35 build aaa66a5 at q8_0 KV with `--spec-type draft-mtp` and n-max 3, 74.00 fresh median and 50.42 at 33k (h59).

Accept a rung when fresh stays within 2 percent and a depth point improves past noise, or when the window grows without an at-depth cost above 10 percent. Run the quality guardrail and, for any SWA rung, the beyond-window recall test before keeping.

## Queue order

1. SWA hybrid sweep. `--override-kv qwen35.attention.sliding_window=int:4096` with `swa_global_layers` at 8, then 4 and 13 at depth, then window at 2048 and 8192 with globals at 8. Recall test is load-bearing. Runs only if SwaHybridRung has not already settled these values.
2. Draft KV types, independent of main KV. `-ctkd` and `-ctvd` at f16, then q8_0, then tbq4_0 if the parser accepts. Depth-first measurement. The memory saving may unlock n-max 4 without the whole-cache cost.
3. n-max 4 on the winning draft KV, at 49k and 64k first, then a fit gate at 98k.
4. ngram-mod stacking. `--spec-type draft-mtp,ngram-mod --spec-ngram-mod-n-min 24` with n-match at 4, 8, 16 and n-max at 3 and 4. Expect gains to depend on repetitive content, so measure on the standard prompts only.
5. Ubatch sweep at 98k. ub at 64, 128 and 384 with b equal to ub and b at 512.
6. Main TBQ4 and TBQ3 KV at 91k fill only. The depth extreme is the one place their theory predicts a win.
7. RotorQuant KV types, planar3_0 and iso3_0 first. Requires a rebuild with `GGML_CUDA_FA=ON` and `GGML_CUDA_FA_ALL_QUANTS=ON`. Budget it as its own sub-phase.
8. p-min 0.60 as a single control run on the winning draft path only.

## Do not touch

`LLAMA_ATTN_ROT_DISABLE`, wrong architecture. `GGML_CUDA_FORCE_MMQ=1` and `GGML_CUDA_GRAPH_OPT=1`, measured noise here. p-min as a speed lever, measured minus 10.8 percent. n-max 2, measured minus 3.1 percent. Whole-cache q4_0 as a speed lever, it is the documented context-maximum option instead.

## Late sweep additions

From the env and field sweep, 2026-09-23. These move to the top of the queue.

1. **Explicit draft KV types.** qwen38-mtp issue 39 records that `-ctkd` and `-ctvd` do not inherit from `-ctk` and `-ctv` and default to f16. Production therefore runs an f16 draft cache today. Sweeping the draft cache to q8_0 and then q4_0 while keeping the main cache at q8_0 is cheap and likely to pay. Source: [issue 39](https://github.com/sudoingX/qwen38-mtp/issues/39).
2. **Small-KV prefill fix.** The same issue documents a silent trap where stock builds run q5_0 and q5_1 flash-attention prefill on CPU, collapsing prefill from 1492 to 41.5 t/s with no error. Upstream [PR 27140](https://github.com/ggml-org/llama.cpp/pull/27140) adds vectorized dequantization that restores it. Any q5_x or mixed-KV rung needs a build containing that fix and a prefill measurement, because decode-only checks cannot see the trap.
3. **ngram-mod parameters.** The community comment on PR 27140 reports about plus 27 percent on code and math with `--spec-type draft-mtp,ngram-mod --spec-ngram-mod-n-min 16 --spec-ngram-mod-n-max 64`. Prefer these parameters to the n-min 24 guess in the original queue.

## Methodology overrides

Five timed samples after a discarded warmup per rung, not three. Issue 39 shows a three-prompt median moving 15 percent where the five-run mean moved 1.6. Measure prefill and decode at every point. Run a fit gate before timed arms and record residency before and after. Reject a row on any crash, CPU fallback, missing draft counters or quality failure. Never classify a crash as noise.

## Second field sweep additions

From two r/LocalLLaMA and r/LocalLLM config threads, 2026-09-23. All untried on this card.

1. **ngram-map-k4v stacking.** `--spec-type draft-mtp,ngram-map-k4v --spec-ngram-map-k4v-size-n 16 --spec-ngram-map-k4v-size-m 24 --spec-ngram-map-k4v-min-hits 1`. A different ngram variant than the ngram-mod we measured as noise. One user reports it as summarization tuned and recommends dropping it for agent use, so measure on both prompt classes.
2. **Mixed KV types.** `-ctk q8_0 -ctv q5_1`. We have only tested symmetric pairs. One config runs this at 119k context.
3. **q4_1 KV at depth.** One user runs 170k with Q4_1 KV on a 24GB card. Untried dtype, sits between q4_0 and q5_1 in the memory tables.
4. **exllamav3 with tabbyAPI.** A whole engine class we have never run. Reported as steadier decode and prompt processing than llama.cpp at agent workloads, with `--draft-cache-mode Q4` for a quantized draft cache, which is exactly what our fork bug blocks, and `sysmem_kv_cache` eviction of old blocks to system RAM for subagent workloads. Rasekov runs 256k with Q8 KV at 4bpw.
5. **NInfer-3090 fork.** Reported 57 t/s at 125k and one user reports poor KV accuracy on a coding agent, so it needs a quality gate before any speed claim.
6. **ik fork Hadamard KV.** `-ctk q4_1 -ctv q4_1 -khad -vhad` on ik_llama.cpp. The Hadamard rotation family behind TBQ in a different fork, unmeasured here.
7. **Agent behavior rungs, a new category.** Two users report Qwen3.8 overthinking and failing tool calls under default harness settings. The froggeric qwen3.8 chat template, `--reasoning-budget`, `--reasoning-preserve` and `chat-template-kwargs reasoning_effort` are all untested behavior levers and matter more than t/s for our agentic use.

## Field-note additions, alexander-ollman qwen3.8-on-rtx3090

From the 2x3090 field writeup, 2026-09-23. Its llama.cpp numbers are below ours, but three findings transfer directly.

1. **fp8 KV is the quality-safe cache.** Their per-token-likelihood instrument finds fp8 indistinguishable from bf16 to 150K with 100 percent retrieval at 147K, and 4-bit cache "costs something real". This matches our recall failure with q4_0 past 150 to 183k. Run SWA8 with q8_0 KV as the quality-first profile and map its ceiling and recall. Expected window around 160k with exact recall, against our 196k with corruption past 150k.
2. **Swift-Qwen3.8-27B swap.** The UkisAI fine-tune halves thinking tokens at equal answers, 37 and 37 on the problems where neither hit the ceiling, and cuts a 36-task coding set from 9.6 to 5.5 hours. For agentic use that is bigger than any t/s lever left. Requires a model download and our quality harness plus the compaction probe.
3. **DFlash2 on the turboq fork.** We burned DFlash2 on the old upstream stack at 46.5 t/s. The fork carries dflash CUDA kernels and the writeup's 212 t/s row is DFlash2 at k=7. Single-consumer case is where DFlash2 wins per their concurrency caveat. Untested combination here.
4. Their community patched vLLM reached 167.8 before DFlash2, from a smarter verify kernel, a 4-bit output head and a trimmed draft vocabulary, and it refuses checkpoints that do not match its assumptions. Same family as the HyperQwen patches we could not fit at 20GB. Record only.

## Third field sweep additions, EXL3 and the trellis quant class

From the Yume_X EXL3 tier map, 2026-09-23, cross-checked against the exllamav3 reports from the earlier config threads. This is a different engine and quant class, not a GGUF variant, so it is a look-first item rather than a flag rung.

1. **What it is.** EXL3 uses trellis coding with a Hadamard transform so rounding error spreads across each weight vector instead of stacking per weight. The independent teacher-logit panel puts EXL3 4bpw 0.004 nats from BF16 against FP8 at 0.002 and NVFP4 at 0.06. Near-FP8 quality at roughly half the file size is the claim worth testing.
2. **The rows bracketing our 20GB card.** The 16GB tier runs Qwen3.8-27B at 3.0 bpw with the built-in MTP head at about 55 tok/s code decode with 110k context on a 16GB A5000. The 24GB tier runs 3.5 bpw plus a DFlash2 5.0 bpw drafter at 94 to 150 tok/s with the full 262k resident on a 22GB budget. Our card sits between those tiers.
3. **The drafter insight transfers directly.** Their quantized drafter cut draft weight reads from 16 bit to 5 and added 33 percent end to end. This is the same lesson as our own draft-KV work but applied to drafter weights, and it is a different lever.
4. **Engine notes from the field.** The exllamav3 and tabbyAPI reports describe steadier decode at depth and steadier prompt processing than llama.cpp under harness load, with sysmem_kv_cache eviction of old blocks to system RAM for subagent workloads. That eviction class is the adaptive streaming idea from the first sweep.
5. **Do not confuse with TurboQuant.** The TBQ KV family we measured is a cache compression. EXL3 is a weight compression. They compose rather than compete.

Run order for a future card session. Check the turboderp/Qwen3.8-27B-exl3 branches for a 3.0 and 3.5 bpw pack with the MTP head, stand up tabbyAPI per the earlier exllamav3 rung, and measure the frozen protocol plus the recall frontier against whatever the GGUF stack is producing that day.
