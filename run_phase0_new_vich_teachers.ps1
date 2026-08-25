param(
    [string]$SaveRoot = "results/teacher_logs"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Promote-BestCheckpoint {
    param(
        [string]$DatasetDir,
        [string]$OutName
    )
    $searchRoot = Join-Path $PSScriptRoot "$SaveRoot\$DatasetDir\POSTERv2"
    if (-not (Test-Path $searchRoot)) {
        Write-Host "WARNING: $searchRoot not found, skipping checkpoint promotion for $OutName"
        return
    }
    $newest = Get-ChildItem -Path $searchRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $newest) {
        Write-Host "WARNING: no run directories under $searchRoot, skipping checkpoint promotion for $OutName"
        return
    }
    $bestPt = Join-Path $newest.FullName "best.pt"
    if (-not (Test-Path $bestPt)) {
        Write-Host "WARNING: $bestPt not found, skipping checkpoint promotion for $OutName"
        return
    }
    $dest = Join-Path $PSScriptRoot "checkpoints\$OutName"
    Copy-Item -Path $bestPt -Destination $dest -Force
    Write-Host "Promoted $bestPt -> $dest"
}

Write-Host "=== New VICH teacher: AffectNetPlus 7cls ==="
python -u main_encoder.py --c AffectNetPlus_7_vich_kld_27may.yaml
if ($LASTEXITCODE -ne 0) { throw "AffectNetPlus 7cls VICH teacher training failed." }
Promote-BestCheckpoint -DatasetDir "AffectNetPlus" -OutName "teacher_affectnetplus7_vich_best.pt"

Write-Host "=== New VICH teacher: AffectNetPlus 8cls ==="
python -u main_encoder.py --c AffectNetPlus_8_vich_kld_27may.yaml
if ($LASTEXITCODE -ne 0) { throw "AffectNetPlus 8cls VICH teacher training failed." }
Promote-BestCheckpoint -DatasetDir "AffectNetPlus" -OutName "teacher_affectnetplus8_vich_best.pt"

Write-Host "=== New VICH teacher: FERPlus 8cls (processed) ==="
python -u main_encoder.py --c FERPlus_8_vich_kld_200e_lr3e5_sam_processed_27may.yaml
if ($LASTEXITCODE -ne 0) { throw "FERPlus VICH teacher training failed." }
Promote-BestCheckpoint -DatasetDir "FER2013" -OutName "teacher_ferplus_vich_best.pt"

Write-Host "=== All new VICH teachers complete ==="
