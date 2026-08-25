param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-19: combined component run -- g2g_kl + adaptive_t together on the
# VAE9182 teacher, best_400e_swa200 recipe. Unblocked by the teacher-head-
# compat audit (VERDICT.md: S1, interface-compatible) and the calibration
# backfill's signal-quality read: adaptive_t only consumes teacher_logits
# (kd_baselines.entropy_adaptive_temperature), never mu/logvar, so it does not
# touch gate's diagnosed broken premise (logvar inversely tracks error) at
# all -- g2g_kl and adaptive_t are orthogonal mechanisms, no known conflict.
# Runs concurrently with the still-in-progress stage1 200e_noSWA grid
# (currently on stage1_g2g_kl, --workers 12) -- --workers 8 here to keep
# total CPU oversubscription bounded (12+8=20 on 16 cores, some contention
# accepted deliberately given GPU has ~7GB free VRAM headroom).

$TeacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"
$TeacherHeadArgs = @("--teacher-vae-head")
$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
$runName = "RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200"

# 2026-07-20: rerun at a 500-epoch cap (was 400). The original 400-epoch
# combined run finished at 89.86% (best_epoch 240, well before the 400 cap --
# not itself a late-peaker), but 3 of 4 other adaptive_t/gate runs in this
# grid were still ascending at their 400-epoch cap, so this rerun removes
# any doubt that the combined run's underperformance (vs. either component
# alone: g2g_kl 90.25%, adaptive_t 90.68%) is an epoch-budget artifact rather
# than a genuine negative interaction.

$cmd = @(
    "train_rafdb_kd.py",
    "--teacher-ckpt", "$TeacherCkpt",
    "--teacher-layer-embedding",
    "--teacher-input-size", "224",
    "--aligned-dir", "$DataRoot",
    "--metadata", "$metadata",
    "--name", "$runName",
    "--save-root", "results\unified_students",
    "--epochs", "500",
    "--batch-size", "64",
    "--workers", "8",
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
    "--seed", "42",
    "--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl",
    "--adaptive-t-enable"
) + $TeacherHeadArgs

for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    Write-Host ""
    Write-Host "########## STAGE: vae9182_combined_g2g_adaptive_t, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd | Out-Host
    $exitCode = $LASTEXITCODE
    Write-Host "[vae9182_combined_g2g_adaptive_t] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "=== vae9182_combined_g2g_adaptive_t completed successfully. ==="
        exit 0
    }
    Write-Host "[vae9182_combined_g2g_adaptive_t] Exited non-zero. No --resume support -- next attempt restarts from epoch 0."
    Start-Sleep -Seconds $RetryDelaySeconds
}
Write-Host "=== vae9182_combined_g2g_adaptive_t did not complete after $MaxRetries attempts. ==="
exit 1
