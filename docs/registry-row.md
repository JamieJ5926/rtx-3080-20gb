# Registry row, local-ai-registry submission

Row as submitted to the 0xsero/local-ai-registry hardware table, with per-cell provenance. Every number below was measured on this machine on 2026-09-23 unless noted.

| Card | VRAM | Model | Weights | Engine | Ctx | Decode tok/s | Prefill tok/s (prompt) | Concurrency (per stream) | MTP |
|---|---|---|---|---|---|---|---|---|---|
| RTX 3080 modded 20G | 20 | Qwen3.8-27B | 15.6 GB | llama.cpp fork | 196K | 76.4 | 803 (130K) | 1 (76) | yes |

## Provenance per cell

| Cell | Value | Evidence |
|---|---|---|
| Card | Modded RTX 3080 20G, GA102, memory bandwidth about 760 GB/s | docs/HARDWARE.md, nvidia-smi reports 20480 MiB |
| VRAM | 20 GB | nvidia-smi FB total 20480 MiB, CUDA visible 19.57 GiB |
| Model | Qwen3.8-27B, bartowski orcarouter uncensored IQ4_XS repack | /home/jamie/models/orcarouter-uncensored-IQ4_XS.gguf |
| Weights | 15.6 GB | GGUF file 15,567,825,152 bytes, 14.49 GiB by llama-bench |
| Engine | llama.cpp turboq qwen35 fork | build commit aaa66a5, launcher LD_LIBRARY_PATH to ~/llama.cpp-turboq-mtp/build/bin |
| Ctx | 196608 | launcher -c 196608, fills measured to 150000 tokens, decision.tsv h76 |
| Decode | 76.41 median | decision.tsv h76, 600 tokens, temp 0, n=3, series 76.01/76.67/76.41 |
| Prefill | 803.2 tok/s at 130015 tokens | single probe 2026-09-23, prompt_n 130015, cache_prompt false |
| Concurrency | 1 slot, 76.4 per stream | launcher --parallel 1 |
| MTP | enabled, n-max 3 | --spec-type draft-mtp, draft acceptance 394 of 612 in the h76 runs |

## Supporting curve

Decode by fill on the same config, decision.tsv h76. Fresh 76.41, 33355 fill 57.51, 91655 fill 54.40, 150000 fill 51.07. Exact literal recall passes 4 of 4 at 111k and 150k and degrades to 1 of 4 at 195k. Prefill at 16701 fill is 1061.6 tok/s.

## Notes for reviewers

The weights are an uncensored abliteration of Qwen3.8-27B. The engine is a community llama.cpp fork with qwen35 sliding-window attention support, so the launch is a host process rather than a digest-pinned container. The full decision trail of 49 plus attempts is in decision.tsv in this repository.
