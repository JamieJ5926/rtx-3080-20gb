# Benchmark protocol and results

## Protocol

- Median generate tok/s, 600 tokens, temperature 0, real visible text, n=3 arms unless noted
- Canonical prompt: `Write a careful technical explanation of PCIe Gen3 x16. Use complete sentences.`
- llama.cpp harness frozen at upstream `b10809` (5266f24da7) for llama-cli arms; all h3+ numbers on this build
- Think-on is not answer speed: 600 thinking tokens with empty visible response are discarded arms
- Ledger: `decision.tsv`, one row per attempt (h0-h38); raw arm outputs in `results/`
- Grep anchor: `Generation: [0-9.]+ t/s` (model output contains "t/s" — never grep bare)

## Day 1 (2026-09-18 early)

| Setup | Generate tok/s | n | Verdict |
|---|---|---|---|
| Ollama think-on | 49.3 | 3 | discarded (empty answer) |
| Ollama think-off | 41.05 | 3 | first product baseline |
| llama.cpp CUDA no-draft | 34.2 | 3 | reverted |
| llama.cpp draft-mtp, Ollama 16 GB blob | 50.95 | 6 | first real-text CUDA win |
| llama.cpp draft-mtp, Unsloth UD-Q3_K_XL 13.15 GB | 60.7 | 3 | lost to IQ4_XS |
| llama.cpp draft-mtp, Unsloth UD-IQ4_XS 14.25 GB | **67.9** | 3 | day-1 best |

Reverted day 1: IQ3_S 54.7, Q4_K_S 49.7, n-max 8/4, q8/q4 KV, ub 2048, ngram 35.2, fa-off 54.5, extra MTP `-md` 66.7, llama-server 67.8. `draft-simple -md` segfaulted. Power already 320 W max; clock lock needs root; 8k ctx OOM (13 GB extra).

## Day 2 (h20-h31)

Same-day upstream control 67.2 (67.1/67.2/67.3), within 1% of 67.9.

| Setup | Generate tok/s | n | Verdict |
|---|---|---|---|
| upstream n-max 4 + p-min 0.65 | 58.0 | 3 | reverted |
| upstream n-max 6 + p-min 0.75 | 49.8 | 3 | reverted |
| upstream DFlash2 n-max 7 | 46.5 | 3 | reverted |
| ik IQ4_KS MTP n-max 2 | 66.16 | 3 | reverted |
| ik IQ4_KS MTP n-max 4 | 69.34 | 3+1 | kept |
| ik n-max 5 / n-max 6 | 62.96 / 59.70 | 3 | reverted, n-max 4 optimum |
| Bonsai PQ2_0 (no MTP) | 64.1 | 3 | kept-secondary (co-residency, 131k ctx) |
| **ik + GGML_CUDA_FORCE_MMQ=1** | **70.51** (70.28/70.51/70.57) | 3 | **kept, current best** |
| orcarouter uncensored IQ4_XS, draft-mtp | 60.2 | 3 | kept-option (-11.4% vs censored) |
| orcarouter uncensored, n-max 2 | 57.3 | 3 | n-max 3 beats it here |

Context (h30, n=1 scoping): ik q8_0 KV ctx 40960 at 27.8k fill — prefill 988.6, decode 80.4; Bonsai prefill 1045.7, decode 53.9. ik OOMs at 98304.

Raw files: `results/*.txt`, `results/qwen38-27b-gen.json`, `results/burn{10,30}.csv`, `results/2026-09-18.md`.

## Unconverted leads

- HyperQwen stack speed on a bandwidth-matched card (see `docs/MODEL-STATUS.md` — blocked on VRAM)
- Memory OC needs root (h25: sudo/docker both refused on this box)
- ik context ceiling bisect between 40960 and 98304
- Bonsai 2-instance parallel-agent aggregate benchmark
