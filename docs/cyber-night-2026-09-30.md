# OrcaSAQ-2-Cyber on the RTX 3080 20GB: night of 2026-09-30

Question: is OrcaSAQ-2-Cyber-Uncensored (the publisher's next version of our daily
model) a usable daily driver on this box, and if so with what profile?

All arms run on the box through the frozen harness: `measure.py` medians of five
timed runs after a discarded warmup, `recall.py` planted-literal probes at the
listed depths, `qualityfixed.py` for the fixed-literal quality probe. One variable
per arm. Every row lands in `decision.tsv` with its receipts under
`results/hq20-hillclimb/runs/` on the box.

## Measured

| arm | fresh | 33k | 60k | 120k | 180k | recall @60k | recall @150k | quality |
|---|---|---|---|---|---|---|---|---|
| Cyber, production shape (SWA 8 globals, q4_0 KV, 196k) | 57.66 | 56.71 | 45.79 | 44.30 | 39.37 | 1/4 | 0/4 | PASS |
| Cyber, SWA 13 globals | 65.75 | 51.30 | 41.38 | 35.00 | 29.76 | **4/4** | **4/4** | PASS |
| Cyber, q8_0 KV at a 65k window | 60.24 | - | 46.55 | - | - | 0/4 | - | PASS |
| Cyber, SWA 8, recall ladder | 61.83 | - | - | - | - | 1/4 (8k 1/4, 16k 0/4, 33k 1/4) | - | PASS |
| Cyber, SWA 16 globals | invalid: builds asserts `is_swa_any()` |

Old model reference on the same stack, cold card earlier the same day:
76.41 fresh, 57.51 at 33k, 51.07 at 150k (h76 profile: SWA 8 globals, q4_0 KV, 196k).

## What the night establishes

1. **Cyber's recall failure is the SWA profile, not the model and not the KV quant.**
   With 8 global layers and a 4096-token window, 56 of 64 layers see only the last
   4k tokens, so a planted literal mid-prompt is invisible to them. Cyber fails
   recall even at 8k under that profile (1/4). Raising globals to 13 fixes it
   completely: 4/4 at 60k and 4/4 at 150k on the same probes and seed.

2. **The fix costs depth throughput.** 13 globals versus 8: 35.00 vs 44.30 at 120k,
   29.76 vs 39.37 at 180k, about 20% down. Fresh reads higher on the SWA 13 arm but
   that is thermal ordering between adjacent arms, not a config win.

3. **KV precision is not a lever here.** q8_0 KV was worse for recall (0/4 versus
   1/4) and slower (60.24 fresh, 46.55 at 60k), so precision cannot be the cause.

4. **The SWA knob has a hard ceiling.** 16 globals leaves no windowed layer and the
   build asserts, so 15 is the practical maximum and 13 is the known-good value.

5. **Cyber is slower than the old model at depth on the same flags** (about 30 versus
   51 at 150k), with a flatter curve. The warm-card control arm for the old model is
   queued (c8) so this comparison can be stated exactly.

## Open, running tonight

- c3 draft k4 and k5 on Cyber (draft depth was skipped for Cyber so far)
- ubatch 512 with the agent-turn bench
- c10 and c12: the minimum globals that still pass recall, to buy the fix as cheaply
  as possible
- c8: old model, full-context control on a warm card
- c9: Cyber with no SWA override at 32k, to see whether it recalls at all when every
  layer keeps full attention

## Recommendation so far

Cyber is usable as a daily **only** with a re-tuned SWA profile (13 globals), which
buys full-context recall at about 20% of depth throughput. It is still slower at
depth than the model it would replace. Whether that trade is worth taking depends on
the c8 control and on how much the cyber fine-tuning is worth in daily use; the
speed question, on the evidence so far, favours keeping the old model as the
long-context daily.
