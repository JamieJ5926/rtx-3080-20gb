# HyperQwen slim-20gb hillclimb rung order

Drafted 2026-09-23 while the GPU gate is held. BuildTest owns the D2 class fix, its arm rerun, the fit ladder from 6144 to 93184, measurement, and quality. Its release names the winning config and the baseline curve. Its decision rows run from h85 through the release, and the hillclimb rows continue from the next free id that the release names.

## Metric, direction, and stop predicate

The primary metric is depth decode at the 33k and 60k points, per Main's 2026-09-23 steering that the depth collapse is the problem and fresh is already won. Context usability stays the named deliverable as the largest `max-model-len` that fits and serves with the recall frontier intact, where the frontier is the deepest fill that returns 4 of 4 unique literals. Each point is the median of five timed samples of 600 tokens at temperature 0 after one discarded warmup, with prefill and draft acceptance recorded. Fresh decode is a guardrail held within 2 percent of its baseline. The noise band is the five-run spread of the released baseline.

The stop predicate pairs a target with a floor. The target is one kept HyperQwen config that beats turboq production in one named use class, the daily driver at fresh and 33k, or big inputs at 111k-equivalent and beyond, measured with the same protocol on both sides. The floor is the six rung categories below plus the checkpoint-portability and censorship A/B phases Main added on 2026-09-23, each run or explicitly blocked with the reason. An early win does not end the run before the floor. The run ends after the floor when the predicate is met or when the remaining ideas are marginal.

## Bars

The turboq production bars are 76.41 fresh, 57.51 at 33k, and 54.40 at 91k decode. The h76 big-input reference points are 55.54 at 111k and 51.07 at 150k.

The keep gate per rung comes from the brief verbatim. Keep a rung when at-depth decode improves 10 percent past noise with fresh within 2 percent of its baseline, or when the window grows 50 percent with at-depth cost under 10 percent and recall intact. Otherwise revert in full. A run that misses both bars is recorded as a reverted-option, and its numbers stay in the table.

The quality guardrail runs on every kept rung. It is the four-literal recall at depth from `recall.py` with a unique seed, plus one fixed-prompt output read from `qualityfixed.py`. Any arm crash, CPU fallback, missing spec counter, or quality failure rejects the row. The production teardown terminate at the window-stop step is not an arm crash, and the window protocol names it below.

## Frozen measurement scripts

`measure.py` discards one warmup, then takes five timed samples and splits prefill from decode, with spec counter deltas. `recall.py` plants four unique literals and reads them back. `qualityfixed.py` runs the fixed prompt with the four literals. `h76verify.py` checks production at 71 to 77 engine decode with 350 to 450 draft tokens accepted out of 500 to 650 drafted. The scripts live at `/home/jamie/hq20/`, and the copies sit in `results/hq20-slim20gb/box/`. The released baseline curve shows that the set separates fresh from depth. The set is frozen for this run.

## Window protocol

Every window runs these steps in order.

1. Announce the rung id, the one variable, and the config delta. The banner goes to `receipts/ANNOUNCE.log` before anything moves. The announce is the logged banner and spec echo, and it spends no hub send.
2. Freeze the overnight supervisor, Mac pid 34846, with `kill -STOP`.
3. Gate idle traffic. Wait until the production request log at `/home/jamie/llama/llama-server.log` shows no new bytes across 30 seconds, with a ten minute budget, and record residency before the arm. The `/slots` and `/metrics` endpoints return empty bodies on this build, so the request log is the only state that gates.
4. Stop `llama-watchdog.service` and kill the production `llama-server` with `pkill -x llama-server`.
5. Run the arm with the one variable changed, then record residency after.
6. Restore the launcher from `/home/jamie/llama/llama-serve.sh.h76-savepoint-h77`. Before any launcher points at the turboq binary, the binary must pass `test -x` and a `--version` run. The restored launcher must diff identical to the savepoint. Then start `llama-watchdog.service`.
7. Verify production. The band is 71 to 77 fresh engine decode with draft near 400 of 580.
8. Resume the supervisor with `kill -CONT 34846`.

Production must read restored and verified in every path, including arm failure and abort. `window.sh` runs on the Mac and owns the announce, the freeze, the idle gate, the dispatch, the poll, the receipt pull, and the resume. `box-window.sh` runs on the box and owns the production take-down, the arm, the measurement, and the closeout that restores and verifies production. One window is one command per rung.

Every window stop logs one teardown terminate from the `aaa66a5` binary. The SIGTERM exit path runs `std::terminate` in `stream_session_manager::~stream_session_manager()`, and ggml dumps a gdb backtrace into the production log. Classify it as a teardown artifact and never as an arm failure. Evidence lives at `reviews/errors/2026-09-23-llama-server-teardown-terminate.md`.

## Rung order

One variable per window. The binding slots come from the BuildTest release. `[WIN_CFG]` is the exact arm env and args. `[BASELINE]` is the curve numbers. `[NOISE]` is the five-run spread. `[KV_AT_DEPTH]` is the KV type that fits at depth. `[SPEC_KNOB]` is `DRAFT_TOKENS` for MTP and `DFLASH_TOKENS` for the DFlash2 verify block, the two settings that feed `num_speculative_tokens` in the launcher spec config. `[ROW_BASE]` is the next free decision id after the release.

Main's depth-first steering of 2026-09-23 reorders execution. The fresh win is banked and fresh is a guardrail only. The problem is the depth collapse at 33k and 60k against the turboq bars, with 93184 fit-blocked, so the depth rungs come first and the int4 per-token-head cost at the 75093-token pool is the thing to understand. Execution order is R2, the draft-chain sweep with 33k as the primary point, then R3, the KV dtype ladder measured at 33k and 60k, then R1b, R4, R5, and R6. R1a was already mid-window when the steering arrived and stays in place because it measures both depth points.

### R0 inherit

No window. Adopt `[BASELINE]` and `[WIN_CFG]` without rerunning anything, and record the inherited baseline as the first hillclimb row.

### R1 gpu-memory-utilization

Values 0.90, 0.95 from the baseline, and 0.9775, at `[WIN_CFG]`. The launcher knob is `GPU_UTIL`, which maps to `--gpu-memory-utilization`, and its own default is 0.93 because the DeltaNet workspace in the MTP decode path allocates beyond the startup memory profile. The 0.9775 arm is the crash-risk arm, and a boot failure rejects the row rather than counting as noise. The KV pool size sets the fit ceiling and cache pressure at depth. Acceptance is the keep gate.

### R2 speculative ladder

`DRAFT_TOKENS` at 2, 3 from the baseline, 4, and 7 with MTP. The `k=4` arm carries a documented hazard: on fp8 with FlashInfer it crashes once one request finishes while another is mid-generation (vLLM 0.28.0), so this arm runs strictly single-stream and any crash rejects the row. Then run the drafter-free DFlash2 variants as first-class arms under `SPEC=mtp`. Set `VLLM_DFLASH2_CHAIN=1` for candidate chains and `VLLM_DFLASH2_LOOKUP=1` for lookup drafting, each at k 2 and k 7. The fork carries the dflash2-ngram-chains and dflash2-lookup-drafting patches with those env families at `vllm/envs.py` lines 181 to 200, and the chain mode drafts from context, so no drafter pack is needed. The with-drafter 212-class variant is pack-gated. `SPEC=dflash2` refuses to boot without `models/Qwen3.8-27B-DFlash2-W4A16/model.safetensors` under the arm repo, no such pack exists at `/home/jamie/models` or `/home/jamie/qwen-arm20/models`, and `prepare/fetch_dflash2.py` would download it, which the brief does not authorize. Record draft acceptance on every arm. The 212 tokens per second class came from DFlash2 at k 7 in single-consumer use, and this box serves one consumer.

### R3 KV dtype ladder for depth

fp8 from the baseline, then `int4_per_token_head` with the `TRITON_ATTN` backend, then the kvarn variants the build accepts. Those are `kvarn_k4v2_g128`, `kvarn_k4v4_g128`, `kvarn_k4v2_g64`, and `kvarn_k4v4_g64` from the `CacheDType` literal at `vllm/config/cache.py` line 19. The backend switch is forced, not chosen: on sm86 the launcher records that both `FLASH_ATTN` and `TRITON_ATTN` refuse fp8, so the fp8 arm runs FlashInfer and the per-token-head arms run `TRITON_ATTN`. At each dtype map the window and the recall frontier. The mechanism is the KV cost per token, about 20 KiB at int4 per-token-head against about 58 KiB at fp8. Required output is the window and recall frontier per KV type.

### R4 context ladder

With the winning KV type from R3, find the largest `max-model-len` that fits and serves. Then run recall probes with unique literals at the 111k-equivalent fill and near the ceiling. This is the big-input rung, and acceptance is the window bar.

### R5 batch knobs

`--max-num-batched-tokens` at 1024 and 4096 against the 2048 the launcher hardcodes, and `MAX_SEQS`, which maps to `--max-num-seqs`, at 1 and 2 against the baseline 8. The launcher expands `EXTRA_ARGS` after its own flags, so the batched-tokens arms shadow the hardcoded value through `EXTRA_ARGS`, and the config resolver warns about the shadow and proceeds. Single-consumer decode favors fewer and larger batches. Acceptance is the decode bar.

### R6 fork env knobs

One knob per window. `VLLM_MARLIN_REPACK_STAGED` at `"1"` and at `"0"` for the load peak, since the unset default is on for sm80 only and both states are arms on this sm86 card. `VLLM_INT4_MQ_3D` at 1 for verify speed on the int4 path. Then cuda-graph capture sizing through the `CG` env knob, which sets `max_cudagraph_capture_size` in the compilation config and defaults to 32, with `VLLM_V2_CUDAGRAPH_MEM_MIB` as the secondary form only if `CG` alone stays flat. `CUDAGRAPH_MODE` stays untouched. Record the load peak and load time on the repack arm. The alexander-ollman writeup found that the verify kernel matters more than the drafter, which is why the int4 verify switch is in the ladder.

### R7 checkpoint portability, the phase after depth

Per Main's 2026-09-23 scope addition and `docs/overnight-rungs.md` under the fourth field sweep. This converts the fork's claim from works on the leminkozey uncensored checkpoint to works on the model class. The prerequisite is a censored packed checkpoint, a W4A16 or AWQ AutoRound pack, either downloaded or produced by the fork's own prepare pipeline against stock weights. Three steps. First, fit and measurement on the standard censored Qwen3.8-27B packed checkpoint in the same shape as the depth mission. Second, the head and vocab calibration on that checkpoint, recorded with the same provenance form as commit 3. Third, the acceptance verdict. The fast path must engage on the second checkpoint, the memory trace must show the same single-read and early-binding behavior, and the fresh and 33k points must land within 10 percent of the uncensored stack's numbers at the same shape. The GGUF-side expectation is about 9 percent slower than the uncensored repack at production shape (66.15 against 72). Any divergence is recorded as a checkpoint-specific finding and never averaged away.

### R8 clean censorship A/B, rung 4 of the fourth sweep

One window on the llama.cpp production stack with `bartowski/Qwen3.8-27B-GGUF` `Qwen3.8-27B-IQ4_XS.gguf` at 15.48 GB, the censored sibling of the production repack at the same quantizer and quant class, with weights-only differences. Frozen protocol against 72.68 fresh and the depth curve, plus the draft acceptance comparison, because the censored pack stores its MTP head at `Q4_0` and the repack may not. The window runs the turboq binary with production flags against the bartowski model, then restores the h76 profile through the closeout.

## End deliverables

The ladder table carries every rung with config, curve points, acceptance, and verdict. The window and recall frontier come per KV type. The final comparison runs against 76.41, 57.51, and 54.40 and ends with one recommendation: daily driver, big inputs, or neither. The untested list and the top follow-on close the report. Production must read verified restored in every path. Decision rows land in `decision.tsv` and receipts land in `results/hq20-hillclimb/`, committed and pushed per standing authorization.

## Running untested list

- DFlash2 with the quantized drafter. The launcher refuses `SPEC=dflash2` without `models/Qwen3.8-27B-DFlash2-W4A16/model.safetensors`, or the unquantized `Qwen3.8-27B-DFlash2`, and no such pack exists at `/home/jamie/models` or `/home/jamie/qwen-arm20/models`, which hold the same llama.cpp GGUFs. `prepare/fetch_dflash2.py` downloads the pack, and the brief gates this rung on the pack existing and does not authorize the download.
- `VLLM_SPEC_DECODE_ATTN` and `VLLM_SPEC_DECODE_ATTN_QMAX`, the split-KV verify kernel switch at `vllm/envs.py` line 219. The brief does not name it. The launcher sets it for `CTX=fast` and for `SPEC=dflash2 CTX=long`, so the mtp long-context arms run with it off. It is the top follow-on candidate because the verify kernel is the named mechanism.
- The turboquant KV dtypes and `int8_per_token_head` at `vllm/config/cache.py` lines 28 to 37. They fall outside the briefed R3 order.
