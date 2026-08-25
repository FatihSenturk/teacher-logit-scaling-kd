$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

$missing = @()
$ok = @()

function Check-Path {
    param([string]$Path, [string]$Label, [long]$MinBytes = 0)
    if (Test-Path $Path) {
        $item = Get-Item $Path
        if ($item.PSIsContainer) {
            $count = (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            if ($count -eq 0) {
                $script:missing += "$Label -- EXISTS BUT EMPTY: $Path"
            } else {
                $script:ok += "$Label -- OK ($count files): $Path"
            }
        } else {
            $size = $item.Length
            if ($size -lt $MinBytes) {
                $script:missing += "$Label -- EXISTS BUT SUSPICIOUSLY SMALL ($size bytes, expected >= $MinBytes): $Path"
            } else {
                $sizeMB = [math]::Round($size / 1MB, 1)
                $script:ok += "$Label -- OK (${sizeMB} MB): $Path"
            }
        }
    } else {
        $script:missing += "$Label -- MISSING: $Path"
    }
}

Write-Host "=== Checking repo / code (should already be here via git clone) ==="
Check-Path "train_affectnetplus_kd.py" "train_affectnetplus_kd.py"
Check-Path "train_rafdb_kd.py" "train_rafdb_kd.py"
Check-Path "train_ferplus_kd.py" "train_ferplus_kd.py"
Check-Path "kd_common.py" "kd_common.py"
Check-Path "run_phase0_extended_ablation_machine2.ps1" "run_phase0_extended_ablation_machine2.ps1"
Check-Path "run_phase0_full_ablation_rafdb_newrecipe.ps1" "run_phase0_full_ablation_rafdb_newrecipe.ps1"
Check-Path "run_phase0_full_ablation_affectnet7.ps1" "run_phase0_full_ablation_affectnet7.ps1"
Check-Path "run_phase0_full_ablation_ferplus.ps1" "run_phase0_full_ablation_ferplus.ps1"
Check-Path "configs\RAFDB_posterv2_vich_recipe.yaml" "configs\RAFDB_posterv2_vich_recipe.yaml"
Check-Path "configs\AffectNetPlus_7_vich_kld_27may.yaml" "configs\AffectNetPlus_7_vich_kld_27may.yaml"
Check-Path "configs\FERPlus_8_vich_teacher_vae_ce_kld.yaml" "configs\FERPlus_8_vich_teacher_vae_ce_kld.yaml"

Write-Host "=== Checking teacher checkpoints (must be copied manually, not in git) ==="
Check-Path "checkpoints\teacher_rafdb_vich_recipe_best.pt" "RAF-DB teacher" 500000000
Check-Path "checkpoints\teacher_affectnetplus7_vich_best.pt" "AffectNet+7 teacher" 500000000
Check-Path "checkpoints\teacher_ferplus_vich_best.pt" "FERPlus teacher" 500000000

Write-Host "=== Checking datasets (must be copied manually, not in git) ==="
Check-Path "data\rafdb_aligned" "RAF-DB data"
Check-Path "data\rafdb_aligned\metadata_rafdb_poster_var.csv" "RAF-DB metadata csv" 100000
Check-Path "data\AffectNet+" "AffectNet+ data"
Check-Path "data\FERPlus_processed" "FERPlus data"

Write-Host "=== Checking pretrained backbone weights (must be copied manually, not in git) ==="
Check-Path "pretrained\hub" "pretrained/hub (timm ImageNet weights)"
Check-Path "pretrained\posterv2" "pretrained/posterv2 (POSTERv2 backbone weights)"
Check-Path "models\mobilefacenet_model_best.pth.tar" "MobileFaceNet weights" 10000000

Write-Host "=== Checking Python environment ==="
$torchCheck = & python -c "import torch; print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available())" 2>&1
Write-Host "Python/torch check: $torchCheck"

Write-Host ""
Write-Host "=================== RESULTS ==================="
Write-Host "-- OK ($($ok.Count)) --" -ForegroundColor Green
$ok | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
Write-Host ""
if ($missing.Count -gt 0) {
    Write-Host "-- MISSING / PROBLEMATIC ($($missing.Count)) --" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "NOT READY -- fix the items above before running run_phase0_extended_ablation_machine2.ps1" -ForegroundColor Red
} else {
    Write-Host "ALL CHECKS PASSED -- ready to run run_phase0_extended_ablation_machine2.ps1" -ForegroundColor Green
}
