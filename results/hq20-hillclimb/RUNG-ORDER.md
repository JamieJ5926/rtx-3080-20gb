# HyperQwen slim-20gb hillclimb rung order

Drafted 2026-09-23 while the GPU gate is held. BuildTest owns the D2 class fix, its arm rerun, the fit ladder from 6144 to 93184, measurement, and quality. Its release names the winning config and the baseline curve. Its decision rows run from h85 through the release, and the hillclimb rows continue from the next free id that the release names.

## Metric, direction, and stop predicate

The primary metric is context usability. It reads as the largest max-model-len that fits and serves with the recall frontier intact, where the frontier is the deepest fill that returns 4 of 4 unique literals. The secondary metric is decode tokens per second at fresh and at depth. Each point is the median of five timed samples of 600 tokens at temperature 0 after one discarded warmup, with prefill and draft acceptance recorded. Direction is window and frontier first, decode second. The noise band is the five-run spread of the released baseline.

The stop predicate pairs a target with a floor. The target is one kept HyperQwen config that beats turboq production in one named use class, the daily driver at fresh and 33k, or big inputs at 111k-equivalent and beyond, measured with the same protocol on both sides. The floor is all six rung categories below, each run or explicitly blocked with the reason. An early win does not end the run before the floor. The run ends after the floor when the predicate is met or when the remaining ideas are marginal.

## Bars

The turboq production bars are 76.41 fresh, 57.51 at 33k, and 54.40 at 91k decode. The h76 big-input reference points are 55.54 at 111k and 51.07 at 150k.

The keep gate per rung comes from the brief verbatim. Keep a rung when at-depth decode improves 10 percent past noise with fresh within 2 percent of its baseline, or when the window grows 50 percent with at-depth cost under 10 percent and recall intact. Otherwise revert in full. A run that misses both bars is recorded as a reverted-option, and its numbers stay in the table.

The quality guardrail runs on every kept rung. It is the four-literal recall at depth from `recall.py` with a unique seed, plus one fixed-prompt output read from `qualityfixed.py`. Any crash, CPU fallback, missing spec counter, or quality failure rejects the row.

## Frozen measurement scripts

`measure.py` discards one warmup, then takes five timed samples and splits prefill from decode, with spec counter deltas. `recall.py` plants four unique literals and reads them back. `qualityfixed.py` runs the fixed prompt with the four literals. `h76verify.py` checks production at 71 to 77 engine decode with 350 to 450 draft tokens accepted out of 500 to 650 drafted. The scripts live at `/home/jamie/hq20/`, and the copies sit in `results/hq20-slim20gb/box/`. The released baseline curve shows that the set separates fresh from depth. The set is frozen for this run.

## Window protocol

Every window runs these steps in order.

1. Announce the rung id, the one variable, and the config delta. The banner goes to `receipts/ANNOUNCE.log` before anything moves. The announce is the logged banner and spec echo, and it spends no hub send.
2. Freeze the overnight supervisor, Mac pid 34846, with `kill -STOP`.
3. Gate idle traffic. Wait until every production slot on port 8083 reads idle, with a ten minute drain budget, and record residency before the arm.
4. Stop `llama-watchdog.service` and kill the production `llama-server` with `pkill -x llama-server`.
5. Run the arm with the one variable changed, then record residency after.
6. Restore the launcher from `/home/jamie/llama/llama-serve.sh.h76-savepoint-h77`. Before any launcher points at the turboq binary, the binary must pass `test -x` and a `--version` run. The restored launcher must diff identical to the savepoint. Then start `llama-watchdog.service`.
7. Verify production. The band is 71 to 77 fresh engine decode with draft near 400 of 580.
8. Resume the supervisor with `kill -CONT 34846`.

Production must read restored and verified in every path, including arm failure and abort. `window.sh` runs on the Mac and owns the announce, the freeze, the idle gate, the dispatch, the poll, the receipt pull, and the resume. `box-window.sh` runs on the box and owns the production take-down, the arm, the measurement, and the closeout that restores and verifies production. One window is one command per rung.

## Rung order

One variable per window. The binding slots come from the BuildTest release. `[WIN_CFG]` is the exact arm env and args. `[BASELINE]` is the curve numbers. `[NOISE]` is the five-run spread. `[KV_AT_DEPTH]` is the KV type that fits at depth. `[SPEC_KNOB]` is the setting name for `num_speculative_tokens`. `[ROW_BASE]` is the next free decision id after the release.

### R0 inherit

No window. Adopt `[BASELINE]` and `[WIN_CFG]` without rerunning anything, and record the inherited baseline as the first hillclimb row.

### R1 gpu-memory-utilization

Values 0.90, 0.95 from the baseline, and 0.9775, at `[WIN_CFG]`. The KV pool size sets the fit ceiling and cache pressure at depth. Acceptance is the keep gate.

### R2 speculative ladder

`[SPEC_KNOB]` at 2, 3 from the baseline, 4, and 7 with MTP. Then DFlash2 at k 2 and k 7. The fork carries the dflash2-ngram-chains and dflash2-lookup-drafting patches, with the `VLLM_DFLASH2_CHAIN` and `VLLM_DFLASH2_LOOKUP` env families at `vllm/envs.py` lines 181 to 200. The quantized drafter pack is not on disk. `/home/jamie/models` holds only the llama.cpp GGUF `Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, and `q38-lemin` carries no separate drafter, so the with-drafter variant stays gated on a pack appearing. Record draft acceptance on every arm. The 212 tokens per second class came from DFlash2 at k 7 in single-consumer use, and this box serves one consumer.

### R3 KV dtype ladder for depth

fp8 from the baseline, then `int4_per_token_head` with the `TRITON_ATTN` backend, then the kvarn variants the build accepts. Those are `kvarn_k4v2_g128`, `kvarn_k4v4_g128`, `kvarn_k4v2_g64`, and `kvarn_k4v4_g64` from the `CacheDType` literal at `vllm/config/cache.py` line 19. At each dtype map the window and the recall frontier. The mechanism is the KV cost per token, about 20 KiB at int4 per-token-head against about 58 KiB at fp8. Required output is the window and recall frontier per KV type.

### R4 context ladder

With the winning KV type from R3, find the largest `max-model-len` that fits and serves. Then run recall probes with unique literals at the 111k-equivalent fill and near the ceiling. This is the big-input rung, and acceptance is the window bar.

### R5 batch knobs

`max-num-batched-tokens` at 1024 and 4096 against the baseline 2048, and `max-num-seqs` at 1 and 2 against the baseline 8. Single-consumer decode favors fewer and larger batches. Acceptance is the decode bar.

### R6 fork env knobs

One knob per window. `VLLM_MARLIN_REPACK_STAGED` at `"1"` and at `"0"` for the load peak, since the unset default is on for sm80 only and both states are arms on this sm86 card. `VLLM_INT4_MQ_3D` at 1 for verify speed on the int4 path. Then cuda-graph capture sizing through `VLLM_V2_CUDAGRAPH_MEM_MIB`. Record the load peak and load time on the repack arm. The alexander-ollman writeup found that the verify kernel matters more than the drafter, which is why the int4 verify switch is in the ladder.

## End deliverables

The ladder table carries every rung with config, curve points, acceptance, and verdict. The window and recall frontier come per KV type. The final comparison runs against 76.41, 57.51, and 54.40 and ends with one recommendation: daily driver, big inputs, or neither. The untested list and the top follow-on close the report. Production must read verified restored in every path. Decision rows land in `decision.tsv` and receipts land in `results/hq20-hillclimb/`, committed and pushed per standing authorization.

## Running untested list

- DFlash2 with the quantized drafter. No vLLM drafter pack exists at `/home/jamie/models` or `/home/jamie/models/q38-lemin`. The llama.cpp GGUF `Qwen3.8-27B-DFlash2-Q4_K_M.gguf` belongs to a different engine.
- `VLLM_SPEC_DECODE_ATTN` and `VLLM_SPEC_DECODE_ATTN_QMAX`, the split-KV verify kernel switch at `vllm/envs.py` line 219. The brief does not name it. It is the top follow-on candidate because the verify kernel is the named mechanism.
- The turboquant KV dtypes and `int8_per_token_head` at `vllm/config/cache.py` lines 28 to 37. They fall outside the briefed R3 order.
