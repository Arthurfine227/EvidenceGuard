param([ValidateSet(2,4,8)][int]$Limit = 8)
$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\Arthur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskPreviousPath = $env:PYTHONPATH
Push-Location $PSScriptRoot
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    $taskOutput = 'results/phase3-dev-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    & $taskPython -m evidencepilot.phase3 --limit $Limit --output $taskOutput
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $taskPreviousPath
    Pop-Location
}
exit $taskExitCode
