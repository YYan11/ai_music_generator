$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectPython = "C:\Users\Jaslyn\anaconda3\envs\midigpt_env\python.exe"
$FallbackPython = "python"

Set-Location $ProjectRoot

$env:FIREBASE_LOCAL_AUTH_BYPASS = "1"

# Clear placeholder proxy settings that block cloud API calls such as Groq.
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:http_proxy -ErrorAction SilentlyContinue
Remove-Item Env:https_proxy -ErrorAction SilentlyContinue
Remove-Item Env:all_proxy -ErrorAction SilentlyContinue

$SelectedPort = $null
foreach ($CandidatePort in 8000..8010) {
    $PortInUse = Test-NetConnection -ComputerName 127.0.0.1 -Port $CandidatePort -InformationLevel Quiet
    if (-not $PortInUse) {
        $SelectedPort = $CandidatePort
        break
    }
}

if ($null -eq $SelectedPort) {
    throw "No free local port found from 8000 to 8010."
}

$env:PORT = "$SelectedPort"
Write-Host "Starting website on http://127.0.0.1:$SelectedPort"

if (Test-Path $ProjectPython) {
    & $ProjectPython web\backend\app.py
    exit $LASTEXITCODE
}

& $FallbackPython web\backend\app.py
exit $LASTEXITCODE
