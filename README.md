# RTX 3080 20 GB

Measurement log for a modded GeForce RTX 3080 with 20 GB VRAM on CUDA Linux. Not a distro project. Weights are not in this repo.

Mac hillclimb (Metal, different quant): [qwen3.8-27b-uncensored-dflash2-m4-pro](https://github.com/JamieJ5926/qwen3.8-27b-uncensored-dflash2-m4-pro). Vault: `Obsidean/local-model-stack-vault/06 Reference/Performance Log.md`.

## Hardware

- GPU: NVIDIA GeForce RTX 3080 (GA102), `42:00.0`
- VRAM: **20480 MiB** (mod, not 10 GB)
- Host: AMD X399 / Ryzen Threadripper 1920X
- PCIe: x16, host max gen 3. Idle gen 1. Under load gen 3 x16
- Driver: `nvidia-open-dkms` 610.57.04, CUDA 13.3 (`nvcc` V13.3.73)

## 2026-09-18

### Detect and CUDA

`memory.total` = 20480 MiB. Idle ~38 C, ~25 W / 320 W, P8. 0 Xid, 0 AER.

`probes/compute.cu` SAXPY n=2^24, 0 mismatches. Load: gen 3 x16, P2, 64 W, 42 C.

### VRAM walk

| Alloc | During-run used | Verify | Notes |
|---|---|---|---|
| 12 GiB | 12874 / 20480 | 0 | 43 C, 96 W, gen 3 x16 |
| 18 GiB | 19018 / 20480 | 0 | 45 C, 96 W |
| 19 GiB | OOM | | display ~360 MiB |
| 18.5 GiB | **19530 / 20480** | 0 | 20 s hold, 0 Xid |

20 GB is addressable. 18.5 GiB is the ceiling with a desktop up.

### Sustained burn (`probes/burn.cu`)

| Run | Util | Temp | Power | SM clock | PCIe | Xid |
|---|---|---|---|---|---|---|
| 10 min | 99% | 61→79→76 C | 255–272 W | 1680–1815 | gen 3 x16 | 0 |
| 30 min | 99% | 74–78 C | 258–271 W | 1680–1785 | gen 3 x16 | 0 |

CSV: `results/burn10.csv`, `results/burn30.csv`.

### LLM

Ollama CUDA 0.33.3 was the first runtime. It is not the hillclimb runtime.

**qwen2.5:32b** (256 tokens): 18753 MiB, 102 prompt tok/s, **7.68 gen tok/s**. `results/ollama-gen.json`.

**qwen3.8:27b** official tag, 17 GB disk, 600 tokens, temperature 0.

The 58.1 tok/s Ollama figure was think-on. All 600 tokens were internal thinking. `resp_len=0`. Do not use it as answer-generation speed.

| Setup | Generate tok/s | n | Notes |
|---|---|---|---|
| Ollama think-on | 49.3 median | 3 | empty visible answer |
| Ollama think-off | **41.05 median** | 3 | usable text. Product baseline |
| llama.cpp CUDA no-draft | 34.2 median | 3 | reverted as speed |
| llama.cpp `--spec-type draft-mtp` ollama 16 GB blob | 50.95 median | 6 | first real-text CUDA decode win |
| llama.cpp `--spec-type draft-mtp` Unsloth UD-Q3_K_XL 13.15 GB | 60.7 median | 3 | kept vs 16 GB blob. Lost to IQ4_XS |
| llama.cpp `--spec-type draft-mtp` Unsloth UD-IQ4_XS 14.25 GB | **67.9 median** | 3 | kept. +12% vs Q3. +98% vs no-draft 34.2. Stop 51.3 met |

VRAM at MTP2 load is about 18 GB of 20 on the 16 GB blob. IQ4_XS is 14.25 GB on disk.

Raw: `results/qwen38-27b-gen.json`, `results/mtp2-n6.txt`, `results/q3-mtp2-n3.txt`, `results/iq4-mtp2-n3.txt`.

Mac vault Unleashed Q3_K_XL llama.cpp was 8.3–10.4 tok/s. Different quant and stack.

## Hillclimb on NVIDIA

DFlash and MLX are Apple-only. Do not use them on this card. The Mac DFlash2 A/B (5.65 vs 5.96 tok/s, rejected) does not transfer.

Order:

1. **Think off.** First paired number on the same Ollama blob.
2. **llama.cpp CUDA.** Server `prompt eval` / `eval` lines, empty ctx, 400–600 tokens, flash attention. This matches the vault protocol.
3. **MTP draft on stock llama.cpp CUDA.** Official Qwen3.8 ships MTP weights. That is the CUDA analogue of DFlash. Same reject rule as Mac: net tok/s must beat no-draft.
4. **Quant A/B.** Official UD-IQ4_XS vs UD-Q3_K_XL vs this 17 GB blob. Keep ctx short.
5. Leave power limits and clocks alone until those four have rows in `results/`.

No vLLM or TensorRT until 1–4 exist.

After MTP2 has a median of 3, not before:

6. Long-context prompt processing tok/s.
7. Sustained decode after KV has grown (vault Metal already fell to 3.57 tok/s at 8K fill).
8. Batch and concurrent agents.
9. A runtime faster than Ollama if llama.cpp stays behind (vLLM or SGLang only then).
