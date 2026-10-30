# EvidenceGuard

Tool access and indirect prompt injection in LLM agents. A COMP7611 project at the **HKU School of Computing and Data Science**. The Python package retains its original name `evidencepilot`.

## Read or present the project

| Start here | Contents |
|---|---|
| [Current presentation](presentation/EvidenceGuard_HKU_CDS.pptx) | Updated 10-slide English Flash/Pro deck with speaker notes. Download and open in PowerPoint. |
| [Illustrated teammate report](TEAMMATE_GUIDE.html) | Chinese explanation v2.0 with principles, workflows, both models and limits. Download and open in a browser. |
| [Latest results](MODEL_COMPARISON_RESULTS.md) | Model comparison, case analysis and evidence links. |
| [Setup and reproduction](TEAM_SETUP.md) | Installation, offline tests and saved-score checks. |
| [Follow-up protocol](MODEL_COMPARISON_PROTOCOL.md) | Frozen model setup, spending guard and stopping rules. |

**Updated 2026-10-30.** Both current presentation and teammate report include Pro. The [original Flash-only deck](presentation/archive/EvidenceGuard_Flash_20261020.pptx) remains archived.

## Formal results

Each model has 20 fixed task IDs, three policies and clean/attacked conditions: **120 formal cases per model**. The combined 240 cases reuse the same 20 task IDs. They are not 240 independent tasks.

| Model | Policy | Clean task success | Attacked task success | Official attack-goal success |
|---|---|---:|---:|---:|
| Flash | None | 19/20 | 19/20 | 0/20 |
| Flash | Boundary | 20/20 | 20/20 | 0/20 |
| Flash | Scoped | 19/20 | 20/20 | 0/20 |
| Pro | None | 19/20 | 13/20 | 3/20 |
| Pro | Boundary | 19/20 | 19/20 | 0/20 |
| Pro | Scoped | 18/20 | 18/20 | 0/20 |

All attacked groups expose the payload in 20/20 cases. Official tools and scoring remain unchanged.

### Findings

- The boundary reminder improves the observed Pro baseline result on this fixed subset. Flash's zero baseline cannot demonstrate a defense benefit.
- Scoped includes the same reminder. It shows no additional attack reduction and fails a legitimate delegated task when the planner omits file tools.
- The official email-goal rule can miss a sent effect when an injected received message also matches its subject search. A **post-hoc secondary state diagnostic** finds 6/20 Pro baseline target-email effects, compared with official 3/20. The other five model/policy groups have zero. **6/20 is not official ASR or a pre-frozen primary result.**

Limits: small nonrandom, related tasks, one template and objective, one run per model, same vendor and different run dates. No concurrent Flash rerun or immutable weights. No general model ranking, statistical significance or zero-risk guarantee follows.

## Evidence and verification

- [Original Flash results](DOJO_RESULTS.md) and [integration details](DOJO_INTEGRATION.md).
- [Pro formal completion](results/pro-comparison-20261030/formal/manifest.json) and [raw formal groups](results/pro-comparison-20261030/formal/).
- [Comparison data and paired changes](results/pro-comparison-20261030/analysis/summary.json).
- [Secondary side-effect diagnostic](results/pro-comparison-20261030/effects.json).
- [Pro audit](results/pro-comparison-20261030/audit/audit.json) and [Flash audit](results/dojo-formal-audit-20261020/audit.json): 120/120 saved scores consistent in each run.
- [Local test logs](results/pro-comparison-20261030/checks/): 30 base and 8 integration/diagnostic tests passed.
- [Pro spending ledger](results/pro-comparison-20261030/budget-ledger.json): conservative peak-rate estimate RMB 16.43 including development, not the actual invoice.

Development cases, scripted controls and formal cases remain separate. Scripted providers verify software and do not count as real-model attacks. Original errors and recovery history remain intact.

## Local checks

Use Python 3.12 and follow [TEAM_SETUP.md](TEAM_SETUP.md) to install the locked environment. Then run from the repository root:

```powershell
.\.venv-dojo\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-dojo\Scripts\python.exe -m unittest discover -s tests_dojo -v
```

Reading records, local tests and saved-score verification need no model key. Fresh real-model experiments require credentials and can consume credits. Existing run directories refuse overwriting.

## Implementation and origins

- `src/evidencepilot/dojo_bridge.py`: native tool calls and policy checks.
- `src/evidencepilot/model_comparison.py`: Pro follow-up and spending guard.
- `src/evidencepilot/dojo_validate.py`: state restoration and official score audit.
- `src/evidencepilot/comparison_effects.py`: separate post-hoc diagnostic.

Tasks, simulated tools, scoring and the attack template come from [AgentDojo](https://github.com/ethz-spylab/agentdojo). This is a workspace subset, not a full leaderboard submission. Earlier adaptation uses [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent), with license and source records in `data/injecagent/`.

## Historical material

[Phase 1](PHASE1_RESULTS.md), [Phase 2](PHASE2_RESULTS.md), [Phase 3](PHASE3_RESULTS.md) and [Phase 4](PHASE4_RESULTS.md) document development, not extra independent formal samples. Earlier fact-verification prototype code remains separate.

Never commit API keys, `.env.local` or virtual environments. Tools are simulated, but the model API receives benchmark context. Reading access depends on the current repository visibility. Contributions require appropriate access and should use branches and pull requests.

