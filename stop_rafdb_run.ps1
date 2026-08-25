$targets = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.ProcessId -eq 50768 -or $_.ParentProcessId -eq 50768 }
foreach ($p in $targets) {
    Write-Output "Stopping PID $($p.ProcessId): $($p.CommandLine)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Output "Done."
