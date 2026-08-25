param(
    [ValidateSet("A", "B")]
    [string]$Stream = "A",
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [switch]$NoWait,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# Two chained phases, launched now, gated on the VAE9182 flat-control queue finishing.
#
# PHASE P3 -- complete the adaptive_t leg to 3 seeds on all 3 teachers.
#   Inventory before this: vae9182 n=3 (done), stage1 n=2 (seeds 42,1), primary n=1 (seed 42).
#   So "the 3rd Primary seed" is actually TWO runs (seeds 1 and 43), plus stage1 seed 43.
#   Expectation: replication, not a new regime (Primary teacher headroom 0.0199 ~ Stage1 0.0220).
#   Recipe copied from each teacher's own existing adaptive_t run_args.json -- not reconstructed.
#
# PHASE MISCAL -- deliberate miscalibration: within-teacher causality for B-007.
#   Take the WELL-calibrated VAE9182 teacher (own ECE 0.0136) and pre-scale its logits by a
#   FIXED T0 = 0.7311, chosen in closed form from cached teacher logits so that the pre-scaled
#   teacher's ECE = 0.0378, i.e. exactly Stage1's native miscalibration level.
#
#   WHY T0 < 1 AND NOT T0 > 1 (this is the crux, do not "fix" it):
#   Two temperatures hit teacher ECE 0.0378 -- T0=0.731 (over-CONFIDENT) and T0~1.25
#   (over-SMOOTH). Matching the ECE magnitude does NOT match the miscalibration DIRECTION.
#   Stage1 is natively over-confident (its T*=1.35 > 1, i.e. it needs softening). To reproduce
#   Stage1's regime we must make VAE9182 over-confident too => sharpen, T0 < 1. Picking 1.25
#   would inject the OPPOSITE pathology and test nothing about Stage1.
#
#   Design: T0 is FIXED and identical in both arms; --adaptive-t-enable is the ONLY manipulated
#   variable. This is why it is not degenerate: the KD softmax is softmax(z/(T0*T_mech)), so
#   SWEEPING T0 with a mechanism on would be degenerate with sweeping the mechanism -- but a
#   fixed T0 with the mechanism toggled is a clean single-variable contrast. The guard in
#   train_rafdb_kd.py is opted out of via --allow-tempscale-with-mechanism (passed in BOTH arms,
#   where it is inert for the OFF arm, so the two arms differ in exactly one flag).
#
#   PRE-REGISTERED PREDICTION: on the native VAE9182 teacher adaptive_t is a WEAK lever
#   (acc +0.054 pp null; ECE -0.0034, consistent 3/3 -- see BULGULAR B-004). Under injected
#   miscalibration its ECE benefit should GROW substantially (toward the -0.0292 seen when
#   Stage1's real miscalibration was removed). NB: the honest framing is "weak -> stronger",
#   NOT "dead -> alive" -- adaptive_t was the one mechanism that was never dead. Gate and G2G
#   are the dead ones; gate is the sharper follow-up if this pilot passes.
#   KILL-SWITCH: 2 seeds first. If the ECE delta does not clear the native -0.0034 in BOTH
#   seeds, stop -- do not spend the 3rd seed.
#
# train_rafdb_kd.py has NO --resume; on a mid-queue crash resume with -Stream/-StartIndex.
# ============================================================================

$TeacherStage1  = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"
$TeacherPrimary = "checkpoints\teacher_rafdb_vich_recipe_best.pt"
$TeacherVae9182 = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"

# Closed-form solution (bisection on cached fold-3 val teacher logits):
#   confidence_ece(vae9182_logits, labels, T=0.7311) = 0.0378 = Stage1's ECE(T=1)
$MiscalT = "0.7311"

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

$streams = @{
    A = @(
        @{ Kind = "p3";     Teacher = "primary"; Seed = 1  },
        @{ Kind = "p3";     Teacher = "stage1";  Seed = 43 },
        @{ Kind = "miscal"; Arm = "off";         Seed = 42 },
        @{ Kind = "miscal"; Arm = "on";          Seed = 42 }
    )
    B = @(
        @{ Kind = "p3";     Teacher = "primary"; Seed = 43 },
        @{ Kind = "miscal"; Arm = "off";         Seed = 1  },
        @{ Kind = "miscal"; Arm = "on";          Seed = 1  }
    )
}

function Wait-ForVae9182 {
    # Gate on artifacts, not on PIDs: the launcher processes belong to another session and
    # their PIDs are not reliable here, but a finished run always has metrics_best.json.
    $target = 12
    while ($true) {
        $done = @(Get-ChildItem "results\unified_students\RAFDB_vae9182_tempscale_*\*\metrics_best.json" -ErrorAction SilentlyContinue).Count
        if ($done -ge $target) {
            Write-Host "[$Stream] VAE9182 flat-control complete ($done/$target). Starting chain at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')."
            return
        }
        Write-Host "[$Stream] waiting for VAE9182 flat-control: $done/$target done ($(Get-Date -Format 'HH:mm:ss'))"
        Start-Sleep -Seconds 300
    }
}

function Get-Cmd {
    param($Stage)

    $common = @(
        "train_rafdb_kd.py",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
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
        "--seed", "$($Stage.Seed)"
    )

    if ($Stage.Kind -eq "p3") {
        switch ($Stage.Teacher) {
            "primary" { $ckpt = $TeacherPrimary; $headArgs = @("--teacher-vich-head") }
            "stage1"  { $ckpt = $TeacherStage1;  $headArgs = @("--teacher-vich-head") }
        }
        $runName = "RAFDB_$($Stage.Teacher)_adaptive_t_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
        $extra = @("--adaptive-t-enable", "--adaptive-t-gamma", "0.5")
    }
    else {
        $ckpt = $TeacherVae9182
        $headArgs = @("--teacher-vae-head")
        $runName = "RAFDB_vae9182_miscalT0731_adaptivet$($Stage.Arm)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
        # T0 identical in both arms; --allow-tempscale-with-mechanism passed in both (inert when
        # adaptive_t is off) so the arms differ in exactly one flag.
        $extra = @("--teacher-temperature-scale", "$MiscalT", "--allow-tempscale-with-mechanism")
        if ($Stage.Arm -eq "on") { $extra += @("--adaptive-t-enable", "--adaptive-t-gamma", "0.5") }
    }

    $cmd = $common + @("--teacher-ckpt", "$ckpt", "--name", "$runName") + $headArgs + $extra
    return @{ Cmd = $cmd; RunName = $runName }
}

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $built   = Get-Cmd -Stage $Stage
    $cmd     = $built.Cmd
    $runName = $built.RunName

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## CHAIN ${Stream} STAGE: $StageLabel ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        & python -u @cmd | Out-Host
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageLabel] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) { return $true }
        Write-Host "[$StageLabel] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

if ($DryRun) {
    Write-Host "=== DRY RUN: STREAM $Stream command preview (nothing is executed) ==="
    foreach ($stage in $streams[$Stream]) {
        $b = Get-Cmd -Stage $stage
        Write-Host ""
        Write-Host "--- $($b.RunName)"
        Write-Host "python -u $($b.Cmd -join ' ')"
    }
    exit 0
}

if (-not $NoWait) { Wait-ForVae9182 }

$stageList = $streams[$Stream]
Write-Host "=== P3+MISCAL chain, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    if ($stage.Kind -eq "p3") { $label = "p3_$($stage.Teacher)_seed$($stage.Seed)" }
    else                      { $label = "miscal_$($stage.Arm)_seed$($stage.Seed)" }
    $ok = Invoke-Run -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i -NoWait ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} P3+MISCAL chain ($($stageList.Count) runs) completed successfully. ==="
exit 0
