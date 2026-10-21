param([switch]$Check)
$ErrorActionPreference = 'Stop'
$taskPython = 'C:\Users\Arthur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskPreviousPath = $env:PYTHONPATH
Push-Location $PSScriptRoot
try {
    $env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
    if ($Check) {
        & $taskPython -m evidencepilot.setup_model --check
    } else {
        & $taskPython -m evidencepilot.setup_model
    }
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $taskPreviousPath
    Pop-Location
}
exit $taskExitCode
