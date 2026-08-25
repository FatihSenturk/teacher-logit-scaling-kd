param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    # T* fit on a HELD-OUT stratified half (half-A) of fold-3 val
    # (diagnostics/b3_tstar_halfsplit.py, seed 1234) -- NOT on the full val -- so
    # the causal run never tunes T* on data overlapping the reported eval. The
    # full-val diagnostic T* was 1.3494; half-A gives 1.3406 (stable scalar).
    # B3's causal accuracy/ECE must be reported on half-B (indices saved in
    # diagnostics/teacher_temperature_scaling/b3_tstar_halfsplit.json), the half
    # T* never saw.
    [double]$TStar = 1.3406
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-20: Phase B3 -- causal test of "teacher calibration -> student outcome".
#
# Identical to the existing Stage1 baseline run
# (RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200: 89.67% best /
# ECE 0.0581), differing in EXACTLY ONE flag: --teacher-temperature-scale <T*>.
# T* = 1.3406 was fitted on a HELD-OUT half (half-A) of fold-3 val
# (diagnostics/b3_tstar_halfsplit.py) -- leak-free per the P1 pre-registration --
# and drops Stage1's *teacher* ECE from ~0.038 to ~0.017 (verified generalizing
# to half-B: 0.0379->0.0203), onto VAE9182's calibration level (0.0136), WITHOUT
# changing head architecture, recipe, or seed. Causal test reported on half-B
# (T*-unseen): if the student moves toward VAE9182's student outcome
# (90.06% / ECE 0.0285), teacher calibration is causal and cheaply fixable; if
# not, the teacher-ECE->student correlation was not causal.
#
# The flag divides the teacher logits by T* before the KD soft-target softmax
# (train_rafdb_kd.py). Baseline-only path (no adaptive_t/logit_std/ctkd), so the
# double-count guard in train_rafdb_kd.py is not triggered.
#
# GPU: run AFTER the Phase A seed replicates free the card (2nd GPU priority per
# the plan). train_rafdb_kd.py has no --resume; a crash restarts from epoch 0.

$TeacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"
$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
$runName = "RAFDB_stage1_tempscale_T1341_halfA_baseline_b070_T6_224_400e_swa200"

$cmd = @(
    "train_rafdb_kd.py",
    "--teacher-ckpt", "$TeacherCkpt",
    "--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0",
    "--teacher-layer-embedding",
    "--teacher-input-size", "224",
    "--teacher-temperature-scale", "$TStar",
    "--aligned-dir", "$DataRoot",
    "--metadata", "$metadata",
    "--name", "$runName",
    "--save-root", "results\unified_students",
    "--epochs", "400",
    "--batch-size", "64",
    "--workers", "12",
    "--img-size", "224",
    "--resize-size", "0",
    "--augment-preset", "kd",
    "--student-head-type", "vich",
    "--student-layer-embedding",
    "--student-lightweight-layer-embedding",
    "--student-layer-embedding-layers", "3",
    "--no-vich-sampling",
    "--alpha", "0.3",
    "--temperature", "6",
    "--label-smoothing", "0.1",
    "--mixup", "0.1",
    "--use-amp",
    "--class-weight-mode", "effective_number",
    "--class-weight-beta", "0.9999",
    "--scheduler-name", "cosine_warm_restarts",
    "--min-lr", "1e-6",
    "--gamma", "0.98",
    "--scheduler-t0", "10",
    "--scheduler-t-mult", "2",
    "--swa", "--swa-start", "200", "--swa-lr", "0.0001",
    "--seed", "42"
)

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    Write-Host ""
    Write-Host "########## B3 STAGE: stage1_tempscale_T$TStar ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd | Out-Host
    $exitCode = $LASTEXITCODE
    Write-Host "[b3_stage1_tempscale] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "=== b3_stage1_tempscale completed successfully. ==="
        exit 0
    }
    Write-Host "[b3_stage1_tempscale] Exited non-zero. No --resume support -- next attempt restarts from epoch 0."
    Start-Sleep -Seconds $RetryDelaySeconds
}
Write-Host "=== b3_stage1_tempscale did not complete after $MaxRetries attempts. ==="
exit 1
