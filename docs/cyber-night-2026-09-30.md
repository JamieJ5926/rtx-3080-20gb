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

## The old model IS recall-fixable at full context

c15 ran the old model with SWA 13 at 196k and died at boot: **CUDA out of memory**,
`mem_used 19999/20480 MiB`. That limit turned out to belong to the 13-global rung at
196k, not to the fix. The arms that followed:

| arm | config | fresh | 60k | recall (60k) |
|---|---|---|---|---|
| c18 | old model, SWA 13, 131k | 72.32 | 46.18 | 4/4 |
| **c19** | **old model, SWA 12, 196k** | 70.98 | **52.07** | **4/4** |
| c20 | old model, SWA 10, 196k | 71.22 | 46.39 | 4/4 |

So the old model serves at 196k with 10 or 12 globals and recalls 4/4 in both. c19 is
the fastest 60k measured by any arm tonight, 18% above Cyber SWA 13 with k4, and it
recalls where the old model's own SWA-8 shape recalled 0/4 at 45.18. The earlier
statement that the old model cannot be recall-fixed at full context was too strong and
is corrected here: only the 13-global rung at 196k is beyond this card.

## Still running tonight

- c16 Cyber SWA 13 at a 131k window: does the recall fix let the window shrink, saving
  KV memory and buying speed?
- c17 repeated fresh measurements of the SWA-13 config against thermal noise
- c18/c19/c20 the old model's recall-fix options at 131k and at 12 or 10 globals

## Recommendation

**The old model at SWA globals 12, 196k.** c22 confirmed the full ladder:

| arm | fresh | 33k | 60k | 120k | 180k | recall |
|---|---|---|---|---|---|---|
| **old model, SWA 12, 196k (c22)** | **71.44** | 58.65 | **52.32** | 35.36 | 31.46 | **4/4, 4/4** |
| Cyber, SWA 13, k4, 196k (c13) | 51.02 | 59.15 | 44.10 | 35.46 | 31.48 | 4/4, 4/4 |

Once both are recall-fixed the old model is the better engine: +40% fresh, +18.6% at
60k, and level at 33k, 120k and 180k, with full recall at 60k and 150k and quality
PASS.

That result does not support the Cyber adoption on throughput grounds. Cyber's case
was that it was the publisher's newer model; against the same recall fix it is slower
at every depth except a 0.5 tok/s tie at 33k. The honest reading is that Cyber was
never faster — it was measured while the old model was still running the broken SWA-8
shape, which made the old model look like a recall casualty rather than the faster
engine.

What changed: the recall failure was never a property of either model. Both are
fixable by giving the attention stack enough global layers; the question each model
has is only how many it can afford at the context it must hold. Cyber affords 13 at
196k, the old model affords 12, and 12 is both sufficient and faster.

## State at the pause

Jamie paused the llama server at about 03:52 on 2026-10-01. The queue runner, the
arm in flight (c23) and the server were stopped, the watchdog was stopped and masked,
and the card is free (309 MiB, 0% utilisation, port 8083 closed). Queue env files and
receipts are untouched, so any arm can be re-run with one `queue-runner.sh` call.

Production's restore savepoint serves Cyber with SWA 13 — recall-correct, and still
the right thing to serve if Cyber remains the chosen daily. Serving the old model at
SWA 12 instead is a one-line savepoint swap, and on tonight's numbers it is the faster
of the two.
