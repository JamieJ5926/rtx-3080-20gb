# RTX 3080 20 GB

Measurement log for a modded GeForce RTX 3080 with 20 GB VRAM on CUDA Linux. Not a distro project. Weights are not in this repo.

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

### Qwen3.8 27B

600 tokens, temperature 0. Think-on is not answer speed: all 600 tokens went into thinking and the visible response was empty (`resp_len=0`).

| Setup | Generate tok/s | n | Notes |
|---|---|---|---|
| Ollama think-on | 49.3 median | 3 | empty visible answer |
| Ollama think-off | 41.05 median | 3 | usable text. First product baseline |
| llama.cpp CUDA no-draft | 34.2 median | 3 | reverted as speed |
| llama.cpp `--spec-type draft-mtp` Ollama 16 GB blob | 50.95 median | 6 | first real-text CUDA decode win |
| llama.cpp `--spec-type draft-mtp` Unsloth UD-Q3_K_XL 13.15 GB | 60.7 median | 3 | kept vs 16 GB blob. Lost to IQ4_XS |
| llama.cpp `--spec-type draft-mtp` Unsloth UD-IQ4_XS 14.25 GB | **67.9 median** | 3 | kept. Current best |

IQ4_XS is 14.25 GB on disk. The 16 GB Ollama blob used about 18 GB of 20 GB VRAM under MTP2.

Raw: `results/qwen38-27b-gen.json`, `results/mtp2-n6.txt`, `results/q3-mtp2-n3.txt`, `results/iq4-mtp2-n3.txt`.

## Hillclimb

Metric: median generate tok/s, 600 tokens, temperature 0, real visible text. Higher is better.

Kept stack: Unsloth `Qwen3.8-27B-UD-IQ4_XS.gguf` with `llama-cli -ngl 99 -fa on --spec-type draft-mtp`.

Tried and reverted: llama.cpp no-draft (34.2), `--spec-draft-n-max 8` (43.8), `-ctk q8_0 -ctv q8_0` (52.1). Power already at 320 W max; clock lock needs root.

Later, not run: long-context prompt processing, decode after KV has grown, batch and concurrent agents, vLLM or SGLang.
