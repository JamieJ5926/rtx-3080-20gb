# h61 overnight ladder, decode-ranked queue

Baseline production (h59 winner). Turboq qwen35 build aaa66a5.
Model orcarouter-uncensored-IQ4_XS.gguf, -ngl 99 -c 98304 --parallel 1.
Main KV -ctk q8_0 -ctv q8_0, draft KV implicit f16, -fa on -ub 256.
Spec --spec-type draft-mtp, n-max 3 default.
Headline medians with old n=3 protocol. Fresh 74.00, 33k 50.42, 91k 40.81.
Launcher on box is /home/jamie/llama/llama-serve.sh via llama-watchdog.service.
This file reflows the rungs doc by expected single-stream decode effect.

Metric. Decode t/s median of 5 after one discarded warmup is the accept and reject metric.
Prefill is guard rail only. It catches the silent CPU prefill trap and never justifies a keep.
Reject on any crash, CPU fallback, missing draft counters, or quality failure.
Never classify a crash as noise.

Bars. Keep when fresh stays within 2 percent of 74.00 (floor 72.52) and a depth point
improves past noise. Or keep when the window grows without an at-depth cost above 10 percent.
Quality guardrail must pass. Every SWA rung needs the beyond-window recall test.

Protocol per point. One warmup discarded, then 5 timed runs, 600 tokens, temp 0,
cache_prompt false, canonical h45 prompt fresh plus fills 16701, 33355, 66685, 91655.
Report median decode and median prefill plus all 5 runs and draft_n and draft_n_accepted.
Fit gate before timed arms. Record VRAM residency before and after. Check /health and ps cmdline.

Order. h61 re-baselines production with the n=5 plus warmup protocol at fresh, 33k, 91k.
Then draft KV q8_0 (h62), draft KV q4_0 (h63), draft KV tbq4_0 if the parser accepts (h64).
Reuse every SWA value SwaHybridRung settles. Run only the SWA values it leaves unsettled,
with recall mandatory. Then n-max 4 on the winning draft KV at 49k and 64k first,
then a fit gate at 98k. Then ngram-mod base n-min 16 n-max 64, then match 4, 8, 16,
then n-max 4 on the best match. Then ubatch at 98k, ub 64, 128, 384 with b equal to ub,
then b 512 variants. Then p-min 0.60 single control on the winning draft path.
Then main TBQ4 and TBQ3 at 91k only. Then, if the night has room, the FA_ALL_QUANTS
rebuild with q5_1 mixed KV and RotorQuant planar3_0 and iso3_0. Then leaner weight packs
with the quality probe. Multi-instance co-residency runs optional last and reports
per-instance decode only, never aggregate.

Do not touch. LLAMA_ATTN_ROT_DISABLE. GGML_CUDA_FORCE_MMQ=1. GGML_CUDA_GRAPH_OPT=1.
p-min as a speed lever. n-max 2. Whole-cache q4_0 as a speed lever.
No sudo. No docker. No VBIOS or power changes.

Restart window. Freeze Mac pid 34846 with kill -STOP. Stop llama-watchdog.service on the box.
Update the launcher. Start the watchdog. Wait for /health ok and verify ps cmdline.
Unfreeze 34846 with kill -CONT. Then fit gate, then warmup plus 5 timed, then residency.

Stop. Queue done or every remaining rung is do-not-touch. Leave production at the best
verified config within the guardrails, or the exact h59 winner if nothing beats it,
verified with an h45-protocol run and the supervisor unfrozen.
