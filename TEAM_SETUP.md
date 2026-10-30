# EvidenceGuard teammate guide

Latest release: the current 10-slide presentation and Chinese illustrated report both include the 2026-10-30 Pro follow-up. Read `MODEL_COMPARISON_RESULTS.md` first and `MODEL_COMPARISON_PROTOCOL.md` for audit/reproduction commands. Local tests now include 30 base and 8 integration/diagnostic tests.

This is a tool-using LLM security evaluation project for COMP7611 at HKU CDS. The original Flash experiment compares three policies on a fixed AgentDojo workspace subset. It contains 20 task IDs and 120 valid cases, not 120 independent tasks. All Flash policies have zero observed attack successes, so that historical run does not establish an additional security benefit. The Pro follow-up linked above has different outcomes and a separate 120-case record.

## 1 Get access and view the materials

Repository: <https://github.com/Arthurfine227/EvidenceGuard>. If public, reading and downloading need no invitation or account. If access is restricted, request an invitation from the owner and accept it using the correct GitHub account. Contributions still require appropriate permissions.

1. Open the repository link. If GitHub denies access, confirm its current visibility with the owner.
2. For restricted access or code collaboration, send your username to the owner and accept the invitation.
3. Read `DOJO_RESULTS.md` and this guide on GitHub.
4. Download `presentation/EvidenceGuard_HKU_CDS.pptx` and open it in PowerPoint. This is the current 10-slide Flash/Pro deck. Speaker notes contain the English script and sources. Add actual team names before presenting. The Flash-only historical deck is in `presentation/archive/`.
5. Download `TEAMMATE_GUIDE.html` and open it in a browser for the illustrated explanation. GitHub normally shows HTML source rather than rendering the report.

For the HTML report's relative evidence links to work, keep the whole repository directory. The report text and diagrams work when the HTML file is shared alone.

You can use **Code > Download ZIP** if you only want to read the project. Unzip it before opening files. For code contributions, use Git clone instead.

## 2 Clone the project

Install Git and Python 3.12 from their official sources if needed. Python 3.12 is the tested interpreter for the formal environment. On Windows, open a PowerShell terminal in the directory where you want the project:

```powershell
git clone https://github.com/Arthurfine227/EvidenceGuard.git
cd EvidenceGuard
```

Complete GitHub authentication if prompted. A private-repository error or 404 usually means the invitation is not accepted, the signed-in account is wrong, or the account has no access. Do not paste access tokens into chat or commit them to files.

## 3 Install the formal evaluation environment

These commands run in PowerShell, not inside Python's `>>>` prompt. They require network access to download dependencies, but do not call the model API. Run them from the repository root:

```powershell
py -3.12 -m venv .venv-dojo
.\.venv-dojo\Scripts\python.exe -m pip install -r evaluation/dojo-workspace-v1.2.2-plan-20261020/requirements.lock.txt
.\.venv-dojo\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
```

The lock file contains the recorded dependencies. Do not upgrade packages if you want to compare with the saved run. We call the environment's Python explicitly, so there is no need to activate a PowerShell script or relax the execution policy. Recreate the environment locally rather than copying someone else's `.venv-dojo` folder.

On macOS/Linux, create the environment with `python3.12 -m venv .venv-dojo` and replace `.\.venv-dojo\Scripts\python.exe` with `./.venv-dojo/bin/python`. These platform substitutions are guidance, not a claim that this project has been validated on those operating systems.

## 4 Verify locally without an API key

```powershell
.\.venv-dojo\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-dojo\Scripts\python.exe -m unittest discover -s tests_dojo -v
```

The current recorded suite contains 30 base tests and 8 integration/diagnostic tests. Controlled providers are scripted checks, not additional real-model attack experiments. The original Flash release had 28 plus 6 tests.

Recompute the saved formal scores without sending any model requests:

```powershell
.\.venv-dojo\Scripts\python.exe -m evidencepilot.dojo_validate --run results/dojo-formal-completed-20261020 --output results/teammate-local-audit
```

Use a new output directory for every audit. The command refuses an existing directory rather than overwriting it. Expected fields in `audit.json`:

```json
{
  "checked_cases": 120,
  "score_recomputation_passed": true,
  "issues": [],
  "api_calls": 0
}
```

This checks reproducibility of official scoring from saved states and traces. It does not independently establish semantic correctness or reproduce new model behavior.

## 5 Inspect real execution evidence

- `src/evidencepilot/dojo_bridge.py`: native tool calling and policy enforcement.
- `results/dojo-formal-completed-20261020/none-none/cases.json`: task 6 queries the calendar and creates a lunch event. The saved calendar grows from 26 to 27 events.
- `results/dojo-formal-completed-20261020/scoped-important_instructions_no_names/cases.json`: task 18 rejects a reasonable optional calendar check and still completes the user task. This is not an intercepted attack.
- `results/dojo-formal-analysis-20261020/summary.json`: six groups of 20 cases, model response names and usage.
- `results/dojo-formal-audit-20261020/audit.json`: recorded full offline score audit.

The original interrupted run remains in `results/dojo-formal-20261020`. Do not treat it as a complete run. The completed view preserves the provenance of one error retry and thirteen previously unrun cases. The frozen plan is a pre-run snapshot, so its completion flag intentionally remains false. The completed view's manifest records final completion.

## 6 Optional new real-model experiments

You do not need to rerun paid experiments for reading, presenting or verifying the saved results. A new run requires your own compatible API configuration and can consume credits. Do not share the owner's key.

Read `DOJO_INTEGRATION.md`, `setup-model.ps1` and `src/evidencepilot/dojo_formal.py` before running anything. Use a new result location and preserve the existing records. The standard wrapper targets the original run location and is not a generic rerun button.

The experiment requested `deepseek-v4-flash`, while the provider returned `deepseek-flash`. No immutable backend weight identifier is available. Even with the same code and configuration, a future service response may differ. Local saved-score verification and a fresh model experiment are different forms of reproduction.

Only the tools are simulated. The real model API receives benchmark context. Never add real personal data or secrets to a task. `.env.local`, virtual environments and local release copies are excluded from Git. Local audit output does not need to be committed.

## 7 Team collaboration

For changes, create a branch and open a pull request instead of overwriting existing evidence:

```powershell
git switch -c your-branch-name
# Edit only the files relevant to your contribution.
git add path/to/changed-file
git commit -m "Describe your change"
git push -u origin your-branch-name
```

Use a branch name that describes your actual task. Keep experimental records unchanged. Do not commit model keys, `.venv-dojo`, screenshots showing credentials, or unnecessary local reruns. The project currently keeps code and simulated experiment traces private. Repository access does not automatically authorize publishing them elsewhere.
