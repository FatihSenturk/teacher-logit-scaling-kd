param(
    [ValidateSet("A", "B")]
    [string]$Stream = "A",
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# FERPlus dose-response (26 Jul): does B-007 hold on a SECOND dataset?
#
# WHY: a causal law demonstrated on one dataset is among the most common reject reasons.
# B-007 (teacher calibration governs student calibration; headroom bounds what any mechanism can
# win) is currently RAF-DB-only. This is the external-validity test.
#
# Not (7 Agu 2026): iddianin guncel makale ifadesi "teacher-side logit scaling governs student
# calibration" -- bkz. baslik v2 (diagnostics/reports/2026-08-04_baslik_v2_teyit.md). Yukaridaki
# satir bu betigin KOSULARDAN ONCE donduruldugu andaki (26 Tem) ifadedir ve tarihi kayit olarak
# korunuyor. Prompt bu satiri paraphrase sayip yeniden yazmaya IZIN veriyordu; yazilmadi, cunku
# bu dosya B-007'nin FERPlus testinde kanit zincirinin bir parcasi (kosulardan once commit'lendi)
# ve on-beyan artefaktlarinin metnini geriye donuk degistirmemek kampanyanin duran kurali.
#
# THE FERPLUS TEACHER IS THE OPPOSITE PATHOLOGY -- which makes this a strong test, not a weak one.
# Stage1 (RAF-DB) is natively OVER-confident: ECE(T=1)=0.0378, signed gap +0.0338, T*=1.349 (>1,
# needs softening). The FERPlus VICH teacher is natively UNDER-confident, because it was trained
# on soft 10-rater vote targets: ECE(T=1)=0.1282, signed gap -0.1277, T*_NLL=0.5063 (<1, needs
# SHARPENING). So the law is being tested in a regime where the required correction runs the other
# way. All numbers below are closed-form from cached teacher logits
# (diagnostics/ferplus_jsd/ferplus_val_logits.pt), so the grid cost no GPU to design.
#
#   teacher-side headroom = ECE(T=1) - min_T ECE(T) = 0.1282 - 0.0084 = 0.1198
#   -- 5.4x LARGER than Stage1's 0.0220, i.e. a much bigger dose to work with.
#
# GRID (3 points x 3 seeds = 9 runs), mirroring Stage1's structure of
# {native, calibrated, crossed-over-to-the-opposite-pathology}:
#   T=1.0000  native      teacher ECE 0.1282  signed gap -0.1277  (badly UNDER-confident)
#   T=0.5063  T*_NLL      teacher ECE 0.0156  signed gap -0.0117  (calibrated)
#   T=0.2600  over-sharp  teacher ECE 0.0393  signed gap +0.0393  (OVER-confident: sign flipped,
#                         exactly as Stage1's T=2.20 flipped from over-confident to over-smooth)
#
# PRE-REGISTERED PREDICTION: student ECE is minimised at T=T*~0.51, and rises at BOTH ends, with
# the T=1.0 end worst (largest |teacher gap|). Equivalently: student ECE is monotone in teacher
# ECE, and monotone in |signed teacher miscalibration|, exactly as on RAF-DB.
# FALSIFIED IF: the student-ECE argmin is not at T*, or the ordering does not follow teacher ECE.
# In that case the law's scope is honestly restricted to RAF-DB.
#
# RECIPE: same LOGIC as RAF-DB (tau_KD=6, alpha=0.3, mixup 0.1, AMP, cosine_warm_restarts,
# SWA at 50% of the budget, lr 3e-4, wd 1e-4, 224px), with these HONEST DIFFERENCES, all of which
# are identical across the three arms so they cannot confound the single manipulated variable:
#   - epochs 200 / swa_start 100 instead of 400/200. FERPlus train is 28259 images vs RAF-DB's
#     12271 (2.3x), so 400 epochs would cost ~9.5 h/run = ~85 h for 9 runs. 200/100 keeps the
#     same SWA-at-half-budget ratio.
#   - NO class weighting: --class-weight-mode/--class-weight-beta DO NOT EXIST in
#     train_affectnetplus_kd.py (verified against --help). FERPlus also trains on soft vote
#     distributions, where class reweighting is less meaningful.
#   - NO --gamma: that flag does not exist in this script either.
#   - label_smoothing is FORCED to 0.0 and supervision to "soft" by train_ferplus_kd.py:1-19.
#
# best/last/swa checkpoints AND metrics_{best,last,swa}.json are already written by
# train_affectnetplus_kd.py (lines 675/682/715/736/752/807/827), so the selection audit can be run
# per-run immediately rather than reconstructed at the end as it had to be for RAF-DB.
#
# train_ferplus_kd.py has NO --resume; on a mid-queue crash resume with -Stream/-StartIndex.
# ============================================================================

$teacherCfg  = "configs\FERPlus_8_vich_teacher_vae_ce_kld.yaml"
$teacherCkpt = "checkpoints\teacher_ferplus_vich_best.pt"
$DataRoot    = "data\FERPlus_processed"

$Tvals = @{ "T100" = "1.0"; "T051" = "0.5063"; "T026" = "0.26" }

# seed42-first on Stream A -> a full 3-point seed42 curve emerges before anything else finishes.
$streams = @{
    A = @(
        @{ Tag = "T051"; Seed = 42 },
        @{ Tag = "T100"; Seed = 42 },
        @{ Tag = "T026"; Seed = 42 },
        @{ Tag = "T051"; Seed = 1 },
        @{ Tag = "T100"; Seed = 1 }
    )
    B = @(
        @{ Tag = "T026"; Seed = 1 },
        @{ Tag = "T051"; Seed = 43 },
        @{ Tag = "T100"; Seed = 43 },
        @{ Tag = "T026"; Seed = 43 }
    )
}

function Get-Cmd {
    param($Stage)
    $tval    = $Tvals[$Stage.Tag]
    $runName = "FERPlus_tempscale_$($Stage.Tag)_vich_T6_224_200e_swa100_seed$($Stage.Seed)"
    $cmd = @(
        "train_ferplus_kd.py",
        "--teacher-config", "$teacherCfg",
        "--teacher-ckpt", "$teacherCkpt",
        "--num-classes", "8",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--train-root", "$DataRoot",
        "--val-root", "$DataRoot",
        "--epochs", "200",
        "--batch-size", "64",
        "--workers", "8",
        "--img-size", "224",
        "--resize-size", "0",
        "--teacher-input-size", "224",
        "--student-head-type", "vich",
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3",
        "--no-vich-sampling",
        "--width-mult", "1.0",
        "--alpha", "0.3",
        "--temperature", "6",
        "--mixup", "0.1",
        "--use-amp",
        "--lr", "3e-4",
        "--weight-decay", "1e-4",
        "--scheduler-name", "cosine_warm_restarts",
        "--min-lr", "1e-6",
        "--scheduler-t0", "10",
        "--scheduler-t-mult", "2",
        "--swa", "--swa-start", "100", "--swa-lr", "0.0001",
        "--teacher-temperature-scale", "$tval",
        "--seed", "$($Stage.Seed)"
    )
    return @{ Cmd = $cmd; RunName = $runName; T = $tval }
}

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $b = Get-Cmd -Stage $Stage
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        $t0 = Get-Date
        Write-Host ""
        Write-Host "########## FERPLUS-DOSE ${Stream} STAGE: $StageLabel ($($b.RunName)), T=$($b.T), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        & python -u @($b.Cmd) | Out-Host
        $exitCode = $LASTEXITCODE
        $elapsed = (Get-Date) - $t0
        Write-Host "[$StageLabel] Exit code: $exitCode after $([math]::Round($elapsed.TotalHours,2))h at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) {
            # First-run wall clock drives the queue plan, per the experiment brief.
            Write-Host "[$StageLabel] WALL-CLOCK $([math]::Round($elapsed.TotalHours,2))h/run -> Stream A (5 runs) ~$([math]::Round(5*$elapsed.TotalHours,1))h, Stream B (4 runs) ~$([math]::Round(4*$elapsed.TotalHours,1))h"
            return $true
        }
        Write-Host "[$StageLabel] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

if ($DryRun) {
    Write-Host "=== DRY RUN: STREAM $Stream (nothing executed) ==="
    foreach ($stage in $streams[$Stream]) {
        $b = Get-Cmd -Stage $stage
        Write-Host ""
        Write-Host "--- $($b.RunName)   (teacher T=$($b.T))"
        Write-Host "python -u $($b.Cmd -join ' ')"
    }
    exit 0
}

$stageList = $streams[$Stream]
Write-Host "=== FERPlus dose-response, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    $label = "$($stage.Tag)_seed$($stage.Seed)"
    $ok = Invoke-Run -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} FERPlus dose-response ($($stageList.Count) runs) completed successfully. ==="
exit 0
