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
| old model, SWA 8 (c8) | 70.54 | 56.41 | 42.16* | 48.69 | 37.49 | 0/4, 0/4 |
| Cyber, SWA 8, k3 (c4) | 57.66 | 56.71 | 45.79 | 44.30 | 39.37 | 1/4, 0/4 |
| Cyber, SWA 13, k3 (c5) | 65.75 | 51.30 | 41.38 | 35.00 | 29.76 | 4/4, 4/4 |
| **Cyber, SWA 13, k4 (c13)** | 51.02 | **59.15** | 44.10 | 35.46 | 31.48 | **4/4, 4/4** |
| Cyber, SWA 10, k4 (c14) | running | | | | | |

\* c8's 60k point sits below its own 120k reading, so it is thermally depressed and a
recheck is queued (c8b).

Fresh deltas across arms are confounded by card temperature, which is worth about 8%
(c8 reads 70.54 warm against a 76.41 cold-card reference for the old model). Compare
arms run back to back, not across the day.

## Best configuration found

**Cyber with SWA globals 13 and draft depth 4.** Full recall at 60k and 150k, quality
PASS, the best 33k of anything measured (59.15, beating the old model's 56.41), level
with the old model around 60k, and behind it at fresh and past 120k.

## Still running tonight

- c14 Cyber SWA 10 plus k4, the cheapest strong combination
- c15 old model with SWA 13, to test whether the recall fix helps it too
- c9b Cyber SWA 9, to pin the exact minimum globals
- c8b old model 60k recheck, for the thermally depressed point

## Recommendation so far

Cyber is usable as a daily **only** with a re-tuned SWA profile (10 to 13 globals).
With it, Cyber is the better engine from 33k to about 60k and the worse one at fresh
and beyond 120k. Two separate questions stay open: whether the old model is also
fixed by more globals (c15), and whether the production SWA 8 shape should have been
failed on recall long before now, given today's probe says it never passed.
