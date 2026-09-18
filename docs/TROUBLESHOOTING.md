# Troubleshooting and lessons

## llama.cpp / ik_llama.cpp

- **Grep pitfall**: generated PCIe text contains "t/s" and "time =" — anchor greps (`^main:`, `Generation:` prefix) or you capture model output.
- **ik CLI quirks**: no `--single-turn`/`-no-cnv`; pipe `-p` with `</dev/null`. Model default 262k ctx OOMs at load — always pass a small `-c`. Prism fork needs `--single-turn`.
- **draft-mtp determinism**: spec draft can change greedy committed tokens (llama.cpp #23335, closed as expected — different kernels per batch size). Q8_0 agrees with no-MTP; Q4-class drifts. For uncensored GGUF, orcarouter discussion 2 (Vulkan corruption at n-max 4) — n-max 2 safe, n-max 3 was clean and faster on this box.
- **ik build**: `source /etc/profile.d/cuda.sh && ~/.local/cmake/bin/cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DGGML_CUDA_F16=ON -DGGML_CCACHE=OFF && cmake --build -j 24`.

## SSH / box

- Nested quotes over ssh break: write remote scripts with `printf '%s\n' … > /tmp/x.sh; chmod +x; nohup /tmp/x.sh`.
- `sudo -n` and `docker` both refused; the docker-group sysfs recipe belongs to the home-pc box, not this one.
- Host RAM 7 GB — vLLM-class loads need a streaming loader (`--load-format=runai_streamer` with `model-loader-extra-config={"memory_limit":2147483648}`).
- Rapid consecutive ssh sessions occasionally return 255 (Tailscale sshd); retry with a pause, keep commands single-purpose.

## vLLM / HyperQwen (2026-09-18 debugging trail)

1. PyPI `vllm==0.28.0` on cu132 wheels installs fine; `--torch-backend` flag does not (no vllm wheels on the torch index).
2. SergiioB GPTQ-Int4 checkpoint: weights alone 18.61 GiB of 19.57 usable → `torch.OutOfMemoryError` during init at any `gpu-memory-utilization`, even `--enforce-eager`. Never fit.
3. leminkozey W4A16: stock vLLM refuses `embed_tokens.weight_packed` (HyperQwen packed-tensor format). Only the patched fork loads it.
4. HyperQwen bare-metal install: clone repo, `uv venv --python 3.12`, install their dep set, apply `patches/series` (38 files, skip `dflash2-backport.patch`). torch 2.13.0+cu130 matches their Dockerfile pin exactly.
5. First boot at GPU_UTIL 0.90: `RuntimeError: torch_call_dispatcher("aten::empty", …)` inside `gptq_marlin_repack` — **no OOM text**. Not an ABI mismatch (small-size probe dispatches fine). It is OOM with the message swallowed by the stable-ABI error path; the allocator log shows `free: 33 MiB, total: 21017133056`.
6. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (their bare-metal gotcha 3) did not fix it — the card is genuinely full, not fragmented.
7. Discriminator experiments: dummy weights and real weights both load clean at GPU_UTIL 0.60 (fail later with the clean `No available memory for the cache blocks`); streamer loader is innocent (passes at 0.60).
8. Their `prepare/quant_mtp.py` requantizes the BF16 MTP module (849→431 MB, round-trip rel err 0.0076) — a needed step the ready-made checkpoint ships unquantized; not sufficient alone on 19.57 GiB.
9. Verdict: checkpoint + patched stack needs >19.2 GiB on this card. A leaner body (4-bit MTP `--bits 4`, lower-util profile with tiny MAX_LEN) is the only untried slack; the stack itself installs and boots on Ampere sm86.

## Bench discipline

- One change, one measurement; keep or revert. Median of 3. Same-day control before trusting day-over-day deltas.
- A visible "works" is not a number: capture the t/s line or the JSON receipt before logging a row.
