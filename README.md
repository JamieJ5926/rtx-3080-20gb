# RTX 3080 20 GB

Serving benchmarks for a modded GeForce RTX 3080 (20480 MiB, GA102) on CUDA Linux. Not a distro project. Weights are not in this repo.

## Current best: 70.51 tok/s

ik_llama.cpp + `ubergarm/Qwen3.8-27B-MTP-IQ4_KS.gguf` + MTP n-max 4 + `GGML_CUDA_FORCE_MMQ=1` — 70.51 median generate tok/s (600 tokens, temp 0, n=3), up from the 41.05 Ollama baseline.

| Model | tok/s | Role |
|---|---|---|
| ik IQ4_KS MTP n4 + MMQ | **70.51** | daily driver |
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
