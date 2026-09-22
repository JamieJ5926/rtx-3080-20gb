# h61 morning table shell, decode headline

Baseline. Turboq qwen35 aaa66a5, orcarouter IQ4_XS, q8_0 main KV, f16 draft KV,
draft-mtp n-max 3, ub 256, 98304 ctx. Fresh 74.00, 33k 50.42, 91k 40.81.
Bars. Fresh floor 72.52 (within 2 percent). Depth win past noise.
Prefill is guard rail only, never a keep reason.

| rung | config | fresh decode | 33k decode | 91k decode | prefill guard | quality | recall | verdict |
|---|---|---|---|---|---|---|---|---|
| h61 | re-baseline, n=5+warmup | | | | | 4/4 | n/a | |
| h62 | draft KV q8_0 | | | | | 4/4 | n/a | |
| h63 | draft KV q4_0 | | | | | 4/4 | n/a | |
| h64 | draft KV tbq4_0 | | | | | 4/4 | n/a | |
| SWA | unsettled values only | | | | | 4/4 | 4/4 | |
| n4 | n-max 4 on draft winner | | | | | 4/4 | n/a | |
| ngram | n-min 16 n-max 64 | | | | | 4/4 | n/a | |
| match | n-match 4/8/16 | | | | | 4/4 | n/a | |
| ub | ub 64/128/384, b variants | | | | | 4/4 | n/a | |
| pmin | p-min 0.60 control | | | | | 4/4 | n/a | |
| tbq91 | main TBQ4/TBQ3 at 91k only | | | | | 4/4 | n/a | |
| faquant | rebuild + q5_1/RotorQuant | | | | | 4/4 | n/a | |
| lean | leaner packs + probe | | | | | probe | n/a | |
| cores | 2x per-instance decode | | | | | 4/4 | n/a | |

Untested list and top three follow-ons land here at closeout.
Best config ships with its exact launcher line.
