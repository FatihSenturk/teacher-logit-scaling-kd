param(
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# P6 ON-KAYIT (2026-08-01) -- yasanin HANGI degiskenin yasasi oldugu.
# BU BLOK BEYANDIR: kosular baslamadan yazildi, esikler simdi donuyor, sonradan
# secilmeyecek. Iki sonuc da yayimlanabilir. Beyan -> commit -> tag -> kosu.
#
# Tek ogretmen: Stage1 (miskalibre olan -- bilgilendirici kol). RAF-DB, 3 tohum
# {42, 1, 43}, tarif ana kampanyayla birebir (asagida P1 kuyrugundan aynen kopya);
# yalniz tau (KD sicakligi), alpha ve T (ogretmen on-olcekleme) degisir.
#
# --- GRID 1: tau x T faktoriyeli (indirgeme testi), 18 YENI kosu ---
# tau in {3, 6, 12} x T in {0.85, 1.3406, 1.70}. tau=6 kolonu MEVCUT kosulardan
# yeniden kullanilir (dogrulandi: 3 T degerinin ucu de 3'er tohumda diskte).
# T degerleri mevcut kolonla birebir ayni olsun diye 1.34 -> 1.3406, 1.7 -> 1.70.
# Grid bilincli olarak iki eslesmis T*tau cifti icerir:
#     (tau=3, T=1.70) <-> (tau=6, T=0.85)   -> T*tau = 5.10
#     (tau=6, T=1.70) <-> (tau=12, T=0.85)  -> T*tau = 10.20
#
# P6.1 (COKME tahmini): ogrenci ECE'si (T, tau)'ya yalniz T*tau carpimi uzerinden
# baglidir. KARAR KURALI (@swa, tohum-ici eslestirilmis):
#   Her eslesmis cift icin:
#     |ort dECE| <= 2 x kontrol ECE tohum sd'si  VE  isaretler 3/3 uyusmuyor
#         -> COKME DOGRULANDI (o cift icin)
#   Iki ciftte birden 3/3 ayni isaret VE |ort dECE| >= 2 x bar
#         -> COKME YANLISLANDI (ayrismanin kendisi bulgu: sira bilgisi ile
#            yumusaklik ayri kanallar)
#   Baska her durum -> COZUNMEDI; cift basina raporlanir, genel iddia YAZILMAZ.
#   BAR SIMDI DONUYOR: stage1/effective_number kontrol kolunun ECE tohum sd'si
#   @swa = 0.0012 (diagnostics/paper_tables/denominator_table.json) -> 2xbar 0.0024.
#
# --- GRID 2: alpha modulasyonu (dinleme kanali), 24 YENI kosu ---
# alpha in {0.1, 0.5, 0.7, 0.9} x T in {1.0, 1.3406} x 3 tohum. alpha=0.3 cifti
# MEVCUT (dogrulandi: baseline 3 tohum + tempscale_T134 3 tohum, effective_number).
# Gap(alpha) := ECE(T=1) - ECE(T=1.3406), tohum-ici.
#
# P6.2 (monotonluk): gap(alpha), alpha arttikca (ogrenci ogretmeni daha az
#   dinledikce) monoton azalir. KARAR KURALI: 5 alpha noktasinda {0.1, 0.3, 0.5,
#   0.7, 0.9}, her tohumda ardil her adimda artmayan (non-increasing); 3/3 tohumda
#   saglanirsa DOGRULANDI.
# P6.3 (uclar): gap(0.9) < gap(0.1), kesin esitsizlik, 3/3 tohumda.
#
# --- CERCEVE ---
# Bu kosular denetim kesmesinin (AUDIT_CUTOFF 2026-07-31-06:00) DISINDA: T8'e
# girmezler (selection_audit_table.py kesmeyle engelliyor). T1-T5'e de girmezler:
# T1/T2 acik isim sozlugunden okur (p1_two_teacher_overlay.py), T5 kontrol havuzu
# alpha=0.3 + t_scale=1.0 sartlari tasir (paper_tables.is_ablation_control).
# Kendi tablolari olacak (T11/T12). Grid 2'nin T=1.0 kollari defterde
# family=baseline gorunur ama alpha!=0.3 oldugundan hicbir kontrol havuzuna
# giremez -- preregistration_block=P6 satiri niyeti kayda gecirir.
#
# Tahmini yuk: 42 kosu x ~2.33 sa (P5 olcumu, --workers 12) ~= 98 sa ~= 2-6 Agu.
# Makale gonderimini BEKLEMEZ/BLOKLAMAZ -- tez / 3. calisma verisi.
#
# Kosu sirasi bilincli: once iki eslesmis ciftin YENI hucreleri (6 kosu -> P6.1
# ~14 saatte cevaplanabilir), sonra Grid 1'in kalani, sonra Grid 2'de uclar
# (alpha 0.1/0.9 -> P6.3 erken), en son orta noktalar.
# train_rafdb_kd.py'de --resume YOK; cokme halinde -StartIndex <n> ile devam.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"  # Stage1 (VICH head)
$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# tag -> exact value (T134 = 1.3406, mevcut kolonla birebir)
$Tvals = @{ "ts085" = "0.85"; "ts100" = "1.0"; "ts134" = "1.3406"; "ts170" = "1.70" }
$Avals = @{ "a010" = "0.1"; "a050" = "0.5"; "a070" = "0.7"; "a090" = "0.9" }

$stages = @(
    # --- Grid 1, eslesmis ciftlerin yeni hucreleri once ---
    @{ G = 1; Tau = 3;  Ts = "ts170"; Seed = 42 },
    @{ G = 1; Tau = 3;  Ts = "ts170"; Seed = 1  },
    @{ G = 1; Tau = 3;  Ts = "ts170"; Seed = 43 },
    @{ G = 1; Tau = 12; Ts = "ts085"; Seed = 42 },
    @{ G = 1; Tau = 12; Ts = "ts085"; Seed = 1  },
    @{ G = 1; Tau = 12; Ts = "ts085"; Seed = 43 },
    # --- Grid 1, kalan hucreler ---
    @{ G = 1; Tau = 3;  Ts = "ts085"; Seed = 42 },
    @{ G = 1; Tau = 3;  Ts = "ts085"; Seed = 1  },
    @{ G = 1; Tau = 3;  Ts = "ts085"; Seed = 43 },
    @{ G = 1; Tau = 3;  Ts = "ts134"; Seed = 42 },
    @{ G = 1; Tau = 3;  Ts = "ts134"; Seed = 1  },
    @{ G = 1; Tau = 3;  Ts = "ts134"; Seed = 43 },
    @{ G = 1; Tau = 12; Ts = "ts134"; Seed = 42 },
    @{ G = 1; Tau = 12; Ts = "ts134"; Seed = 1  },
    @{ G = 1; Tau = 12; Ts = "ts134"; Seed = 43 },
    @{ G = 1; Tau = 12; Ts = "ts170"; Seed = 42 },
    @{ G = 1; Tau = 12; Ts = "ts170"; Seed = 1  },
    @{ G = 1; Tau = 12; Ts = "ts170"; Seed = 43 },
    # --- Grid 2, uclar once (P6.3 erken cevaplansin) ---
    @{ G = 2; A = "a010"; Ts = "ts100"; Seed = 42 },
    @{ G = 2; A = "a010"; Ts = "ts134"; Seed = 42 },
    @{ G = 2; A = "a090"; Ts = "ts100"; Seed = 42 },
    @{ G = 2; A = "a090"; Ts = "ts134"; Seed = 42 },
    @{ G = 2; A = "a010"; Ts = "ts100"; Seed = 1  },
    @{ G = 2; A = "a010"; Ts = "ts134"; Seed = 1  },
    @{ G = 2; A = "a090"; Ts = "ts100"; Seed = 1  },
    @{ G = 2; A = "a090"; Ts = "ts134"; Seed = 1  },
    @{ G = 2; A = "a010"; Ts = "ts100"; Seed = 43 },
    @{ G = 2; A = "a010"; Ts = "ts134"; Seed = 43 },
    @{ G = 2; A = "a090"; Ts = "ts100"; Seed = 43 },
    @{ G = 2; A = "a090"; Ts = "ts134"; Seed = 43 },
    # --- Grid 2, orta noktalar ---
    @{ G = 2; A = "a050"; Ts = "ts100"; Seed = 42 },
    @{ G = 2; A = "a050"; Ts = "ts134"; Seed = 42 },
    @{ G = 2; A = "a070"; Ts = "ts100"; Seed = 42 },
    @{ G = 2; A = "a070"; Ts = "ts134"; Seed = 42 },
    @{ G = 2; A = "a050"; Ts = "ts100"; Seed = 1  },
    @{ G = 2; A = "a050"; Ts = "ts134"; Seed = 1  },
    @{ G = 2; A = "a070"; Ts = "ts100"; Seed = 1  },
    @{ G = 2; A = "a070"; Ts = "ts134"; Seed = 1  },
    @{ G = 2; A = "a050"; Ts = "ts100"; Seed = 43 },
    @{ G = 2; A = "a050"; Ts = "ts134"; Seed = 43 },
    @{ G = 2; A = "a070"; Ts = "ts100"; Seed = 43 },
    @{ G = 2; A = "a070"; Ts = "ts134"; Seed = 43 }
)

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $tsVal = $Tvals[$Stage.Ts]
    if ($Stage.G -eq 1) {
        $tau     = $Stage.Tau
        $alpha   = "0.3"
        $tauTag  = "{0:d2}" -f [int]$tau
        $runName = "RAFDB_stage1_p6tau_T${tauTag}_$($Stage.Ts)_b070_224_400e_swa200_seed$($Stage.Seed)"
    } else {
        $tau     = 6
        $alpha   = $Avals[$Stage.A]
        $runName = "RAFDB_stage1_p6alpha_$($Stage.A)_$($Stage.Ts)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
    }

    # Tarif P1 doz-yanit kuyrugundan AYNEN; yalniz --temperature/--alpha/
    # --teacher-temperature-scale/--seed/--name degisir.
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$teacherCkpt",
        "--teacher-vich-head",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "400",
        "--batch-size", "64",
        "--workers", "12",
        "--img-size", "224",
        "--resize-size", "0",
        "--augment-preset", "kd",
        "--student-head-type", "vich",
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3",
        "--no-vich-sampling",
        "--alpha", "$alpha",
        "--temperature", "$tau",
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
        "--teacher-temperature-scale", "$tsVal",
        "--seed", "$($Stage.Seed)"
    )

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## P6 STAGE $StageLabel ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
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

Write-Host "=== P6 tau x alpha on-kayitli kuyruk: $($stages.Count) kosu, index $StartIndex'ten ==="
for ($i = $StartIndex; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    if ($stage.G -eq 1) { $label = "G1_tau$($stage.Tau)_$($stage.Ts)_seed$($stage.Seed)" }
    else                { $label = "G2_$($stage.A)_$($stage.Ts)_seed$($stage.Seed)" }
    $ok = Invoke-Run -Stage $stage -StageLabel "$label (idx $i)"
    if (-not $ok) {
        Write-Host "=== P6: stage $label (index $i) failed after $MaxRetries attempts. Resume: -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== P6 kuyrugu ($($stages.Count) kosu) tamamlandi. ==="
exit 0
