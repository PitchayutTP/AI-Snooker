$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) {
    py -3.12 -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12, then run setup-camera.ps1 again.' }
}
& $pythonPath -m pip install -r (Join-Path $PSScriptRoot 'backend\requirements-camera.txt')
if ($LASTEXITCODE -ne 0) { throw 'Camera dependency installation failed.' }
& $pythonPath (Join-Path $PSScriptRoot 'scripts\download_pose.py')
if ($LASTEXITCODE -ne 0) { throw 'Pose model download failed.' }
Write-Host 'Setup complete. Start the backend with start-backend.ps1.'
