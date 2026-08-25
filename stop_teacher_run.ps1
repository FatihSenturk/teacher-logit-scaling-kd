$targets = @()
$targets += Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.ProcessId -eq 8020 -or $_.ParentProcessId -eq 8020 }
$targets += Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.ProcessId -eq 51556 }
foreach ($p in $targets) {
    Write-Output "Stopping PID $($p.ProcessId): $($p.CommandLine)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Output "Done."
