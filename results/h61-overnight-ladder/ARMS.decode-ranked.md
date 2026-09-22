# h61 arm matrix, decode-ranked, single-stream 98k production shape

Base launcher (h59 winner, turboq qwen35 aaa66a5):
exec /usr/bin/llama-server -m /home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf -ngl 99 -c 98304 --parallel 1 -ctk q8_0 -ctv q8_0 -fa on -ub 256 --spec-type draft-mtp --jinja --port 8083 --host 0.0.0.0

h61 re-baseline. Same launcher. Warmup discarded + 5 timed at fresh, 33k, 91k.
Headline decode medians to beat. Fresh 74.00, 33k 50.42, 91k 40.81.
Prefill recorded only as guard rail. Fit gate + residency before and after.

h62 draft KV q8_0. Add -ctkd q8_0 -ctvd q8_0, all else identical.
Hypothesis. Production runs f16 draft cache today (issue 39). Halving draft bytes
should move single-stream decode at fresh and 33k first, 91k second.
Measure fresh + 33k + 91k, warmup + 5 each, plus prefill guard and quality probe.

h63 draft KV q4_0. Add -ctkd q4_0 -ctvd q4_0 on the h62 winner path only.
Smaller draft cache still. Same three points. Watch prefill for the CPU trap.

h64 draft KV tbq4_0. Add -ctkd tbq4_0 -ctvd tbq4_0 if the parser accepts.
If the server refuses the type at boot, log the verbatim error and mark reverted
without timed arms. Same three points if it boots.

SWA unsettled only. Reuse every value SwaHybridRung settles. Run only what it leaves
unsettled, globals 8 then 4 and 13 at depth, window 2048 and 8192 with globals 8.
Recall test is load-bearing on every SWA arm. Decode ranked at 33k + 91k first.

n-max 4 on the winning draft KV. At 49k and 64k first, then a fit gate at 98k.
SIGSEGV risk at 98k is known (h56b2). Any crash is a reject, never noise.
Draft acceptance recorded per arm.

ngram-mod base. --spec-type draft-mtp,ngram-mod --spec-ngram-mod-n-min 16
--spec-ngram-mod-n-max 64 on the winning draft path. Standard prompts only.
Then match 4, 8, 16. Then n-max 4 on the best match. Decode at fresh + 33k.

ubatch at 98k. ub 64, 128, 384 with b equal to ub, then b 512 variants.
h45 needed ub 256 because ub 512 OOMed the speculative fattn alloc.
Fit gate before every ub arm. Decode at 98k shape, 33k second.

p-min 0.60 control. Single run on the winning draft path only.
Measured minus 10.8 percent before. Expect revert. Prefill guard still recorded.

Main TBQ4 and TBQ3 at 91k only. The depth extreme is the one place their theory
predicts a win. Fresh already lost 12 and 20 percent. Decode at 91k only,
fresh recorded only to confirm the known cost.

FA_ALL_QUANTS rebuild phase, only if the night has room. Rebuild with
GGML_CUDA_FA=ON and GGML_CUDA_FA_ALL_QUANTS=ON as its own sub-phase.
Then q5_1 mixed KV and RotorQuant planar3_0 and iso3_0 first.
Every q5_x or mixed-KV arm needs the PR 27140 prefill measurement,
because decode-only checks cannot see the CPU-prefill trap.

Leaner weight packs with the quality probe, only if decode rungs are exhausted.
Report decode t/s on the 98k single-stream shape. Quality probe mandatory.

Co-residency optional last. Two instances only. Report per-instance decode t/s,
never aggregate. Bandwidth-bound expectation from h33, value is parallel streams.
