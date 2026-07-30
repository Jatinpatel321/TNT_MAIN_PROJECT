$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
Write-Host "[ADB Keep-Alive] Started. Refreshing tunnels every 10s. Press Ctrl+C to stop." -ForegroundColor Cyan

while ($true) {
    $devices = & $adb devices 2>&1
    if ($devices -match "device$") {
        & $adb reverse tcp:8000 tcp:8000 2>&1 | Out-Null
        & $adb reverse tcp:8082 tcp:8082 2>&1 | Out-Null
        & $adb reverse tcp:8083 tcp:8083 2>&1 | Out-Null
        Write-Host "$(Get-Date -Format 'HH:mm:ss') [OK] adb reverse tcp:8000 + tcp:8082 + tcp:8083 active" -ForegroundColor Green
    } else {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') [WAIT] No device found, retrying..." -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 10
}
