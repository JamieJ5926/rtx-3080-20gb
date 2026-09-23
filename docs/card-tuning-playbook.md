# How to hillclimb a new GPU card for local model serving

A working procedure distilled from the 2026-09 RTX 3080 20GB program. Use it when a new card lands on the bench. Order matters. Measure the ceiling before tuning anything, take platform levers before software ones, and keep one variable per attempt.

## 1. Intake and ceiling

Record the facts before touching a flag.

- Chip, memory capacity, memory bandwidth and compute capability.
- BAR state. `lspci -vv` for the BAR regions and `nvidia-smi -q` for the BAR1 figure.
- Power limit and current draw, driver and CUDA toolkit versions.
- Whether the box runs a desktop on the GPU. A desktop on the GPU silently steals memory and slows decode.

Then compute the theoretical decode ceiling. Transfer bytes per token divided into memory bandwidth gives the raw tokens per second limit. The script that does it for any GGUF is coder543's `gguf_bandwidth.py` from llama.cpp discussion 17621, run per cache type and fill depth. Every later claim gets compared to that ceiling, so nothing gets called a win that is just an accounting error.

## 2. Platform levers, before software

**Resizable BAR.** Stock firmware commonly parks the GPU BAR at 256 MiB. The options in order of preference.

1. On Linux, enable 4G decoding in firmware and let the kernel resize BARs. Boot with `pci=realloc` and fix DSDT only if the platform needs it. This avoids firmware flashing entirely.
2. [ReBarUEFI](https://github.com/xCuri0/ReBarUEFI) adds a DXE driver to the firmware image and enables Resizable BAR on unsupported platforms. Turing cards need [NvStrapsReBar](https://github.com/terminatorul/NvStrapsReBar) instead. Recovery from a bad BAR size is a CMOS clear.
3. A wrong size can stop boot. Have the CMOS reset documented before trying.

Inference benefit is unproven at the time of writing. The mapping improves, compute behaviour does not change. Measure before and after with the frozen benchmark or treat it as unverified.

**Power and clocks.** VBIOS flashes unlock power limits, frankencard 3080 20G owners document 320W to 366W and 400W unlocks. Decode is memory-bandwidth-bound so power is mostly a prefill lever. Firmware flashing can brick a card. Treat it as last resort and measure the bandwidth ceiling first to see if power is even the binding constraint.

## 3. Software ladder

Work these in order. Each is one attempt against the frozen benchmark.

1. **Engine choice.** A community fork beat upstream by about 5 percent at identical flags in this program. Same card, same model, different kernels. Compare one fork and one upstream build before tuning anything else.
2. **Speculative decoding.** The largest single lever seen here, roughly 2x. Use the model's built-in MTP head when the file has one. Sweep the draft depth per card, the optimum moves with hardware and quant. Confidence gating measured as helping starved cards and hurting fast ones, so sweep it and do not adopt it blind.
3. **KV cache type.** q8_0 to q4_0 buys context at a small speed cost. A quantized KV cache buys context, never speed. Cache type choices are the context lever.
4. **Sliding window overrides** on hybrid architectures. Windowed layers hold a bounded cache while a few global layers hold the full history. Exact recall testing is mandatory, since too few globals silently breaks long-range recall.
5. **Batch and ubatch.** Prefill scales with ubatch, decode can regress. Sweep at the working context, not at empty.
6. **Weight quant tiers.** Fewer bytes per token raises the ceiling. Quality is the trade and it is model specific. Never infer quality from file size.

## 4. Measurement discipline

- One variable per attempt.
- Five timed samples after a discarded warmup.
- Record prefill and decode both. A decode-only check misses silent CPU fallback in attention kernels.
- Verify memory residency before and after every arm. A shared desktop can spill weights to system RAM and halve throughput with no error anywhere.
- Reject any row with a crash, restart or missing counters. A crash is a finding, never noise.
- Keep a decision log, one row per attempt with hypothesis, change, before, after and verdict. The rows from this program live in `decision.tsv`.

## 5. Usability gates, not just speed

- Exact recall at working depth, tested with planted literals, is the real usability gate for agent work. Large windows degrade recall before they fail outright.
- Compaction or memory management across long sessions must be tested with chained tests, not single ones.
- Content changes results. Draft acceptance varies with predictable versus novel text, so a single lucky run never replaces the protocol median.

## 6. Peer scoreboard

[qwen38-mtp](https://github.com/sudoingX/qwen38-mtp) keeps the community per-card sweep table. Find the nearest card class before starting so the ladder begins where the field ended, and contribute the row when done.
