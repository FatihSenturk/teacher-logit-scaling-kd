param(
    [int]$Epochs = 150,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int]$ImgSize = 224
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherCkpt = "checkpoints/teacher_rafdb_vich_recipe_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb_newrecipe_noerasing"

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
    "--workers", "$Workers",
    "--img-size", "$ImgSize",
    "--teacher-input-size", "224",
    "--random-erasing-p", "0",
    "--use-amp"
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

# Isolated A/B test vs run_phase0_full_ablation_rafdb_newrecipe.ps1's baseline (same
# corrected-recipe teacher, teacher_input_size=224), with three deltas:
#  - --random-erasing-p 0 instead of default 0.1 (augmentation-hurts-KD hypothesis check;
#    color_jitter is a dead arg under augment_preset="kd" so only erasing is varied)
#  - --img-size 224 instead of default 256: RAF-DB aligned crops are native 100x100, so
#    256 was pure upsampling with no extra information; 224 matches the teacher's own
#    training resolution exactly (skips _prepare_teacher_images' resize op entirely) and
#    cuts student FLOPs by ~24% ((256^2-224^2)/256^2)
#  - --epochs 150 instead of 250 (original grid's best epochs were all <=241)
Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_150e_224px" -ExtraArgs @()

Write-Host "RAF-DB newrecipe no-erasing baseline test complete. Artifacts under: $SaveRoot"
