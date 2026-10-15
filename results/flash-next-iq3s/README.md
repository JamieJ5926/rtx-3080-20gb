# Qwen3.8-Flash-Next IQ3_S on one RTX 3080 20GB

Strata on home-pc-1. Threadripper 1920X, 55 GB DDR4, the card at 320 W, BAR1 256 MB. The model is ISTA GSQ-RCO IQ3_S with the refusal control vector on. Context 262144, int8 KV, 32768 of that resident on the GPU, MTP spec 4, 34 GB expert budget.

The bench is one cold prompt of about 39k tokens, then six agent turns, then three short chats. Recall is planted keys. `climb.jsonl` is one JSON object per arm.

## Kept

| Arm | Turn decode tok/s | Cold prefill tok/s | Recall |
|---|---:|---:|---|
| f256-r34-int8 (spec 4, 34 GB, int8) | 54.5 | 911 | 5/5 |

Short-chat decode on that arm was 41.8 tok/s. Tool calls were 6/6. This is the config to serve. A new session pays the cold prompt.

## Same bench, not kept

| Arm | Turn decode | Cold prefill | Why it lost |
|---|---:|---:|---|
| spec 3 | 59.0 | 549 | decode up, cold start much worse |
| resident 36 GB | 58.7 | 715 | same |
| k8v4 KV | 55.8 | 826 | small decode gain, worse cold prefill |
| 16k prefill chunks | 55.6 | 538 | cold prefill fell apart |
| spec-min-p 0.7 | 55.0 | 725 | noise |
| spec 2 | 54.0 | 599 | both worse |
| spec 6 | 53.0 | 515 | both worse |
| resident 32 GB | 52.8 | 539 | both worse |
| 32k prefill chunks | 51.5 | 451 | both worse |
| adapt-swaps 24 | 51.2 | 766 | decode worse |

q8 KV never started. The engine accepts fp16, int8, q4_0, or k8v4.

Earlier rows in `climb.jsonl` (`base-r30`, the `b52-*` arms) are the same model before the 34 GB budget and the quiet box. `b52-r34` was 52.5 tok/s turn decode and 973 cold prefill at 131k context. The jump from about 17 tok/s to about 52 came from giving the experts RAM, not from the flag sweeps after it.

llama.cpp RPC on this card, a different bench, stopped at 17.94 tok/s tg128 (`../hillclimb-iq3s` is not in this folder; the summary lives in the mixed-cluster repo).
