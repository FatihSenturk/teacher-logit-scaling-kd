param(
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# A13 -- 2.248 M scratch doz-yaniti (2 sicaklik x 2 tohum = 4 kosu).
# Panel R1-W7: 76x oraninda kapasite kolu scratch, sicaklik kolu on-egitimli.
# T=1.0 zaten var (w100ns, n=3); eksik olan T=1.7 ve T=2.2.
#
# BU DOSYA ELLE YAZILMADI. Ureteci: diagnostics/build_replicate_queue.py
# Her kosunun komut satiri REFERANS KOSUNUN KENDI run_args.json'undan uretildi;
# bayrak adlari train_rafdb_kd.py'nin kendi argparse nesnesinden okundu. Boylece
# "tarif birebir ayni, yalniz sicaklik ve tohum degisiyor" iddiasi anlatilan degil YAPISAL.
# Uretim raporu (hangi anahtar varsayilana dustu): diagnostics/replicate_queue_build.md
#
# train_rafdb_kd.py'de --resume YOK. Kuyruk ortasinda cokerse -StartIndex ile devam et;
# YARIM KALAN KOSU DEVAM ETTIRILMEZ, temiz yeniden baslar (optimizer durumu ve veri
# sirasi temiz kosuyla ayni olmaz, karsilastirilabilirligi bozar).
# ============================================================================

$stages = @(
    @{ Label = "w100ns/T170/seed42"; Args = @("--teacher-ckpt", "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt", "--teacher-vae-head", "--teacher-layer-embedding", "--teacher-votes-sum", "0", "--teacher-vich-use-sampling", "--teacher-vich-logvar-min", "-10.0", "--teacher-vich-logvar-max", "10.0", "--teacher-vich-init-logvar-bias", "-5.0", "--teacher-temperature-scale", "1.7", "--teacher-input-size", "224", "--aligned-dir", "data\rafdb_aligned", "--metadata", "data\rafdb_aligned\metadata_rafdb_poster_var.csv", "--train-folds", "2", "--val-folds", "3", "--train-frac", "1.0", "--val-frac", "1.0", "--name", "RAFDB_vae9182_frontier_w100ns_tempscale_T170_b070_T6_224_400e_swa200_seed42", "--save-root", "results\unified_students", "--epochs", "400", "--batch-size", "64", "--workers", "8", "--max-train-batches", "0", "--max-val-batches", "0", "--img-size", "224", "--resize-size", "0", "--augment-preset", "kd", "--rotation-degrees", "12.0", "--color-jitter", "0.2", "--random-erasing-p", "0.1", "--ra-mag", "7", "--width-mult", "1.0", "--student-arch", "plus", "--dropout", "0.5", "--no-student-pretrained", "--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--student-embedding-dim", "768", "--student-feature-adapter-dim", "0", "--student-vae-kl-beta", "0.001", "--beta-vich", "0.0001", "--no-vich-sampling", "--vich-logvar-min", "-10.0", "--vich-logvar-max", "10.0", "--vich-init-logvar-bias", "-5.0", "--lr", "0.0003", "--weight-decay", "0.0001", "--alpha", "0.3", "--temperature", "6.0", "--label-smoothing", "0.1", "--mixup", "0.1", "--gate-uncertainty-source", "mean_logvar", "--gate-norm", "batch", "--gate-alpha-lo", "0.1", "--gate-alpha-hi", "0.7", "--gate-k", "2.0", "--gate-tau", "0.0", "--g2g-weight", "0.0", "--g2g-mode", "kl", "--g2g-warmup-epochs", "0", "--adaptive-t-gamma", "0.5", "--ctkd-t-min", "1.0", "--ctkd-t-max", "8.0", "--ctkd-grl-lambda-max", "1.0", "--feature-distill-weight", "0.0", "--feature-distill-mode", "mse_cosine", "--use-amp", "--class-weight-mode", "effective_number", "--class-weight-beta", "0.9999", "--scheduler-name", "cosine_warm_restarts", "--min-lr", "1e-06", "--gamma", "0.98", "--scheduler-t0", "10", "--scheduler-t-mult", "2", "--swa", "--swa-start", "200", "--swa-lr", "0.0001", "--ema-decay", "0.999", "--seed", "42", "--swanlab-project", "Unified-FER-KD", "--swanlab-mode", "offline", "--swanlab-logdir", "swanlog") },
    @{ Label = "w100ns/T170/seed1"; Args = @("--teacher-ckpt", "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt", "--teacher-vae-head", "--teacher-layer-embedding", "--teacher-votes-sum", "0", "--teacher-vich-use-sampling", "--teacher-vich-logvar-min", "-10.0", "--teacher-vich-logvar-max", "10.0", "--teacher-vich-init-logvar-bias", "-5.0", "--teacher-temperature-scale", "1.7", "--teacher-input-size", "224", "--aligned-dir", "data\rafdb_aligned", "--metadata", "data\rafdb_aligned\metadata_rafdb_poster_var.csv", "--train-folds", "2", "--val-folds", "3", "--train-frac", "1.0", "--val-frac", "1.0", "--name", "RAFDB_vae9182_frontier_w100ns_tempscale_T170_b070_T6_224_400e_swa200_seed1", "--save-root", "results\unified_students", "--epochs", "400", "--batch-size", "64", "--workers", "8", "--max-train-batches", "0", "--max-val-batches", "0", "--img-size", "224", "--resize-size", "0", "--augment-preset", "kd", "--rotation-degrees", "12.0", "--color-jitter", "0.2", "--random-erasing-p", "0.1", "--ra-mag", "7", "--width-mult", "1.0", "--student-arch", "plus", "--dropout", "0.5", "--no-student-pretrained", "--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--student-embedding-dim", "768", "--student-feature-adapter-dim", "0", "--student-vae-kl-beta", "0.001", "--beta-vich", "0.0001", "--no-vich-sampling", "--vich-logvar-min", "-10.0", "--vich-logvar-max", "10.0", "--vich-init-logvar-bias", "-5.0", "--lr", "0.0003", "--weight-decay", "0.0001", "--alpha", "0.3", "--temperature", "6.0", "--label-smoothing", "0.1", "--mixup", "0.1", "--gate-uncertainty-source", "mean_logvar", "--gate-norm", "batch", "--gate-alpha-lo", "0.1", "--gate-alpha-hi", "0.7", "--gate-k", "2.0", "--gate-tau", "0.0", "--g2g-weight", "0.0", "--g2g-mode", "kl", "--g2g-warmup-epochs", "0", "--adaptive-t-gamma", "0.5", "--ctkd-t-min", "1.0", "--ctkd-t-max", "8.0", "--ctkd-grl-lambda-max", "1.0", "--feature-distill-weight", "0.0", "--feature-distill-mode", "mse_cosine", "--use-amp", "--class-weight-mode", "effective_number", "--class-weight-beta", "0.9999", "--scheduler-name", "cosine_warm_restarts", "--min-lr", "1e-06", "--gamma", "0.98", "--scheduler-t0", "10", "--scheduler-t-mult", "2", "--swa", "--swa-start", "200", "--swa-lr", "0.0001", "--ema-decay", "0.999", "--seed", "1", "--swanlab-project", "Unified-FER-KD", "--swanlab-mode", "offline", "--swanlab-logdir", "swanlog") },
    @{ Label = "w100ns/T220/seed42"; Args = @("--teacher-ckpt", "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt", "--teacher-vae-head", "--teacher-layer-embedding", "--teacher-votes-sum", "0", "--teacher-vich-use-sampling", "--teacher-vich-logvar-min", "-10.0", "--teacher-vich-logvar-max", "10.0", "--teacher-vich-init-logvar-bias", "-5.0", "--teacher-temperature-scale", "2.2", "--teacher-input-size", "224", "--aligned-dir", "data\rafdb_aligned", "--metadata", "data\rafdb_aligned\metadata_rafdb_poster_var.csv", "--train-folds", "2", "--val-folds", "3", "--train-frac", "1.0", "--val-frac", "1.0", "--name", "RAFDB_vae9182_frontier_w100ns_tempscale_T220_b070_T6_224_400e_swa200_seed42", "--save-root", "results\unified_students", "--epochs", "400", "--batch-size", "64", "--workers", "8", "--max-train-batches", "0", "--max-val-batches", "0", "--img-size", "224", "--resize-size", "0", "--augment-preset", "kd", "--rotation-degrees", "12.0", "--color-jitter", "0.2", "--random-erasing-p", "0.1", "--ra-mag", "7", "--width-mult", "1.0", "--student-arch", "plus", "--dropout", "0.5", "--no-student-pretrained", "--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--student-embedding-dim", "768", "--student-feature-adapter-dim", "0", "--student-vae-kl-beta", "0.001", "--beta-vich", "0.0001", "--no-vich-sampling", "--vich-logvar-min", "-10.0", "--vich-logvar-max", "10.0", "--vich-init-logvar-bias", "-5.0", "--lr", "0.0003", "--weight-decay", "0.0001", "--alpha", "0.3", "--temperature", "6.0", "--label-smoothing", "0.1", "--mixup", "0.1", "--gate-uncertainty-source", "mean_logvar", "--gate-norm", "batch", "--gate-alpha-lo", "0.1", "--gate-alpha-hi", "0.7", "--gate-k", "2.0", "--gate-tau", "0.0", "--g2g-weight", "0.0", "--g2g-mode", "kl", "--g2g-warmup-epochs", "0", "--adaptive-t-gamma", "0.5", "--ctkd-t-min", "1.0", "--ctkd-t-max", "8.0", "--ctkd-grl-lambda-max", "1.0", "--feature-distill-weight", "0.0", "--feature-distill-mode", "mse_cosine", "--use-amp", "--class-weight-mode", "effective_number", "--class-weight-beta", "0.9999", "--scheduler-name", "cosine_warm_restarts", "--min-lr", "1e-06", "--gamma", "0.98", "--scheduler-t0", "10", "--scheduler-t-mult", "2", "--swa", "--swa-start", "200", "--swa-lr", "0.0001", "--ema-decay", "0.999", "--seed", "42", "--swanlab-project", "Unified-FER-KD", "--swanlab-mode", "offline", "--swanlab-logdir", "swanlog") },
    @{ Label = "w100ns/T220/seed1"; Args = @("--teacher-ckpt", "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt", "--teacher-vae-head", "--teacher-layer-embedding", "--teacher-votes-sum", "0", "--teacher-vich-use-sampling", "--teacher-vich-logvar-min", "-10.0", "--teacher-vich-logvar-max", "10.0", "--teacher-vich-init-logvar-bias", "-5.0", "--teacher-temperature-scale", "2.2", "--teacher-input-size", "224", "--aligned-dir", "data\rafdb_aligned", "--metadata", "data\rafdb_aligned\metadata_rafdb_poster_var.csv", "--train-folds", "2", "--val-folds", "3", "--train-frac", "1.0", "--val-frac", "1.0", "--name", "RAFDB_vae9182_frontier_w100ns_tempscale_T220_b070_T6_224_400e_swa200_seed1", "--save-root", "results\unified_students", "--epochs", "400", "--batch-size", "64", "--workers", "8", "--max-train-batches", "0", "--max-val-batches", "0", "--img-size", "224", "--resize-size", "0", "--augment-preset", "kd", "--rotation-degrees", "12.0", "--color-jitter", "0.2", "--random-erasing-p", "0.1", "--ra-mag", "7", "--width-mult", "1.0", "--student-arch", "plus", "--dropout", "0.5", "--no-student-pretrained", "--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--student-embedding-dim", "768", "--student-feature-adapter-dim", "0", "--student-vae-kl-beta", "0.001", "--beta-vich", "0.0001", "--no-vich-sampling", "--vich-logvar-min", "-10.0", "--vich-logvar-max", "10.0", "--vich-init-logvar-bias", "-5.0", "--lr", "0.0003", "--weight-decay", "0.0001", "--alpha", "0.3", "--temperature", "6.0", "--label-smoothing", "0.1", "--mixup", "0.1", "--gate-uncertainty-source", "mean_logvar", "--gate-norm", "batch", "--gate-alpha-lo", "0.1", "--gate-alpha-hi", "0.7", "--gate-k", "2.0", "--gate-tau", "0.0", "--g2g-weight", "0.0", "--g2g-mode", "kl", "--g2g-warmup-epochs", "0", "--adaptive-t-gamma", "0.5", "--ctkd-t-min", "1.0", "--ctkd-t-max", "8.0", "--ctkd-grl-lambda-max", "1.0", "--feature-distill-weight", "0.0", "--feature-distill-mode", "mse_cosine", "--use-amp", "--class-weight-mode", "effective_number", "--class-weight-beta", "0.9999", "--scheduler-name", "cosine_warm_restarts", "--min-lr", "1e-06", "--gamma", "0.98", "--scheduler-t0", "10", "--scheduler-t-mult", "2", "--swa", "--swa-start", "200", "--swa-lr", "0.0001", "--ema-decay", "0.999", "--seed", "1", "--swanlab-project", "Unified-FER-KD", "--swanlab-mode", "offline", "--swanlab-logdir", "swanlog") }
)

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $cmd = @("train_rafdb_kd.py") + $Stage.Args

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## A13 STAGE: $StageLabel, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        # PS 5.1 tuzagi: cagiran stderr'i pipeline'a sokarsa her satir NativeCommandError
        # olur ve Stop altinda oldurucu hale gelir. timm'in FutureWarning'i G0 kuyrugunu
        # ilk kosuda bu yuzden oldurdu. Basari zaten $LASTEXITCODE'dan okunuyor.
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & python -u @cmd | Out-Host
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $prevEAP
        Write-Host "[$StageLabel] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) { return $true }
        Write-Host "[$StageLabel] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

Write-Host "=== A13: $($stages.Count) kosu, index $StartIndex'ten ==="
for ($i = $StartIndex; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    $ok = Invoke-Run -Stage $stage -StageLabel "$($stage.Label) (idx $i)"
    if (-not $ok) {
        Write-Host "=== A13: stage $($stage.Label) (index $i) $MaxRetries denemede basarisiz. Devam: -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== A13 ($($stages.Count) kosu) tamamlandi. ==="
exit 0
