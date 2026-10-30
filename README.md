# EvidenceGuard

Tool-using LLM security evaluation for COMP7611, HKU School of Computing and Data Science. The Python package retains its original name `evidencepilot`.

## Start here for teammates

**2026-10-30 update:** the Pro follow-up is complete. Read [second-model findings](MODEL_COMPARISON_RESULTS.md) and the [frozen process and budget protocol](MODEL_COMPARISON_PROTOCOL.md). Pro has 3/20 official baseline attack successes and 0/20 in both defense groups. A separate, explicitly post-hoc state diagnostic finds 6/20 baseline target-email effects. Scoped loses a legitimate delegated task and shows no extra security gain over the boundary reminder. The existing slide deck below covers the historical Flash run, not these new results.

- [Teammate setup and reproduction guide](TEAM_SETUP.md): access, installation, offline checks and optional paid runs.
- [Presentation with English speaker notes](presentation/EvidenceGuard_HKU_CDS.pptx): download and open in PowerPoint.
- [Detailed illustrated project guide](TEAMMATE_GUIDE.html): download and open locally in a browser.
- [Formal results and limitations](DOJO_RESULTS.md): 20 fixed tasks, 120 valid cases. No observed security gain over the baseline.

No API key is needed to read the saved results or run the local verification tests. This repository is private. The owner must invite each teammate before they can access these links or clone it.

The sections below retain the original prototype documentation. For the current security project, follow the teammate guide above.

Start with `START_HERE.md` for the current project status, delivery criteria and remaining milestones. Historical phase reports document pilot experiments rather than independent completed projects.

The frozen AgentDojo subset is now complete: see `DOJO_RESULTS.md` for the 120-case results and limitations, and `DOJO_INTEGRATION.md` for reproduction details. The remaining course milestone is the report and presentation.

## Security course experiments (EvidenceGuard)

The current course work extends the original demo with a separate security evaluation track:

- `PHASE1_RESULTS.md`: initial real-model baseline.
- `PHASE2_RESULTS.md`: tool protocol and defense comparison.
- `PHASE3_RESULTS.md`: pinned public-data adaptation, benign controls, token usage and limitations.
- `PHASE3.md`: methodology and reproduction commands.
- `PHASE4_RESULTS.md`: native function calling, stateful sandbox and effect-based scoring.
- `PHASE4.md`: fourth-stage threat model, permissions and reproduction commands.

The security runner uses simulated tools only. Its public-data adaptation is not an official benchmark score. Original multimodal-demo commands below remain separate.

EvidencePilot is an auditable starter project for multimodal claim verification. It demonstrates a real agent loop rather than a single prompt:

1. decompose a claim;
2. decide whether an image tool is needed;
3. retrieve evidence for each subclaim;
4. rate source provenance;
5. form a verdict while preserving uncertainty;
6. expose the complete tool trace.

The repository runs offline with a tiny demonstration corpus. It also supports any OpenAI-compatible chat-completions endpoint through environment variables.

## Quick start

From this directory, using Python 3.10 or newer:

```powershell
$env:PYTHONPATH = "src"
python -m evidencepilot.cli "COMP7608A is offered in Shanghai Block 4"
```

To inspect an image as part of the workflow:

```powershell
python -m evidencepilot.cli "This image was taken at the stated event" --image path\to\image.png
```

To save a machine-readable report:

```powershell
python -m evidencepilot.cli "Your claim" --output report.json
```

## Connect an LLM

Set the values shown in `.env.example` in your shell. Never commit an API key.

```powershell
$env:EVIDENCEPILOT_API_KEY = "..."
$env:EVIDENCEPILOT_BASE_URL = "https://your-compatible-endpoint/v1"
$env:EVIDENCEPILOT_MODEL = "your-model"
```

Without those variables, deterministic offline logic is used. With them, claim decomposition and evidence-grounded verdict generation use the configured model.

## Run tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Current scope

This is a deliberately small first milestone. The local evidence corpus makes tests reproducible, while interfaces are separated so the following components can be added without rewriting the agent:

- live web/news search;
- OCR and reverse-image retrieval;
- a learned manipulation detector;
- persistent state and retry policies;
- benchmark datasets and experiment tracking;
- a browser UI.

The current output must not be presented as professional fact-checking. Source quality and image authenticity still require human review.

