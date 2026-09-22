# RTX 3080 20 GB

Serving benchmarks for a modded GeForce RTX 3080 (20480 MiB, GA102) on CUDA Linux. Not a distro project. Weights are not in this repo.

## Current best: 76.41 tok/s at a 196k window

The turboq qwen35 fork (build `aaa66a5`) with the SWA hybrid profile. `--override-kv qwen35.attention.sliding_window=int:4096,qwen35.attention.swa_global_layers=int:8` + `-ctk q4_0 -ctv q4_0` + `--spec-type draft-mtp` at `-c 196608`. Measured 76.41 median fresh (h76), 57.51 at 33k, 54.40 at 91k, 55.54 at 111k, 51.07 at 150k. Exact recall verified at 111k and 150k and degraded at 183k. This beats the dense 98k profile at every point and doubles the window.

| Model | tok/s | Role |
|---|---|---|
| turboq fork SWA8 + q4_0 KV + draft-mtp | **76.41** | daily driver, 196608 window (h76) |
| turboq fork + uncensored IQ4_XS + draft-mtp + ub 256 | **74.00** | daily driver, 98304 ctx (h59) |
| upstream b10809 + uncensored IQ4_XS + draft-mtp + ub 256 | 72.68 | previous engine (h45) |
| llama-server base UD-IQ4_XS + draft-mtp + ub 256 | 66.15 | base model, production shape (h47) |
| ik IQ4_KS MTP n4 + MMQ | 70.51 | censored bench best (h29) |
| Bonsai PQ2_0 ternary | 64.1 | co-residency (2× instance), ctx 131072 |
| orcarouter uncensored IQ4_XS | 60.2 | uncensored option, quality stock-equal |
| upstream llama.cpp IQ4_XS | 67.9 | reference harness |

## Repo map

- `docs/HARDWARE.md` — card and host facts, VRAM ceiling, bandwidth (~760 GB/s at 320-bit)
- `docs/MODEL-STATUS.md` — per-model kept stacks, secondaries, blocked paths (vLLM/HyperQwen)
- `docs/BENCHMARKS.md` — protocol, full results tables, unconverted leads
- `docs/TROUBLESHOOTING.md` — gotchas: llama.cpp flags, SSH quoting, the vLLM OOM debugging trail
- `decision.tsv` — the experiment ledger, one row per hillclimb attempt (h0-h38)
- `results/` — raw arm outputs, burn CSVs, day notes
- `scripts/` — measurement helpers (`measure_gen.py`)

Protocol: median generate tok/s, 600 tokens, temperature 0, real visible text, n=3. See `docs/BENCHMARKS.md`.
