$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logFile = "phase0_extended_ablation_console.log"

Add-Content -Path $logFile -Value "=== RESUME: baseline (61.73%), gate (57.83%), g2g_kl (61.93%), logit_std (58.08%), adaptive_t (61.63%) done; continuing ctkd (final AffectNet+8 run) ==="
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_phase0_full_ablation_affectnet8.ps1" -StartAt ctkd 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "AffectNet+8cls grid (resume) failed." }

Add-Content -Path $logFile -Value "=== RAF-DB multi-seed validation ==="
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_phase0_rafdb_multiseed.ps1" 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "RAF-DB multiseed failed." }

Add-Content -Path $logFile -Value "=== Extended Phase 0 ablation (this machine) complete ==="
