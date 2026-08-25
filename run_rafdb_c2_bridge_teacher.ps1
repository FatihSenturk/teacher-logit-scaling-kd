param(
    [int]$MaxRetries = 4,
    [int]$RetryDelaySeconds = 20
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-20: Phase C2 -- bridge/matched-pair teacher.
#
# Trains a VAE-head teacher with Primary's EXACT recipe
# (configs/RAFDB_posterv2_vae_recipe_seed1.yaml differs from Primary's
# RAFDB_posterv2_vich_recipe.yaml by exactly two lines: vae_head/vich_head).
# Isolates head architecture as the single variable behind VAE9182's teacher-ECE
# advantage. Pre-registered decision (measured by Phase C3 after this finishes):
#   fold-3 15-bin ECE ~0.015 (NLL-optimal T* ~1.0)   -> HEAD attribution
#   ~0.038 (T* ~1.3, over-confident like VICH teachers) -> RECIPE/augmentation
#
# SOLO GPU ONLY: main_encoder.py hardcodes cuda:0 and has no device override, so
# this must NOT run alongside any student-KD GPU work (launch only after Phase A
# seed replicates AND Phase B3 have freed the card). Expect ~8-9h for 300 epochs
# (empirically grounded: Primary's own identical-recipe run took ~8.4h).
#
# Unlike train_rafdb_kd.py, main_encoder.py SUPPORTS --resume (restores model/
# optimizer/schedule/scaler and continues from the saved epoch). On a crash we
# resume from the last.pt of a logdir THIS run created -- never an older
# teacher's checkpoint -- by snapshotting pre-existing logdirs before launching.

$Config = "RAFDB_posterv2_vae_recipe_seed1.yaml"
$TeacherLogDir = "results\teacher_logs\RAFDB\POSTERv2"

if (-not (Test-Path (Join-Path "configs" $Config))) {
    Write-Host "ERROR: configs\$Config not found."
    exit 1
}

# Snapshot logdirs that already exist, so retry-resume only ever targets a dir
# created by THIS run (guards against resuming an unrelated old teacher).
$preExisting = @()
if (Test-Path $TeacherLogDir) {
    $preExisting = @(Get-ChildItem -Path $TeacherLogDir -Directory | Select-Object -ExpandProperty FullName)
}

function Get-OurNewestLastPt {
    if (-not (Test-Path $TeacherLogDir)) { return $null }
    $ourDirs = Get-ChildItem -Path $TeacherLogDir -Directory |
        Where-Object { $preExisting -notcontains $_.FullName }
    $lastPts = foreach ($d in $ourDirs) {
        $p = Join-Path $d.FullName "last.pt"
        if (Test-Path $p) { Get-Item $p }
    }
    if (-not $lastPts) { return $null }
    return ($lastPts | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    $cmd = @("main_encoder.py", "--c", $Config)
    $resumeFrom = $null
    if ($attempt -gt 1) {
        $resumeFrom = Get-OurNewestLastPt
        if ($resumeFrom) {
            $cmd += @("--resume", $resumeFrom)
            Write-Host "[c2_bridge] Resuming from: $resumeFrom"
        } else {
            Write-Host "[c2_bridge] No checkpoint from this run yet -- restarting fresh."
        }
    }

    Write-Host ""
    Write-Host "########## C2 BRIDGE TEACHER, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd | Out-Host
    $exitCode = $LASTEXITCODE
    Write-Host "[c2_bridge] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    if ($exitCode -eq 0) {
        Write-Host ""
        $final = Get-OurNewestLastPt
        Write-Host "=== c2_bridge teacher completed successfully. Newest last.pt: $final ==="
        Write-Host "=== Next: run diagnostics/bridge_teacher_check.py --ckpt <that dir>\best.pt (Phase C3). ==="
        exit 0
    }
    Write-Host "[c2_bridge] Exited non-zero; will attempt resume."
    Start-Sleep -Seconds $RetryDelaySeconds
}
Write-Host "=== c2_bridge teacher did not complete after $MaxRetries attempts. ==="
exit 1
