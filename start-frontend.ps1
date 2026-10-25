$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'frontend\ai-snooker')
try {
    if (!(Test-Path 'node_modules')) {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
    }
    npm.cmd run dev
    if ($LASTEXITCODE -ne 0) { throw 'Frontend stopped with an error.' }
} finally { Pop-Location }
