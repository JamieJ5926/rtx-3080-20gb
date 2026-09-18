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

Tried and reverted: no-draft 34.2, IQ3_S 54.7, Q4_K_S 49.7, n-max 8/4, q8/q4 KV, ub 2048, ngram 35.2, fa-off 54.5, extra MTP `-md` 66.7, llama-server 67.8. Power already 320 W max. Clock lock needs root. 8k context OOM (13 GB extra). `draft-simple -md` segfaulted.

Not run: vLLM or SGLang, batch/concurrent agents. Clocks need root.

### 2026-09-18 hillclimb day 2 (h20-h24)

Same-day upstream control reproduced 67.2 (67.1/67.2/67.3), within 1% of 67.9.

| Setup | Generate tok/s | n | Verdict |
|---|---|---|---|
| upstream n-max 4 + p-min 0.65 | 58.0 median | 3 | reverted (ungated n-max 4 was 59.0) |
| upstream n-max 6 + p-min 0.75 | 49.8 median | 3 | reverted |
| upstream DFlash2 n-max 7 | 46.5 median | 3 | reverted |
| ik_llama.cpp IQ4_KS MTP n-max 2 | 66.16 median | 3 | reverted |
| **ik_llama.cpp IQ4_KS MTP n-max 4** | **69.34 median** (69.01/69.34/69.43, 4th run 69.96) | 3+1 | **kept, new best** |

New kept stack: ik_llama.cpp (built CUDA 13.3, `GGML_CUDA_F16`, `/home/jamie/ik_llama.cpp/build/bin/llama-cli`) with `ubergarm/Qwen3.8-27B-MTP-IQ4_KS.gguf` 15.75 GiB (PPL 6.9938 vs BF16 6.9540), flags `-ngl 99 -c 4096 -fa on --spec-type mtp:n_max=4,p_min=0.0`. ik CLI lacks `--single-turn`/`-no-cnv`; pipe `-p` with `</dev/null` and a small `-c` (model default 262k KV OOMs at load). Raw: `results/ik-iq4ks-n4.txt`.

Hyprland costs 296 MiB idle and no decode impact; desktop stays (no iGPU on TR 1920X). Headless remains available via `systemctl isolate multi-user.target` if context headroom is ever needed.
Build: `llama-cli` 0.4.0-dev b10809 (5266f24da7), GNU 16.2.1. All h3+ numbers are on this build.

Candidates from 2026-09-18 research (see `decision.tsv` h20-h26): `--spec-draft-p-min` sweep 0.65-0.75 at n-max 4/6 (community rule 2: gating pays on bandwidth-poor cards), DFlash2 draft (`--spec-type draft-dflash`, ~73 vs ~63 MTP on 2x5060 Ti per PR 27858), ik_llama.cpp `IQ4_KS` + built-in MTP (3090 kept setup: 72.9 t/s decode), headless cost of Hyprland (~360 MiB display, no iGPU on TR 1920X), memory OC (needs root; h6 contradiction to re-probe). Sources: `github.com/sudoingX/qwen38-mtp`, llama.cpp PR 27858, `post.smzdm.com/p/a46m428x`, r/LocalLLaMA backend-comparison thread 1tgis7s.
