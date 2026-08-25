param(
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# G0 -- kontrol ogretmeni grid inceltmesi (2026-08-06). ONAYLANDI: Fatih, 6 Agu.
#
# ON-BEYAN DURUMU: BU KOSULAR ON-BEYANLI DEGIL. Round-2 hakem raporu (5 Agu)
# gorulmusken planlandilar. PREREGISTRATIONS bolum B'ye (on-kaydi OLMAYANLAR)
# kaydedildi; makalede "pre-registered" DENMEYECEK.
#
# NEDEN. Panel R1-W11: kontrol ogretmeninin (VAE9182) kendi optimumu
# T*_NLL=0.983 / T*_ECE=1.057 araliginda, ama on-beyanli falsifikasyon testinin
# grid'i {0.85, 1.00, 1.34, 1.70, 2.20} -- en yakin aralik 0.15. Yani "iyi
# kalibre ogretmen ic optimum gostermez" tahmini, BASARISIZ OLABILECEGI OLCEKTE
# SINANAMADI. Bu iki nokta (0.95 ve 1.10) onu sinanabilir yapar.
#
# Orijinal on-beyanli test 0.15 grid cozunurlugunde kosuldu ve TUTTU; bu iki
# nokta sonradan, incelemeye cevaben, ogretmenin kendi optimumu olceginde
# sinamak icin eklendi.
#
# TARIF: rafdb_p1_vae9182_flatcontrol_queue.ps1 ile BIREBIR ayni. Yalniz
# --teacher-temperature-scale ve --seed degisiyor. Ayniligi koşu argumanlarindan
# dogrula, addan degil (P6'daki ad->parametre kapisinin aynisi).
#
# 2 T x 3 tohum = 6 kosu, ~14 sa. train_rafdb_kd.py'de --resume YOK; kuyruk
# ortasinda cokerse -StartIndex ile devam et.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"  # VAE9182 (VAE head)
$teacherHeadArgs = @("--teacher-vae-head")

$Tvals = @{ "T095" = "0.95"; "T110" = "1.10" }

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# seed42 once: iki noktanin da seed42'si erken bitsin, kismi cikti bile
# yorumlanabilir olsun.
$stages = @(
    @{ Tag = "T095"; Seed = 42 },
    @{ Tag = "T110"; Seed = 42 },
    @{ Tag = "T095"; Seed = 1  },
    @{ Tag = "T110"; Seed = 1  },
    @{ Tag = "T095"; Seed = 43 },
    @{ Tag = "T110"; Seed = 43 }
)

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $tval    = $Tvals[$Stage.Tag]
    $runName = "RAFDB_vae9182_tempscale_$($Stage.Tag)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$teacherCkpt",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "400",
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
        "--teacher-temperature-scale", "$tval",
        "--seed", "$($Stage.Seed)"
    ) + $teacherHeadArgs

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## G0 STAGE: $StageLabel ($runName), T=$tval, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        # PS 5.1 tuzagi (6 Agu'da yasandi): cagiran taraf stderr'i pipeline'a sokarsa
        # (ornegin `*>&1`), PowerShell her stderr satirini NativeCommandError'a cevirir ve
        # $ErrorActionPreference="Stop" altinda bu OLUMCUL olur. timm'in zararsiz
        # FutureWarning'i kuyrugu ilk kosuda oldurdu. Basari/basarisizlik zaten
        # $LASTEXITCODE'dan okundugu icin native cagri boyunca Stop'a ihtiyac yok.
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

Write-Host "=== G0 kontrol grid inceltmesi: $($stages.Count) kosu, index $StartIndex'ten ==="
for ($i = $StartIndex; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    $label = "$($stage.Tag)_seed$($stage.Seed)"
    $ok = Invoke-Run -Stage $stage -StageLabel "$label (idx $i)"
    if (-not $ok) {
        Write-Host "=== G0: stage $label (index $i) $MaxRetries denemede basarisiz. Devam: -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== G0 kontrol grid inceltmesi ($($stages.Count) kosu) tamamlandi. ==="
exit 0
