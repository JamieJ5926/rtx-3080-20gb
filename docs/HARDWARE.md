# Hardware

## Card

- NVIDIA GeForce RTX 3080 (GA102 rev a1), PCIe `42:00.0`
- VRAM: **20480 MiB total**, 437 MiB reserved → 19.57 GiB usable, minus ~368 MiB display = ~19.2 GiB for compute
- Memory clock max 9501 MHz (19 Gbps GDDR6X). Stock 3080 bus, 320-bit → **~760 GB/s** effective (not the 3090's 384-bit 936 GB/s)
- Power limit: 320 W (default = max; 100-320 W range)
- Idle: ~38 C, ~25 W, P8. Load: 99% util, 74-78 C, 255-272 W, SM 1680-1815 MHz, PCIe gen 3 x16
- 0 Xid, 0 AER across a 30-min burn and all hillclimb runs

## VRAM ceiling with desktop up (Hyprland 296-368 MiB)

| Alloc | During-run used | Verify |
|---|---|---|
| 12 GiB | 12874 / 20480 | 0 |
| 18 GiB | 19018 / 20480 | 0 |
| 19 GiB | OOM | (display ~360 MiB) |
| 18.5 GiB | **19530 / 20480** | 0, 20 s hold |

Headless (`systemctl isolate multi-user.target`) recovers the 368 MiB if ever needed.

## Host

- AMD X399 / Ryzen Threadripper 1920X, **7 GB RAM total** (streaming model loaders required for vLLM-class stacks)
- PCIe x16, host max gen 3
- Driver `nvidia-open-dkms` 610.57.04, CUDA 13.3 (`nvcc` V13.3.73)
- No sudo, no docker, no pacman; user-space `uv` at `~/.local/bin/uv`, cmake at `~/.local/cmake/bin/cmake`
