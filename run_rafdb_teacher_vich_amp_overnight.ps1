param(
    [int]$MaxRetries = 30,
    [int]$RetryDelaySeconds = 15,
    [ValidateSet("stage1_klb1e4", "stage2_klb1e4_qcs")]
    [string]$StartAt = "stage1_klb1e4"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$LogRoot = "results/teacher_logs/RAFDB/POSTERv2"

# Two-stage overnight teacher diagnostic, both derived from
# teacher_rafdb_vich_recipe_best.pt's recipe (RAFDB_posterv2_vich_recipe.yaml,
# ce_kld_beta=0.001, RAFDB_RECIPE transform, use_amp=False) with AMP left OFF
# throughout: use_sam=True disables GradScaler (main_encoder.py:134,
# `enabled=not args.use_sam`), so AMP would run pure autocast with no
# underflow protection -- too risky to combine with the ce_kld_beta change
# we're actually trying to isolate. epochs cut 300->200 since prior runs
# plateaued well before 300.
#
#   Stage 1: ce_kld_beta 0.001 -> 0.0001 (10x less KL pressure), RAFDB_RECIPE
#            transform unchanged. Tests whether the KL regularization term
#            was over-smoothing the teacher's distillation signal.
#   Stage 2: same ce_kld_beta=0.0001, transform switched RAFDB_RECIPE ->
#            QCS-rafdb (HFlip + p=0.5 ColorJitter, NO RandomErasing --
#            structurally different/lighter than RAFDB_RECIPE's
#            deterministic ColorJitter + RandomErasing(p=0.5)). Isolates the
#            augmentation-pipeline variable independent of ce_kld_beta,
#            matching ce9241's known transform family.
#
# Each stage auto-resumes from its own newest run's last.pt on any crash via
# main_encoder.py's --resume flag (restores model+optimizer+scheduler+scaler,
# continues from the saved epoch).
$stages = @(
    @{ Config = "RAFDB_posterv2_vich_klb1e4_200e.yaml";     Name = "stage1_klb1e4" },
    @{ Config = "RAFDB_posterv2_vich_klb1e4_qcs_200e.yaml"; Name = "stage2_klb1e4_qcs" }
)

function Get-LatestRunDir {
    Get-ChildItem -Path $LogRoot -Directory -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Invoke-TeacherStage {
    param([string]$ConfigFile, [string]$StageName)

    Write-Host ""
    Write-Host "########## STAGE: $StageName ($ConfigFile) : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    $resumeArgs = @()
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host "=== [$StageName] Attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
        if ($resumeArgs.Count -gt 0) {
            Write-Host "Resuming with: $resumeArgs"
        }
        $cmd = @("main_encoder.py", "--c", $ConfigFile) + $resumeArgs
        Write-Host "Command: python -u $($cmd -join ' ')"
        & python -u @cmd
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageName] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

        if ($exitCode -eq 0) {
            Write-Host "=== [$StageName] Completed successfully. ==="
            return $true
        }

        Write-Host "[$StageName] Exited non-zero -- looking for a checkpoint to resume from."
        $latest = Get-LatestRunDir
        if ($null -eq $latest) {
            Write-Host "[$StageName] No run directory found under $LogRoot -- cannot resume. Aborting stage."
            return $false
        }
        $lastCkpt = Join-Path $latest.FullName "last.pt"
        if (-not (Test-Path $lastCkpt)) {
            Write-Host "[$StageName] No last.pt found in $($latest.FullName) -- cannot resume. Aborting stage."
            return $false
        }
        Write-Host "[$StageName] Found checkpoint: $lastCkpt"
        $resumeArgs = @("--resume", $lastCkpt)
        Start-Sleep -Seconds $RetryDelaySeconds
    }

    Write-Host "=== [$StageName] Exhausted $MaxRetries attempts without completing. ==="
    return $false
}

$stageNames = $stages | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    $ok = Invoke-TeacherStage -ConfigFile $stage.Config -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping chain: stage $($stage.Name) did not complete. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== All teacher diagnostic stages completed successfully. ==="
exit 0
