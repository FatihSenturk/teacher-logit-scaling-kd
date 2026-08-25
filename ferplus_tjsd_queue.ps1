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
# FERPlus T*_JSD arm (27 Jul): is "calibrated" the same thing as "human-aligned"?
#
# B-015 is CLOSED and CONFIRMED: student ECE is monotone in teacher ECE, on two datasets with
# OPPOSITE teacher pathologies, 9/9 within-seed curves. That law is about calibration against
# HARD labels. FERPlus can ask a question no hard-label dataset can, because it ships the raw
# 10-rater vote distribution: is the temperature that best CALIBRATES the teacher also the one
# that best matches HUMAN DISAGREEMENT? On the teacher the answer is already NO, and the gap is
# large (diagnostics/ferplus_jsd/ferplus_teacher_signed_grid.json):
#
#   T        teacher ECE   signed gap   JSD vs 10 raters   mean entropy   (human entropy 0.4401)
#   0.5063     0.0156        -0.0117        0.0490            0.2562      <- best ECE/NLL
#   0.74       0.0665        -0.0649        0.0440            0.4119      <- best JSD, matches human H
#   1.0        0.1282        -0.1277        0.0492            0.6118      <- native
#   0.26       0.0393        +0.0393        0.0659            0.1161      <- over-sharpened
#
# Moving the teacher from T*_ECE to T*_JSD costs +0.0508 ECE and buys -0.0050 JSD.
# THE STUDENT-SIDE QUESTION: does a student distilled at the human-aligned temperature inherit
# the human-uncertainty match, and what does it pay in hard-label calibration?
#
# WHY T=0.74 IS A DISCRIMINATING GRID POINT AND NOT A FOURTH REPLICATE.
# Its teacher ECE (0.0665) is HIGHER than T=0.26's (0.0393) but LOWER than T=1.0's (0.1282), so
# the teacher-ECE ordering is  0.5063 < 0.26 < 0.74 < 1.0. That makes the two hypotheses give
# DIFFERENT predictions at this one point, which is the only reason it is worth 7.5 GPU-hours:
#
#   PRE-REGISTERED PREDICTION 1 (B-015 extension, hard-label ECE):
#       student ECE at T=0.74 lands BETWEEN the T=0.26 and T=1.0 students, preserving the
#       ordering  ECE(0.5063) < ECE(0.26) < ECE(0.74) < ECE(1.0).
#       Measured anchors @swa (3 seeds): 0.0185 / 0.0587 / ??? / 0.0783
#   PRE-REGISTERED PREDICTION 2 (human alignment, student JSD vs the 10-rater distribution):
#       student JSD is MINIMISED at T=0.74, i.e. below the T=0.5063, T=0.26 and T=1.0 students.
#
#   If BOTH hold, the two objectives are demonstrably distinct and a real trade-off exists:
#       you must choose whether to calibrate against argmax labels or against human ambiguity.
#   If P1 holds and P2 fails, human alignment does NOT transfer through distillation, and the
#       teacher-side JSD optimum is a property of the teacher only. Report as such.
#   If P1 fails, B-015's monotonicity has a counterexample at an interior grid point -- that is a
#       genuine restriction of the law and must be reported as one, not explained away.
#
# ⚠️ MANDATORY EVALUATION RULE (from the brief, and it is the right rule):
# Do NOT score these students on hard-label ECE alone. That metric is defined against argmax
# labels and therefore hands the win to T*_ECE by construction -- a rigged test. Every arm is
# scored on BOTH axes: hard-label {ECE, NLL, Brier, acc, macro-F1} AND human-distribution
# {JSD vs the 10-rater distribution, correlation of per-sample entropy with human entropy}.
# Both results are reported whichever way they fall. Student-side scorer:
#   diagnostics/ferplus_student_jsd.py   (post-hoc, from best/last/swa checkpoints, CPU)
#
# Everything else is IDENTICAL to the 9 B-015 runs (same launcher shape, same recipe, tau_KD=6
# fixed), so teacher pre-scaling remains the single manipulated variable.
# 3 runs: 2 paired (~4.75 h) then 1 solo (~2.79 h) = ~7.5 h wall clock.
# train_ferplus_kd.py has NO --resume; on a crash resume with -Stream/-StartIndex.
# ============================================================================

$teacherCfg  = "configs\FERPlus_8_vich_teacher_vae_ce_kld.yaml"
$teacherCkpt = "checkpoints\teacher_ferplus_vich_best.pt"
$DataRoot    = "data\FERPlus_processed"
$Tval        = "0.74"
$Tag         = "T074"

# seed42 first on Stream A so the seed-matched comparison against the existing seed-42 curve
# (which is complete at all three earlier temperatures) is the first thing available.
$streams = @{
    A = @(42, 1)
    B = @(43)
}

function Get-Cmd {
    param([int]$Seed)
    $runName = "FERPlus_tempscale_${Tag}_vich_T6_224_200e_swa100_seed$Seed"
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
        "--teacher-temperature-scale", "$Tval",
        "--seed", "$Seed"
    )
    return @{ Cmd = $cmd; RunName = $runName }
}

function Invoke-Run {
    param([int]$Seed)
    $b = Get-Cmd -Seed $Seed
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        $t0 = Get-Date
        Write-Host ""
        Write-Host "########## FERPLUS-TJSD ${Stream} seed$Seed ($($b.RunName)), T=$Tval, attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        & python -u @($b.Cmd) | Out-Host
        $exitCode = $LASTEXITCODE
        $elapsed = (Get-Date) - $t0
        Write-Host "[seed$Seed] Exit code: $exitCode after $([math]::Round($elapsed.TotalHours,2))h at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) {
            Write-Host "[seed$Seed] WALL-CLOCK $([math]::Round($elapsed.TotalHours,2))h/run"
            return $true
        }
        Write-Host "[seed$Seed] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

if ($DryRun) {
    Write-Host "=== DRY RUN: STREAM $Stream (nothing executed) ==="
    foreach ($s in $streams[$Stream]) {
        $b = Get-Cmd -Seed $s
        Write-Host ""
        Write-Host "--- $($b.RunName)   (teacher T=$Tval)"
        Write-Host "python -u $($b.Cmd -join ' ')"
    }
    exit 0
}

$seedList = $streams[$Stream]
Write-Host "=== FERPlus T*_JSD arm, STREAM $Stream : $($seedList.Count) runs, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $seedList.Count; $i++) {
    $seed = $seedList[$i]
    if (-not (Invoke-Run -Seed $seed)) {
        Write-Host "=== STREAM ${Stream}: seed$seed (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} FERPlus T*_JSD ($($seedList.Count) runs) completed successfully. ==="
exit 0
