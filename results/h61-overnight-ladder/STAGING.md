# h61 staging, GPU untouched, SWA holds card

SwaHybridRung holds the GPU. Last status re-polling N13 measurement, waiting for N13 recall job.
No GPU work started. No server restarts. No nvidia-smi. No launcher writes.
Mac pid 34846 is frozen (Ts) by the active rung. Left frozen.

Read-only box check at staging (no timed arms, no inference):
- launcher /home/jamie/llama/llama-serve.sh carries SWA overrides
  --override-kv qwen35.attention.sliding_window=int:4096,qwen35.attention.swa_global_layers=int:13
- turboq binary present, orcarouter model present
- llama-watchdog.service inactive (sibling stopped per runbook)
- /health down (sibling mid-rung, expected)

Decode is the metric. Prefill is guard rail only.
Baseline headline. Fresh 74.00, 33k 50.42, 91k 40.81. Fresh floor 72.52.
Harness measure-h61.py does warmup discarded plus 5 timed, median decode headline,
median prefill guard, draft counters required, hygiene before and after.
Probes quality-probe.py and recall-probe.py both carry enable_thinking false.
Runner run-h61-arm.sh freezes 34846, stops watchdog, swaps launcher, waits for health,
verifies cmdline, runs fresh plus 33k plus 91k, then quality, then unfreezes.
SWA arms also run recall-probe at depth. Recall is load-bearing.

Queue is decode-ranked. h61 re-baseline, then draft KV q8_0, q4_0, tbq4_0,
then SWA unsettled only with reuse, then n-max 4 on draft winner,
then ngram-mod base plus matches, then ubatch, then p-min control,
then main TBQ at 91k only, then FA_ALL_QUANTS rebuild if room,
then leaner packs and co-residency optional last with per-instance decode only.
