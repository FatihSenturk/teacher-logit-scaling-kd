param(
    [int]$PollSeconds = 300,
    [int]$MaxWaitHours = 20,
    [int]$A12StartIndex = 0,
    [int]$A13StartIndex = 0,
    [switch]$SkipWait
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# A12 -> A13 zinciri (6 Agu 2026). GPU tek; G0 bitmeden baslamamali.
#
# NEDEN BEKLEME KOSULU "6/6 TAMAM", "surec olmus" DEGIL. G0 iki kosu arasinda
# birkac saniye bos kalir; surec yoklugu o bosluga da uyar ve zincir G0'in
# ortasinda baslardi. Onun yerine G0'in ALTI kosusunun her birinde
# metrics_swa.json arayarak bitmisligi TAMAMLANMA ARTEFAKTINDAN okuyoruz.
# (swa_student.pth egitimin en sonunda yaziliyor -- yarim koşuda yok.)
#
# G0 COKERSE ZINCIR BASLAMAZ, bilerek. Yarim kalan G0'i -StartIndex ile temiz
# yeniden baslatmak, GPU'yu 22 saatlik A12'ye vermekten oncelikli. Bekleme
# tavani dolarsa zincir HATA ile cikar ve GPU'yu bos birakir -- sessizce
# yanlis isi baslatmaktansa gorunur sekilde durmak.
#
# On-beyan: PREREGISTRATIONS A12 ve A13, commit b71e6ad, etiket
# a12-a13-predeclared -- ikisi de bu zincir calismadan ONCE donduruldu.
# ============================================================================

$G0Runs = @(
    "RAFDB_vae9182_tempscale_T095_b070_T6_224_400e_swa200_seed42",
    "RAFDB_vae9182_tempscale_T110_b070_T6_224_400e_swa200_seed42",
    "RAFDB_vae9182_tempscale_T095_b070_T6_224_400e_swa200_seed1",
    "RAFDB_vae9182_tempscale_T110_b070_T6_224_400e_swa200_seed1",
    "RAFDB_vae9182_tempscale_T095_b070_T6_224_400e_swa200_seed43",
    "RAFDB_vae9182_tempscale_T110_b070_T6_224_400e_swa200_seed43"
)

function Get-G0Done {
    $done = 0
    foreach ($r in $G0Runs) {
        $dir = Join-Path "results\unified_students" $r
        if (-not (Test-Path $dir)) { continue }
        $hit = Get-ChildItem -Path $dir -Directory -ErrorAction SilentlyContinue |
               Where-Object { Test-Path (Join-Path $_.FullName "metrics_swa.json") }
        if ($hit) { $done++ }
    }
    return $done
}

if (-not $SkipWait) {
    $deadline = (Get-Date).AddHours($MaxWaitHours)
    Write-Host "=== zincir: G0'in 6/6 bitmesi bekleniyor (tavan $MaxWaitHours sa, yoklama $PollSeconds sn) ==="
    while ($true) {
        $done = Get-G0Done
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] G0 tamamlanan: $done/6"
        if ($done -ge 6) { break }
        if ((Get-Date) -gt $deadline) {
            Write-Host "=== zincir: $MaxWaitHours saatlik tavan doldu, G0 hala $done/6. BASLATILMIYOR. ==="
            Write-Host "=== G0'i once bitir: powershell -File rafdb_g0_control_grid_queue.ps1 -StartIndex <ilk bitmeyen> ==="
            exit 2
        }
        Start-Sleep -Seconds $PollSeconds
    }
    Write-Host "=== G0 6/6 tamam. GPU serbest; A12 basliyor. ==="
}

$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "########## A12 kuyrugu: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
& powershell -NoProfile -ExecutionPolicy Bypass -File "rafdb_a12_realsignal_gate_queue.ps1" -StartIndex $A12StartIndex | Out-Host
$a12 = $LASTEXITCODE
Write-Host "[zincir] A12 exit: $a12 at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

if ($a12 -ne 0) {
    $ErrorActionPreference = $prevEAP
    Write-Host "=== zincir: A12 basarisiz (exit $a12). A13 BASLATILMIYOR -- eksik kolla devam etmek ==="
    Write-Host "=== iki isi de yarim birakirdi. Devam: -A12StartIndex <idx> ile bu betigi -SkipWait ile cagir. ==="
    exit $a12
}

Write-Host ""
Write-Host "########## A13 kuyrugu: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
& powershell -NoProfile -ExecutionPolicy Bypass -File "rafdb_a13_scratch_dose_queue.ps1" -StartIndex $A13StartIndex | Out-Host
$a13 = $LASTEXITCODE
Write-Host "[zincir] A13 exit: $a13 at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

$ErrorActionPreference = $prevEAP
if ($a13 -ne 0) {
    Write-Host "=== zincir: A13 basarisiz (exit $a13). Devam: -SkipWait -A12StartIndex 10 -A13StartIndex <idx> ==="
    exit $a13
}

Write-Host ""
Write-Host "=== zincir tamam: A12 (10 kosu) + A13 (4 kosu). $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
exit 0
