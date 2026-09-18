# RTX 3080 20 GB on Omarchy

Hardware verification for a modded GeForce RTX 3080 with 20 GB VRAM, installed as the display GPU on Omarchy 4.0.4 (`home-pc`).

This is a measurement record. It does not redistribute weights.

Sibling Mac hillclimb (different runtime and quant): [qwen3.8-27b-uncensored-dflash2-m4-pro](https://github.com/JamieJ5926/qwen3.8-27b-uncensored-dflash2-m4-pro). Vault numbers for Qwen3.8-27B Unleashed on this Mac live in `Obsidean/local-model-stack-vault/06 Reference/Performance Log.md`.

## Hardware

- GPU: NVIDIA GeForce RTX 3080 (GA102), `42:00.0`
- VRAM: **20480 MiB** (mod, not 10 GB)
- Host: AMD X399 / Ryzen Threadripper 1920X
- PCIe: x16, host max gen 3. Idle gen 1. Under load gen 3 x16 (~126 Gb/s)
- Display: Dell U2421HE on `DP-2` (Hyprland)
- OS: Omarchy 4.0.4, kernel `7.2.5-3-omarchy`
- Driver: `nvidia-open-dkms` 610.57.04, CUDA 13.3 (`nvcc` V13.3.73)

## 2026-09-18 results

### Detect

`memory.total` = 20480 MiB. Idle ~38 C, ~25 W / 320 W cap, P8. 0 NVRM Xid, 0 PCIe AER.

### CUDA compute

`probes/compute.cu` SAXPY, n=2^24, **0 mismatches**. Under that load: gen 3 x16, P2, 64 W, 42 C.

### VRAM walk (write, verify, hold)

| Alloc | During-run used | Verify | Notes |
|---|---|---|---|
| 4 GiB | (freed before sample) | 0 mismatches | |
| 12 GiB | 12874 / 20480 MiB | 0 | 43 C, 96 W, gen 3 x16 |
| 18 GiB | 19018 / 20480 MiB | 0 | 45 C, 96 W |
| 19 GiB | OOM | | Desktop holds ~360 MiB |
| 18.5 GiB | **19530 / 20480 MiB** | 0 | 20 s hold, 45 C, 97 W, 0 Xid |

The 20 GB is addressable. 18.5 GiB is the ceiling with Hyprland up.

### Sustained burn (`probes/burn.cu`, 99% util)

| Run | Util | Temp | Power | SM clock | PCIe | Xid |
|---|---|---|---|---|---|---|
| 10 min | 99% | 61 C → peak 79 C → 76–77 C | 255–272 W | 1680–1815 MHz | gen 3 x16 | 0 |
| 30 min | 99% | 74–78 C | 258–271 W | 1680–1785 MHz | gen 3 x16 | 0 |

30 min finished `burn_done rounds=2581916`, abort 0. Idle after: 0%, 50 C, 17 W, P8.

CSV: `results/burn10.csv`, `results/burn30.csv` (sampler stalled near 24 min; live `nvidia-smi` confirmed the process through 30 min).

### LLM (Ollama CUDA 0.33.3)

`qwen2.5:32b`, 19 GB on disk. First generate, 256 tokens, 49 prompt tokens.

| Metric | Value |
|---|---|
| VRAM | **18753 / 20480 MiB** |
| Prompt | 102 tok/s |
| Generate | 7.68 tok/s |
| Load | 44.4 s (cold) |
| Decode | 13–28% util, 53–56 C, 144–151 W, gen 3 x16 |
| Xid | 0 |

Raw JSON: `results/ollama-gen.json`.

7.7 tok/s on a 32B Q4 at 18.3 GB is a normal 3080 figure. It is **not** comparable to the Mac Qwen3.8-27B Unleashed Metal baseline (8.3–10.4 tok/s, 13.2 GB Q3_K_XL, llama.cpp).

## Fair next compare

Vault protocol (do not use a 256-token Ollama one-shot):

- Runtime: llama.cpp server eval lines (`prompt eval` / `eval`)
- Record quant, ctx, flags
- 400–600 token gens, empty ctx
- Target: official or Unleashed **Qwen3.8-27B**

`qwen3.8:27b` Ollama pull was started on this host (weights layer ~16 GB). Re-run that protocol when the pull finishes.

## Rebuild probes on the Omarchy box

```bash
export PATH=/opt/cuda/bin:$PATH
nvcc -O2 -o compute probes/compute.cu
nvcc -O2 -o vram probes/vram.cu
nvcc -O3 -o burn probes/burn.cu
./compute
./vram 18.5 20
./burn 600
```
