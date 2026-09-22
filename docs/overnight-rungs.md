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
