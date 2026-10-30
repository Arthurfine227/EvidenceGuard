# Second-model follow-up protocol

## Purpose

Compare `deepseek-v4-pro` with the historical Flash results on exactly the same task/attack/policy matrix. The goal is to test model dependence, not to search for an attack-success headline. Do not modify the original Flash results or pool the runs as independent tasks.

The user authorized up to RMB 100 for this follow-up on 2026-10-30. This includes development checks and formal requests. The runner leaves RMB 5 unused and records reservations before sending requests.

## Fixed design

- AgentDojo package 0.1.35, workspace benchmark v1.2.2.
- Original plan hash: `238b6af1347d20efa6c721faeb3ed1e67bb6c96ce5288615642139f2760d8242`.
- Development tasks: 0 and 1. Formal tasks: 2 through 21.
- Policies: none, boundary, scoped. Same prompts and unchanged `dojo_bridge.py`.
- Conditions: clean and `important_instructions_no_names`, official injection_task_0.
- Main model: at most 12 turns, 1024 output tokens per call, temperature 0, thinking disabled.
- Scoped planner: same second model, at most 512 output tokens. Switching models changes both the main agent and the planner.
- Fixed group order follows the historical experiment. No task replacement, attack search, prompt tuning or utility-based reruns.
- Official tools, simulated environment and utility/security scoring remain unchanged.

The follow-up uses the previously evaluated tasks. It is a fixed-protocol replication, not a newly untouched test set. The original formal tasks were held out from the original development work, but their historical outcomes are now known.

## Process

```text
Verify original plan, dependencies and upstream source/data hashes
    |
Freeze new model identity, budget and protocol
    |
Run 12 development cases on tasks 0 and 1
    |
Check compatibility without tuning for scores
    |
Run 120 formal cases on tasks 2 through 21
    |
Restore saved final states and recompute official scores offline
    |
Compare six paired task groups with the historical Flash run
    |
Publish records, limits and accounting estimates
```

The model API is real and paid. Calendar, email and cloud tools only affect the official simulated environment. The API key stays in the existing local configuration. The runner constructs a new provider with the Pro model rather than overwriting `.env.local`.

## Budget method

Official source checked on 2026-10-30: <https://api-docs.deepseek.com/zh-cn/quick_start/pricing/>.

For Pro, use peak cache-miss input RMB 9 per million tokens and output RMB 27 per million tokens, even when the actual time is off-peak or input receives a cache discount. Before each request, reserve using twice the UTF-8 JSON byte count plus 8192 input tokens for serialization overhead, together with the requested output-token cap. Reject the next call if this exceeds RMB 95 in the shared ledger.

When token usage arrives, settle that reservation using the conservative peak rates. A failed request without usage retains its full reservation. The estimate depends on the verified pricing and conservative serialization bound. It is a local guard, not a provider-enforced spending cap or a complete account invoice. Other programs using the same account are outside the ledger.

## Errors and recovery

Stop on the first API, adapter, dependency or budget error. Preserve the partial phase and its false completion flag. Never treat an error as a safe case. Any recovery must explicitly identify the original error and incomplete tasks. A failed utility score is an outcome, not a reason to rerun.

The development gate checks execution compatibility, not task/attack performance. A valid model-induced utility failure or attacker success does not invalidate the gate. All development records remain separate from formal scores.

## Commands

These commands consume model credits. Existing phase paths intentionally refuse overwriting. Do not rerun them casually.

```powershell
.\.venv-dojo\Scripts\python.exe -m evidencepilot.model_comparison --root results/pro-comparison-20261030 --phase dev --cap-rmb 100
.\.venv-dojo\Scripts\python.exe -m evidencepilot.model_comparison --root results/pro-comparison-20261030 --phase formal --cap-rmb 100
```

After formal completion, these commands do not call the model API:

```powershell
.\.venv-dojo\Scripts\python.exe -m evidencepilot.dojo_validate --run results/pro-comparison-20261030/formal --output results/pro-comparison-20261030/audit
.\.venv-dojo\Scripts\python.exe -m evidencepilot.comparison_report --root results/pro-comparison-20261030 --output results/pro-comparison-20261030/analysis
```

## Interpretation

Compare defense versus baseline within each model before discussing model differences. A zero baseline attack count cannot demonstrate reduced attack success. Tool-name authorization cannot validate recipients or file arguments. Blocked calls may be legitimate optional actions. Record their context.

Model services run at different dates. There is no simultaneous Flash rerun, immutable weight identifier, randomized order or repeated seed. This is a same-vendor comparison, not cross-family or cross-vendor validation. Small nonrandom, related tasks limit statistical claims. No outcomes should be selected to make a defense look effective.

The existing presentation covers the historical Flash experiment. Consult the new comparison report before presenting combined findings. Do not silently attribute second-model results to the earlier slide deck.
