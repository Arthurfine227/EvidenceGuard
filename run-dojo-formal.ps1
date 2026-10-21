$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv-dojo\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'AgentDojo environment not found. See DOJO_INTEGRATION.md.' }
Push-Location $PSScriptRoot
try {
    $taskOutput = 'results/dojo-formal-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    & $taskPython -m evidencepilot.dojo_formal --plan evaluation/dojo-workspace-v1.2.2-plan-20261020 --output $taskOutput
    $taskExitCode = $LASTEXITCODE
} finally { Pop-Location }
exit $taskExitCode
