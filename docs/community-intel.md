# Community intel for Qwen3.8-27B serving

Captured 2026-09-22 from the Chinese and English local-LLM scene. The forums block unauthenticated fetches, so search ran through Bing's index plus one logged-in browser pass. This file records what we learned, where each fact came from, and what the usability hillclimb does with it.

## Sources

- [sudoingX/qwen38-mtp](https://github.com/sudoingX/qwen38-mtp). The community MTP record for Qwen3.8-27B on llama.cpp. 53 configurations, 40 contributors, 2016 Pascal through Blackwell, plus a per-card sweep table.
- [Indras-Mirror/llama.cpp-turboq-mtp](https://github.com/Indras-Mirror/llama.cpp-turboq-mtp). A llama.cpp fork with sliding-window attention for the `qwen35` hybrid, a fused TBQ4 KV cache, and a custom MTP.
- [Chiphell VBIOS thread](https://www.chiphell.com/thread-2483939-1-1.html) and [NGA BIOS flash tutorial](https://ngabs.com/read.php?tid=23857470). Frankencard power unlocks from 320W to 366W and 400W by flashing another brand's VBIOS.
- [Zhihu frankencard guide](https://zhuanlan.zhihu.com/p/2029188132206035598). The 3080 20G frankencard as a local-LLM card.
- [Zhihu MTP flag note](https://zhuanlan.zhihu.com/p/2040374238842967425). Confirms the upstream flag names `--spec-type draft-mtp` and `--spec-draft-n-max`.

## The seven community rules

Recorded in the qwen38-mtp README with per-card evidence. Our action follows each rule.

1. The draft depth sweet spot depends on the card and the split mode. 24GB cards peak at `--spec-draft-n-max 2`. Bigger or faster cards peak at 3 to 4. Our h31 data prefers 3 on this card, so the ladder sweeps 2, 3, and 4 rather than adopting one value.
2. `--spec-draft-p-min` in the 0.60 to 0.75 range helps bandwidth-starved rigs and hurts fast ones. Acceptance can rise while throughput falls. The ladder sweeps 0.60 and 0.75 and keeps the value only if the metric moves.
3. The gain scales with generation length while overhead dominates. Generations under roughly 400 tokens can pay more than they win. The frozen protocol uses 600 tokens and stays above that floor.
4. On multi-GPU boxes, fix `--split-mode` before touching spec flags. Not applicable to this single-card box.
5. Speculative decode is a single-stream optimization. The gain is gone by `--parallel 4`, and a `--parallel 2` baseline reads low. Both arms measure at `--parallel 1`, which matches our current flags.
6. Rebuild llama.cpp before tuning. The community measured +10 to 15 percent on every quant from newer builds alone, and one b10450 baseline matched the day-one with-flag number. We run b10809. Attempt E rebuilds from current upstream and measures the floor before any flag.
7. A shared desktop halves decode, silently. One report had a compositor spill 3.5GB of weights to host RAM while `/health` stayed green and decode halved with no error. This box runs a desktop. Every measurement now checks that the weights are resident and records desktop GPU memory. This rule likely explains the one anomalous 55.66 t/s run in this program.

## Sliding-window attention for the qwen35 hybrid

The turboq fork windows the dense attention layers so decode cost stops scaling with the full context, and keeps 8 layers global so long-range recall survives. Their measured table at roughly 62K context.

| Config | Decode | Beyond-window recall |
|---|---|---|
| Pure SWA, all layers windowed | ~97 t/s | No, hallucinates |
| SWA hybrid, 8 global layers | ~70 t/s | Yes, exact |
| Dense, no SWA | ~18 to 20 t/s | Yes, slow |

The flags are `--override-kv qwen35.attention.sliding_window=int:4096` and `--override-kv qwen35.attention.swa_global_layers=int:8`. The qwen35 build lives in that fork, so this change needs a user-space build, no sudo. Our depth curve falls 43 percent from fresh to 91K fill (h54), which is the collapse SWA bounds. Attempt F.

The fork also ships a fused TBQ4 and TBQ3 KV path and its own MTP. Its Qwen3.8 numbers are 74.1 t/s with MTP against 44 to 50 without, on a 4090. Treat as a candidate engine swap after attempt F proves the SWA effect.

## Frankencard VBIOS unlocks

Filed, not scheduled. The threads document power-limit unlocks from 320W to 366W and 400W. Decode is memory-bandwidth-bound on this card, so power moves it little. Prefill and clocks would gain more. Flashing a VBIOS on a modded card carries brick risk, and this program keeps the card at stock limits.

## The community table gap

The qwen38-mtp sweep table has a 3080 10GB row at 45.1 to 64.4 t/s and no 20GB row. Our measured pair is 36.6 to 72.68 t/s at a 98304 context window (h45). A pull request with our row would lead the 3080 class and doubles as the distribution for the findings post.

## Ladder mapping

| Attempt | Change | Source |
|---|---|---|
| A | `GGML_CUDA_FORCE_MMQ=1` | h29, local |
| B | Sweep `--spec-draft-n-max` 2, 3, 4, then `--spec-draft-p-min` 0.60 and 0.75 | Rules 1 and 2 |
| C | `--cache-type-k q4_0 --cache-type-v q4_0` for the context ceiling | qwen38-mtp launch command |
| D | Kept wins combined | Hillclimb discipline |
| E | Rebuild llama.cpp from current upstream, measure the floor | Rule 6 |
| F | SWA hybrid build of the turboq fork | The table above |
| A2 | `GGML_CUDA_GRAPH_OPT=1` for concurrent Q, K, V streams | CUDA discussion 17621 |

## Second sweep, later on 2026-09-22

### The concurrent-streams flag

The upstream CUDA work in [discussion 17621](https://github.com/ggml-org/llama.cpp/discussions/17621) fuses token-generation kernels and runs the Q, K and V projections on concurrent CUDA streams. Kernel fusion is on by default. The concurrent streams need `GGML_CUDA_GRAPH_OPT=1` and work on single-GPU setups only, which matches this box. The same thread records a counter-example where the flag slowed token generation from 61.76 to 54.77 on an NVIDIA GB10. Sweep it and keep it only if the metric moves. Attempt A2.

### The speed-of-light calculation

The thread links `gguf_bandwidth.py`, a script that computes the theoretical tokens per second for any GGUF on any bandwidth figure. Run it for our model at 760 GB per second before claiming any build is fastest. It answers how much headroom exists above our 72.68 measured number.

### The card-class anchor

A Zhihu test measured the modded 3080 20G at 83 percent of an RTX 3090 24G in token generation speed, Ollama with Qwen3 in FP16 and Q4_K_M, at 70 percent of the rental price. Source: [Zhihu writeup](https://zhuanlan.zhihu.com/p/1968331561104564891), [syndicated summary](https://post.smzdm.com/p/a46m428x/). The summary is AI-generated, so treat the 83 percent figure as directional.

### Driver and container notes

A frankencard setup walkthrough confirms `nvidia-driver-550` on Ubuntu 22.04 with the 20G mod and documents the community vLLM image `dengcao/vllm-openai:v0.9.2`. We run driver 610.57. Source: [cnblogs walkthrough](https://www.cnblogs.com/yisheng163/p/20408329).
