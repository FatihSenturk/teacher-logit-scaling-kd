param(
    [int]$Epochs = 250,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int[]]$Seeds = @(43, 44)
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Statistical validation for the ORIGINAL RAF-DB grid (teacher_vich9237_best.pt, 92.37%):
# baseline and CTKD were 90.09% vs 89.83% on a single seed (42). Re-run both at 2 more
# seeds to see whether that ~0.26pp gap exceeds seed-to-seed noise.
#
# NOTE: deliberately NOT passing --teacher-input-size 224 here, even though we now know
# train_rafdb_kd.py's default (--teacher-input-size 0 => matches student's --img-size 256)
# fed the teacher 256px images instead of its native 224px in the original grid. This
# script's whole point is to reproduce that EXACT original setup at different seeds --
# fixing the resolution here would make it a different experiment, not a noise check.
$TeacherCkpt = "checkpoints/teacher_vich9237_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb_multiseed"

$commonArgs = @(
    "--teacher-ckpt", $TeacherCkpt,
    "--teacher-vich-head",
    "--teacher-vich-init-logvar-bias", "0.0",
    "--aligned-dir", $AlignedDir,
    "--metadata", $Metadata,
    "--student-head-type", "vich",
    "--save-root", $SaveRoot,
    "--epochs", "$Epochs",
    "--batch-size", "$BatchSize",
    "--workers", "$Workers"
)

function Invoke-Phase0Run {
    param([string]$Name, [string[]]$ExtraArgs)
    $cmd = @("train_rafdb_kd.py") + $commonArgs + @("--name", $Name) + $ExtraArgs
    Write-Host "=== Phase 0 full run: $Name ==="
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd
    if ($LASTEXITCODE -ne 0) { throw "Phase 0 run failed: $Name" }
    Write-Host "Finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

foreach ($seed in $Seeds) {
    Invoke-Phase0Run -Name "rafdb_baseline_250e_seed$seed" -ExtraArgs @("--seed", "$seed")
    Invoke-Phase0Run -Name "rafdb_ctkd_250e_seed$seed" -ExtraArgs @("--mixup", "0", "--ctkd-enable", "--seed", "$seed")
}

Write-Host "RAF-DB multi-seed validation runs completed successfully. Artifacts under: $SaveRoot"
