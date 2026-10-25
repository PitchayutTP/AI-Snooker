param([string]$DatabaseUrl = '')
$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Run setup-camera.ps1 first.' }
if ($DatabaseUrl) { $env:DATABASE_URL = $DatabaseUrl }
if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    throw 'PostgreSQL configuration is required. Pass -DatabaseUrl or set DATABASE_URL before starting.'
}
Push-Location (Join-Path $PSScriptRoot 'backend')
try {
    & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw 'Backend stopped with an error.' }
} finally { Pop-Location }
