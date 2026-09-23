# Overnight rung queue

Assembled 2026-09-23 from the fork knob sweep and the card class playbook. One rung per attempt, keep or revert against the frozen protocol, decision rows appended per attempt. Production at queue time is the turboq qwen35 build aaa66a5 at q8_0 KV with `--spec-type draft-mtp` and n-max 3, 74.00 fresh median and 50.42 at 33k (h59).

Accept a rung when fresh stays within 2 percent and a depth point improves past noise, or when the window grows without an at-depth cost above 10 percent. Run the quality guardrail and, for any SWA rung, the beyond-window recall test before keeping.

## Queue order

1. SWA hybrid sweep. `--override-kv qwen35.attention.sliding_window=int:4096` with `swa_global_layers` at 8, then 4 and 13 at depth, then window at 2048 and 8192 with globals at 8. Recall test is load-bearing. Runs only if SwaHybridRung has not already settled these values.
2. Draft KV types, independent of main KV. `-ctkd` and `-ctvd` at f16, then q8_0, then tbq4_0 if the parser accepts. Depth-first measurement. The memory saving may unlock n-max 4 without the whole-cache cost.
3. n-max 4 on the winning draft KV, at 49k and 64k first, then a fit gate at 98k.
4. ngram-mod stacking. `--spec-type draft-mtp,ngram-mod --spec-ngram-mod-n-min 24` with n-match at 4, 8, 16 and n-max at 3 and 4. Expect gains to depend on repetitive content, so measure on the standard prompts only.
5. Ubatch sweep at 98k. ub at 64, 128 and 384 with b equal to ub and b at 512.
6. Main TBQ4 and TBQ3 KV at 91k fill only. The depth extreme is the one place their theory predicts a win.
7. RotorQuant KV types, planar3_0 and iso3_0 first. Requires a rebuild with `GGML_CUDA_FA=ON` and `GGML_CUDA_FA_ALL_QUANTS=ON`. Budget it as its own sub-phase.
8. p-min 0.60 as a single control run on the winning draft path only.

## Do not touch

`LLAMA_ATTN_ROT_DISABLE`, wrong architecture. `GGML_CUDA_FORCE_MMQ=1` and `GGML_CUDA_GRAPH_OPT=1`, measured noise here. p-min as a speed lever, measured minus 10.8 percent. n-max 2, measured minus 3.1 percent. Whole-cache q4_0 as a speed lever, it is the documented context-maximum option instead.

## Late sweep additions

From the env and field sweep, 2026-09-23. These move to the top of the queue.

1. **Explicit draft KV types.** qwen38-mtp issue 39 records that `-ctkd` and `-ctvd` do not inherit from `-ctk` and `-ctv` and default to f16. Production therefore runs an f16 draft cache today. Sweeping the draft cache to q8_0 and then q4_0 while keeping the main cache at q8_0 is cheap and likely to pay. Source: [issue 39](https://github.com/sudoingX/qwen38-mtp/issues/39).
2. **Small-KV prefill fix.** The same issue documents a silent trap where stock builds run q5_0 and q5_1 flash-attention prefill on CPU, collapsing prefill from 1492 to 41.5 t/s with no error. Upstream [PR 27140](https://github.com/ggml-org/llama.cpp/pull/27140) adds vectorized dequantization that restores it. Any q5_x or mixed-KV rung needs a build containing that fix and a prefill measurement, because decode-only checks cannot see the trap.
3. **ngram-mod parameters.** The community comment on PR 27140 reports about plus 27 percent on code and math with `--spec-type draft-mtp,ngram-mod --spec-ngram-mod-n-min 16 --spec-ngram-mod-n-max 64`. Prefer these parameters to the n-min 24 guess in the original queue.

## Methodology overrides

Five timed samples after a discarded warmup per rung, not three. Issue 39 shows a three-prompt median moving 15 percent where the five-run mean moved 1.6. Measure prefill and decode at every point. Run a fit gate before timed arms and record residency before and after. Reject a row on any crash, CPU fallback, missing draft counters or quality failure. Never classify a crash as noise.

## Second field sweep additions

From two r/LocalLLaMA and r/LocalLLM config threads, 2026-09-23. All untried on this card.

1. **ngram-map-k4v stacking.** `--spec-type draft-mtp,ngram-map-k4v --spec-ngram-map-k4v-size-n 16 --spec-ngram-map-k4v-size-m 24 --spec-ngram-map-k4v-min-hits 1`. A different ngram variant than the ngram-mod we measured as noise. One user reports it as summarization tuned and recommends dropping it for agent use, so measure on both prompt classes.
2. **Mixed KV types.** `-ctk q8_0 -ctv q5_1`. We have only tested symmetric pairs. One config runs this at 119k context.
3. **q4_1 KV at depth.** One user runs 170k with Q4_1 KV on a 24GB card. Untried dtype, sits between q4_0 and q5_1 in the memory tables.
4. **exllamav3 with tabbyAPI.** A whole engine class we have never run. Reported as steadier decode and prompt processing than llama.cpp at agent workloads, with `--draft-cache-mode Q4` for a quantized draft cache, which is exactly what our fork bug blocks, and `sysmem_kv_cache` eviction of old blocks to system RAM for subagent workloads. Rasekov runs 256k with Q8 KV at 4bpw.
5. **NInfer-3090 fork.** Reported 57 t/s at 125k and one user reports poor KV accuracy on a coding agent, so it needs a quality gate before any speed claim.
6. **ik fork Hadamard KV.** `-ctk q4_1 -ctv q4_1 -khad -vhad` on ik_llama.cpp. The Hadamard rotation family behind TBQ in a different fork, unmeasured here.
7. **Agent behavior rungs, a new category.** Two users report Qwen3.8 overthinking and failing tool calls under default harness settings. The froggeric qwen3.8 chat template, `--reasoning-budget`, `--reasoning-preserve` and `chat-template-kwargs reasoning_effort` are all untested behavior levers and matter more than t/s for our agentic use.

## Field-note additions, alexander-ollman qwen3.8-on-rtx3090

From the 2x3090 field writeup, 2026-09-23. Its llama.cpp numbers are below ours, but three findings transfer directly.

1. **fp8 KV is the quality-safe cache.** Their per-token-likelihood instrument finds fp8 indistinguishable from bf16 to 150K with 100 percent retrieval at 147K, and 4-bit cache "costs something real". This matches our recall failure with q4_0 past 150 to 183k. Run SWA8 with q8_0 KV as the quality-first profile and map its ceiling and recall. Expected window around 160k with exact recall, against our 196k with corruption past 150k.
2. **Swift-Qwen3.8-27B swap.** The UkisAI fine-tune halves thinking tokens at equal answers, 37 and 37 on the problems where neither hit the ceiling, and cuts a 36-task coding set from 9.6 to 5.5 hours. For agentic use that is bigger than any t/s lever left. Requires a model download and our quality harness plus the compaction probe.
3. **DFlash2 on the turboq fork.** We burned DFlash2 on the old upstream stack at 46.5 t/s. The fork carries dflash CUDA kernels and the writeup's 212 t/s row is DFlash2 at k=7. Single-consumer case is where DFlash2 wins per their concurrency caveat. Untested combination here.
4. Their community patched vLLM reached 167.8 before DFlash2, from a smarter verify kernel, a 4-bit output head and a trimmed draft vocabulary, and it refuses checkpoints that do not match its assumptions. Same family as the HyperQwen patches we could not fit at 20GB. Record only.

## Third field sweep additions, EXL3 and the trellis quant class

From the Yume_X EXL3 tier map, 2026-09-23, cross-checked against the exllamav3 reports from the earlier config threads. This is a different engine and quant class, not a GGUF variant, so it is a look-first item rather than a flag rung.

1. **What it is.** EXL3 uses trellis coding with a Hadamard transform so rounding error spreads across each weight vector instead of stacking per weight. The independent teacher-logit panel puts EXL3 4bpw 0.004 nats from BF16 against FP8 at 0.002 and NVFP4 at 0.06. Near-FP8 quality at roughly half the file size is the claim worth testing.
2. **The rows bracketing our 20GB card.** The 16GB tier runs Qwen3.8-27B at 3.0 bpw with the built-in MTP head at about 55 tok/s code decode with 110k context on a 16GB A5000. The 24GB tier runs 3.5 bpw plus a DFlash2 5.0 bpw drafter at 94 to 150 tok/s with the full 262k resident on a 22GB budget. Our card sits between those tiers.
3. **The drafter insight transfers directly.** Their quantized drafter cut draft weight reads from 16 bit to 5 and added 33 percent end to end. This is the same lesson as our own draft-KV work but applied to drafter weights, and it is a different lever.
4. **Engine notes from the field.** The exllamav3 and tabbyAPI reports describe steadier decode at depth and steadier prompt processing than llama.cpp under harness load, with sysmem_kv_cache eviction of old blocks to system RAM for subagent workloads. That eviction class is the adaptive streaming idea from the first sweep.
5. **Do not confuse with TurboQuant.** The TBQ KV family we measured is a cache compression. EXL3 is a weight compression. They compose rather than compete.

Run order for a future card session. Check the turboderp/Qwen3.8-27B-exl3 branches for a 3.0 and 3.5 bpw pack with the MTP head, stand up tabbyAPI per the earlier exllamav3 rung, and measure the frozen protocol plus the recall frontier against whatever the GGUF stack is producing that day.

## Fourth field sweep additions, checkpoint portability

1. **Test the standard censored Qwen3.8-27B on the slim-20gb stack.** This converts the fork's claim from works on the leminkozey uncensored checkpoint to works on the model class. Prerequisite is a censored packed checkpoint, a W4A16 or AWQ AutoRound pack, either downloaded or produced by the fork's own prepare pipeline against stock weights. The known GGUF-side expectation is that the standard model runs about 9 percent slower than the uncensored repack at production shape, measured at 66.15 against 72.68 in decision.tsv h47.
2. **Run the head and vocab calibration on the second checkpoint.** This closes the one stated limitation of the rewrite, that its preparation tooling was calibrated to the uncensored checkpoint. Record the calibration provenance the same way commit 3 does.
3. **Acceptance.** The fast path engages on the second checkpoint, the memory trace shows the same single-read and early-binding behavior, and the fresh and 33k points land within 10 percent of the uncensored stack's numbers at the same shape. Any divergence gets recorded as a checkpoint-specific finding rather than averaged away.
4. **The clean censorship A/B, and it is now byte-exact.** Fetch the censored pack at the PREVIOUS revision, not `main`, and the layout confound disappears entirely:

   ```
   hf download bartowski/Qwen3.8-27B-GGUF --revision f0eec4a4bb4975114a030d048952d83c0a53c034 \
     --include "Qwen3.8-27B-IQ4_XS.gguf" --local-dir ./
   ```

   That revision's file is still fetchable, HTTP 200, `x-linked-size` 15,567,824,480 bytes, etag `c2ae2b018f967370087c196c86d6811b2340ec19138a3752252ade5fbd1f4786`. Its tensor byte histogram is identical to our production file, tensor for tensor:

   | type | old-revision censored | our uncensored |
   |---|---|---|
   | IQ4_XS | 12,886,097,920 | 12,886,097,920 |
   | Q6_K | 1,524,633,600 | 1,524,633,600 |
   | Q8_0 | 802,160,640 | 802,160,640 |
   | Q4_0 | 238,878,720 | 238,878,720 |
   | F32 | 105,058,304 | 105,058,304 |
   | **total** | **15,556,829,184** | **15,556,829,184** |

   Its MTP block `blk.64.*` is the same fifteen tensors at the same types, eight of them Q4_0, exactly as ours. File totals differ by 672 bytes, which is metadata only. So this is the clean A/B the earlier plan could not reach: same quantizer, same quant type, same tensor layout, same draft-block precision, differing only in the weights. It settles whether censorship costs speed and nothing else, against 76.41 fresh and the 33k and 91k points.

   The `main` revision, 15,475,951,328 bytes, sha256 `4b927360fa7c4aa41a734302f0795ca45df0e8b8a258bc76cc5fbf9d98a484db`, is the NEW computed layout and is a separate second question: whether bartowski's computed layout beats the standard layout at the same quant type. Run it only after the censorship A/B, and do not let the two share a conclusion. Its license is unspecified in repo metadata, record that as unverified.

   The draft-head question is CLOSED: our GGUF already stores its whole MTP block at Q4_0 (see the section below), so it is not a variable in either comparison.

5. **The censored vLLM arm, now cheap.** `dbirks/Qwen3.8-27B-W4A16-AutoRound`, license apache-2.0, base_model `Qwen/Qwen3.8-27B`, 19,472,769,333 bytes used storage. This is the stock-weight sibling of our own uncensored pack and the evidence is byte-level: it ships the identical seven-shard layout `model-00001..00007.safetensors` with shard sizes 3211003472, 3195027104, 3195027104, 3217442568, 699275200, 2542807272, 2542796896, which match ours on shards 1 to 5 exactly and match ours on 6 and 7 as the pre-embed-quant halved pair our tree still carries as `.bak_embed` and `.bak`. Its `model_extra_tensors.safetensors` is 849,400,392 bytes, byte-identical in size to ours, and its quantization ignore list is the same shape as ours, keeping `lm_head`, `mtp.fc` and all `mtp.layers.0.*` in floating point. So the censored arm needs only the three steps we have already run once on the uncensored base: `prepare/quant_lm_head.py`, `prepare/quant_embed.py` and `prepare/build_draft_vocab.py`. No AutoRound pass, no 51.75 GiB stock download. Then serve it on the slim-20gb stack at the winning shape and compare fresh and 33k against 84.69 and 24.79.

6. **Quantize the fork's BF16 MTP module and measure it for speed.** The vLLM checkpoint's MTP module is BF16 where the GGUF's is Q4_0, so the fork rereads 810 MiB of draft weights per draft forward where the llama.cpp stack rereads roughly a quarter of that. `prepare/quant_mtp.py /path/to/checkpoint --bits 8|4 [--keep-fc]` is already written, already validated, and its own docstring records "Measured acceptance change: int8 none". It was run once during the full-VRAM ladder for fitting, did not make the stack fit, and the released checkpoint went back to BF16, so it has never been benchmarked for speed. Cost class is checkpoint-reprepare plus one window. Run it on a COPY of the checkpoint, not in place, since it is the only copy. Note it asserts all seven mtp linears live in one shard and aborts otherwise, which forces `--keep-fc` if the shard splits.

## Draft-head precision, closed

Measured this session by reading `model_extra_tensors.safetensors`'s header only, and the production GGUF's tensor table, no weights loaded:

- **vLLM checkpoint `/home/jamie/models/q38-lemin`:** 15 tensors, every one BF16, 849,398,784 bytes, 810 MiB, 424,699,392 parameters. `model-extra-tensors` includes `mtp.fc` [5120,10240] and one full decoder layer, `q_proj` [12288,5120], `k`/`v_proj` [1024,5120], `o_proj` [5120,6144], `gate`/`up`/`down_proj` [17408,5120]. Kept in floating point by the recipe, per the checkpoint's own README.
- **Production GGUF `orcarouter-uncensored-IQ4_XS.gguf`:** the MTP block is `blk.64.*`, and its eight Q4_0 tensors are `attn_k`, `attn_output`, `attn_q`, `attn_v`, `ffn_down`, `ffn_gate`, `ffn_up` and `nextn.eh_proj`. `nextn.enorm`, `hnorm`, `shared_head_norm` are F32, as norms are. So the whole draft block is already Q4_0 on the llama.cpp side.

The consequence is a correction to an earlier hypothesis in this queue: the GGUF's Q4_0 MTP head does **not** explain a draft-acceptance difference against the vLLM stack, because both paths quantize it the same way relative to their own formats. The real asymmetry is that the fork leaves 810 MiB BF16 on the vLLM side while llama.cpp reads about a quarter of that. The acceptance difference between the two stacks, 66.0 percent at vLLM k=3 fresh against roughly 70 percent on llama.cpp at n-max 3, is therefore a draft-vocabulary and verify-path question, not a draft-precision one.
