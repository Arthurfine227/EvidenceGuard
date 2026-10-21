param([ValidateRange(1,4)][int]$LimitTasks = 4)
$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\Arthur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskPreviousPath = $env:PYTHONPATH
Push-Location $PSScriptRoot
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    $taskOutput = 'results/phase2-dev-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    & $taskPython -m evidencepilot.phase2 --limit-tasks $LimitTasks --output $taskOutput
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $taskPreviousPath
    Pop-Location
}
exit $taskExitCode
