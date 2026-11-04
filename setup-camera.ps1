$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) {
    py -3.12 -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12, then run setup-camera.ps1 again.' }
}
$requirements = 'backend\requirements-camera.txt'
& $pythonPath -m pip install -r (Join-Path $PSScriptRoot $requirements)
if ($LASTEXITCODE -ne 0) { throw 'Camera dependency installation failed.' }
& $pythonPath (Join-Path $PSScriptRoot 'scripts\download_pose.py') --variant full
if ($LASTEXITCODE -ne 0) { throw 'Full Pose model download failed.' }
Write-Host 'Setup complete. Start the backend with start-backend.ps1.'
