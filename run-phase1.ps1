# Run with: powershell -ExecutionPolicy Bypass -File .\run-phase1.ps1
param(
    [ValidateSet('simulation', 'llm')][string]$Mode = 'simulation',
    [ValidateSet('all', 'dev', 'test')][string]$Split = 'all'
)
$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\Arthur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Bundled Python not found. Select a working interpreter in VS Code and use the commands in PHASE1.md.'
}
$taskPreviousPath = $env:PYTHONPATH
Push-Location $PSScriptRoot
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    $taskOutput = 'results/phase1-' + $Mode + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    & $taskPython -m evidencepilot.security_eval --mode $Mode --split $Split --output $taskOutput
    if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed; see the error above.' }
} finally {
    $env:PYTHONPATH = $taskPreviousPath
    Pop-Location
}
