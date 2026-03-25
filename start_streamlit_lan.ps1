$ErrorActionPreference = "Stop"

$projectRoot = "G:\Order-Process-Automation"
$logDir = Join-Path $projectRoot "data"
$outLog = Join-Path $logDir "streamlit_lan_out.log"
$errLog = Join-Path $logDir "streamlit_lan_err.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Start-Process `
    -FilePath "python" `
    -ArgumentList @(
        "-u",
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8501"
    ) `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog

$started = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        Invoke-WebRequest -UseBasicParsing -Method Head -Uri "http://127.0.0.1:8501" | Out-Null
        $started = $true
        break
    } catch {
    }
}

if (-not $started) {
    Write-Error "Streamlit did not become reachable on port 8501."
}

Write-Output "LAN URL: http://192.168.68.104:8501"
