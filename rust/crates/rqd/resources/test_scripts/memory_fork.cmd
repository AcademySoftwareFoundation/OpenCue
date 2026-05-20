@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference='Stop'; ^
Write-Host 'Parent process starting...'; ^
$main = New-Object byte[] (10MB); ^
Start-Sleep -Seconds 10; ^
$childScript = 'Write-Host ''Child process starting...''; $a = New-Object byte[] (5MB); Start-Sleep -Seconds 10; $b = New-Object byte[] (5MB); Write-Host ''Child process allocated ~5MB, sleeping...''; Start-Sleep -Seconds 60'; ^
$child1 = Start-Process -FilePath powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command', $childScript) -PassThru; ^
$child2 = Start-Process -FilePath powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command', $childScript) -PassThru; ^
Write-Host ('Child PIDs: {0}, {1}' -f $child1.Id, $child2.Id); ^
Write-Host 'All processes running. Parent will wait before exiting.'; ^
Start-Sleep -Seconds 60; ^
Stop-Process -Id $child1.Id,$child2.Id -ErrorAction SilentlyContinue; ^
Write-Host 'Script completed'"
