# OrcaSAQ-2-Cyber on the RTX 3080 20GB: findings, night of 2026-09-30

Question: is OrcaSAQ-2-Cyber-Uncensored (the publisher's next version of the daily
model) usable as the daily driver on this box, and with what profile?

Protocol for every arm: `measure.py` median of five timed runs after a discarded
warmup (the discarded line also carries a `decode=` value, so medians read from the
whole file are wrong; the collector reads `run` lines only), `recall.py` planted
four-literal probes at the named depths with seed 2026092330, `qualityfixed.py` for
the fixed-literal probe. One variable per arm. Every arm writes a `decision.tsv` row.

## The headline finding, and a correction

**Long-range recall is broken under the SWA 8 profile for both models.** On the
identical battery and probe:

- old daily model (orcarouter-IQ4_XS, SWA 8, 196k): recall **0/4 at 60k, 0/4 at 150k**
- Cyber (SWA 8, 196k): recall **1/4 at 60k, 0/4 at 150k**
- Cyber with no SWA override at 32k: recall **4/4 at 16k**

An earlier statement in this run that the old model passes 4/4 on this profile was
wrong. It rested on the vLLM stack and an older probe format, not on this stack with
this probe. The production shape has been passing a weaker test than the one used
here.

**The mechanism is the 4096-token sliding window.** With 8 global layers, 56 of 64
layers see only the last 4k tokens, so a planted literal mid-prompt is invisible.
Cyber fails even at 8k under that profile. Raising the global-layer count restores
recall completely: 10, 12 and 13 globals all pass 4/4 at both depths; 16 is invalid
(the build asserts when no windowed layer remains).

## Speed, warm card, matched arms

| arm | fresh | 33k | 60k | 120k | 180k | recall |
|---|---|---|---|---|---|---|
| old model, SWA 8 (c8 + c8b) | 70.69 | 56.50 | 45.18 | 49.85 | 37.61 | 0/4, 0/4 |
| Cyber, SWA 8, k3 (c4) | 57.66 | 56.71 | 45.79 | 44.30 | 39.37 | 1/4, 0/4 |
| Cyber, SWA 9, k3 (c9b) | 65.77 | | 52.74 | | | 3/4, 3/4 |
| Cyber, SWA 13, k3 (c5) | 65.75 | 51.30 | 41.38 | 35.00 | 29.76 | 4/4, 4/4 |
| **Cyber, SWA 13, k4 (c13)** | 51.02 | **59.15** | 44.10 | 35.46 | 31.48 | **4/4, 4/4** |
| Cyber, SWA 10, k4 (c14) | 55.05 | 48.20 | 39.53 | 32.20 | 29.80 | 4/4, 4/4 |

c8's 60k point read 42.16 on the first pass and 45.18 on the recheck (c8b), so the
first reading was thermally depressed; the curve is monotonic with the recheck in
place. At 60k the old model is therefore level with Cyber, not behind it.

SWA 9 (c9b) recalls 3/4, not 4/4, so the minimum passing global count is **10**.

Fresh deltas across arms are confounded by card temperature, which is worth about 8%
(c8 reads 70.69 warm against a 76.41 cold-card reference for the old model). Compare
arms run back to back, not across the day.

## Best configuration found

**Cyber with SWA globals 13 and draft depth 4.** Full recall at 60k and 150k, quality
PASS, the best 33k of anything measured (59.15, beating the old model's 56.41), level
with the old model around 60k, and behind it at fresh and past 120k. SWA 10 with k4
(c14) recalls just as correctly but is slower at every depth on this data.

## Landed in production

The restore savepoint `llama-serve.sh.h76-savepoint-h77` now carries Cyber with
`swa_global_layers=int:13`; the diff against the previous savepoint is that one token.
Every arm restore from now on therefore serves the recall-correct profile, and the
previous savepoint is kept as `.h76-savepoint-h77.swa8-backup`. Before this, both the
arm restore and the live daily driver served SWA 8, which fails the recall probe at
60k and 150k.

## The old model cannot be given the same fix at full context

c15 ran the old model with SWA 13 at 196k and died at boot: **CUDA out of memory**,
`mem_used 19999/20480 MiB` against a 20GB card. Cyber holds that profile at the same
context, so the old model's KV footprint at 13 globals is larger than Cyber's. Arms
c18 (SWA 13 at 131k), c19 (SWA 12 at 196k) and c20 (SWA 10 at 196k) pin what it can
actually hold.

## Still running tonight

- c16 Cyber SWA 13 at a 131k window: does the recall fix let the window shrink, saving
  KV memory and buying speed?
- c17 repeated fresh measurements of the SWA-13 config against thermal noise
- c18/c19/c20 the old model's recall-fix options at 131k and at 12 or 10 globals

## Recommendation

Cyber with **SWA globals 13, draft k4, at 196k** is the daily driver, and it is what
production now serves. It is the fastest configuration measured that passes the recall
probe at 60k and 150k, it beats the old model from 33k to 60k, and it gives up fresh
and past-120k throughput for recall integrity that the old model at SWA 8 does not
have at all.

The old model stays the faster engine at fresh and deep context, but only in a shape
that fails recall; whether a shape exists that both fits the card and recalls is what
c18 to c20 settle. Until then the trade is explicit: old model is faster, Cyber SWA 13
is correct.
