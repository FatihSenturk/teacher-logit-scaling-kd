"""Kuyruk üreteci: "tarif birebir aynı, yalnız tohum/sıcaklık değişiyor" iddiasını YAPISAL yap.

NEDEN VAR. İki ertelenmiş iş (A12 gerçek-sinyal gate n=3, A13 scratch doz-yanıtı) mevcut
kollara yeni hücre ekliyor. Bu tür işlerin bütün değeri "referans kolla aynı tarif" olmasında;
tarifi elle .ps1'e kopyalarsam iddia ANLATILAN olur, sessizce sapabilir. Onun yerine komut
satırı REFERANS KOŞUNUN KENDİ `run_args.json`'undan üretiliyor ve bayrak isimleri
`train_rafdb_kd.py`'nin KENDİ argparse nesnesinden okunuyor. Aynı disiplin P6'nın
ad->parametre kapısında ve R3-W1'in import-etme-kopyalama kuralında kullanıldı.

ÜÇ KAPI:
  1. Bütün `store` bayrakları AÇIKÇA yazılır -- varsayılana eşit olsalar bile. Varsayılan
     sonradan değişirse yeni koşu sessizce sapmasın diye.
  2. Parser'da olup referans `run_args.json`'da OLMAYAN her anahtar raporlanır (o koşudan
     sonra eklenmiş bayraklar). Sessiz varsayım yok -- G0 çıkış kontrolündeki kuralın aynısı.
  3. `store_true` varsayılanının False, `store_false` varsayılanının True olduğu doğrulanır;
     değilse üretim durur (o bayrak komut satırında ifade edilemez demektir).

Kullanım: python diagnostics/build_replicate_queue.py
Çıktı   : rafdb_a12_realsignal_gate_queue.ps1, rafdb_a13_scratch_dose_queue.ps1
          + diagnostics/replicate_queue_build.md (üretim raporu: hangi anahtar varsayılana düştü)
"""
import argparse
import glob
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "unified_students"
REPORT = ROOT / "diagnostics" / "replicate_queue_build.md"

sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- parser

class _Grab(Exception):
    def __init__(self, parser):
        self.parser = parser


def training_parser():
    """`train_rafdb_kd.parse_args()`'ın KENDİ parser'ı.

    Betikte `build_parser()` yok, parser `parse_args()` içinde kuruluyor. Bayrak adlarını
    elle listelemek yerine `parse_args`'ı geçici olarak kesip nesneyi alıyoruz -- böylece
    bayrak adı/eylem türü tek kaynaktan, betiğin kendisinden geliyor.
    """
    orig = argparse.ArgumentParser.parse_args

    def _fake(self, *a, **k):
        raise _Grab(self)

    argparse.ArgumentParser.parse_args = _fake
    try:
        importlib.import_module("train_rafdb_kd").parse_args()
        raise RuntimeError("parse_args() beklenmedik şekilde döndü")
    except _Grab as g:
        return g.parser
    finally:
        argparse.ArgumentParser.parse_args = orig


def flag_of(action):
    """dest -> komut satırı bayrağı (en uzun uzun-biçim)."""
    longs = [o for o in action.option_strings if o.startswith("--")]
    if not longs:
        raise RuntimeError(f"'{action.dest}' için uzun bayrak yok")
    return max(longs, key=len)


# --------------------------------------------------------------------------- ref args

def ref_args(run_name):
    hits = sorted(glob.glob(str(RUNS / run_name / "*" / "run_args.json")))
    if not hits:
        raise RuntimeError(f"referans koşu bulunamadı: {run_name}")
    return json.loads(Path(hits[-1]).read_text(encoding="utf-8")), hits[-1]


def build_cmd(parser, ra, overrides):
    """(argüman listesi, varsayılana düşen anahtarlar) döndürür."""
    vals = dict(ra)
    vals.update(overrides)
    out, fell_back, unrepresentable = [], [], []

    # dest BASINA grupla. Bir dest'in birden cok eylemi olabilir -- `--student-pretrained`
    # (store_true, varsayilan True) ile `--no-student-pretrained` (store_false) ayni dest'i
    # paylasiyor. Eylem eylem gezmek hem ayni bayragi iki kez yazar hem de "False istiyorum
    # ama elimdeki eylem store_true" diye yanlis hata verir; dogru soru "bu dest'i istenen
    # degere goturebilen bir eylem var mi".
    by_dest = {}
    for a in parser._actions:                                                # noqa: SLF001
        if a.dest == "help":
            continue
        by_dest.setdefault(a.dest, []).append(a)

    for dest, acts in by_dest.items():
        if dest not in vals:
            fell_back.append((dest, acts[0].default))
            continue
        v = vals[dest]
        store = [a for a in acts if type(a).__name__ == "_StoreAction"]
        if store:
            if v is None:
                unrepresentable.append((dest, v))
                continue
            out.append(flag_of(store[0]))
            out.extend(str(x) for x in (v if isinstance(v, (list, tuple)) else [v]))
            continue

        want = "_StoreTrueAction" if v else "_StoreFalseAction"
        hit = [a for a in acts if type(a).__name__ == want]
        if hit:
            out.append(flag_of(hit[0]))
        elif bool(acts[0].default) != bool(v):
            # Istenen degere goturebilen bayrak yok ve varsayilan da o degil: bu tarif
            # komut satirindan yeniden uretilemez. Sessizce atlamak referansi bozar.
            raise RuntimeError(f"--{dest}: {v!r} isteniyor ama bunu saglayan bayrak yok "
                               f"(varsayılan {acts[0].default!r}) — ifade edilemez")

    extra = [k for k in ra if k not in by_dest]
    roundtrip_check(parser, out, ra, overrides)
    return out, fell_back, unrepresentable, extra


def roundtrip_check(parser, argv, ra, overrides):
    """ASIL KAPI: uretilen komut satiri parser'a geri verilince referans namespace'e mi cozulur?

    Uretecin dogru bayrak adini sectigine, listeleri dogru actigina, bool eslesmelerini dogru
    kurduguna GUVENMEK yerine olcuyoruz. Referansta bulunan her anahtar, komut satiri yeniden
    ayristirildiginda ayni degeri vermeli -- kasitli degistirilenler haric. Tutmazsa uretim
    durur; sessizce sapmis bir "birebir ayni tarif" iddiasi en kotu ciktidir.
    """
    ns = vars(parser.parse_args(argv))
    want = dict(ra)
    want.update(overrides)
    bad = []
    for k, v in want.items():
        if k not in ns:
            continue
        got = ns[k]
        if isinstance(v, Path) or isinstance(got, Path):
            # `type=Path` bayraklari: run_args.json bunlari duz metin olarak sakliyor, parser
            # ise Path uretiyor. Ayni yolun iki gosterimi -- ayri ayri karsilastirilmali.
            same = v is not None and got is not None and Path(v) == Path(got)
        elif isinstance(v, (list, tuple)) or isinstance(got, (list, tuple)):
            same = list(v or []) == list(got or [])
        elif isinstance(v, bool) or isinstance(got, bool):
            same = bool(v) == bool(got)
        elif isinstance(v, (int, float)) and isinstance(got, (int, float)):
            same = abs(float(v) - float(got)) < 1e-12
        else:
            same = v == got
        if not same:
            bad.append(f"{k}: istenen {v!r} -> ayrıştırılan {got!r}")
    if bad:
        raise RuntimeError("gidiş-dönüş sınaması BAŞARISIZ (" + want.get("name", "?") + "):\n  "
                           + "\n  ".join(bad))


# --------------------------------------------------------------------------- ps1

HEADER = """param(
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
{banner}
#
# BU DOSYA ELLE YAZILMADI. Ureteci: diagnostics/build_replicate_queue.py
# Her kosunun komut satiri REFERANS KOSUNUN KENDI run_args.json'undan uretildi;
# bayrak adlari train_rafdb_kd.py'nin kendi argparse nesnesinden okundu. Boylece
# "tarif birebir ayni, yalniz {varies} degisiyor" iddiasi anlatilan degil YAPISAL.
# Uretim raporu (hangi anahtar varsayilana dustu): diagnostics/replicate_queue_build.md
#
# train_rafdb_kd.py'de --resume YOK. Kuyruk ortasinda cokerse -StartIndex ile devam et;
# YARIM KALAN KOSU DEVAM ETTIRILMEZ, temiz yeniden baslar (optimizer durumu ve veri
# sirasi temiz kosuyla ayni olmaz, karsilastirilabilirligi bozar).
# ============================================================================

$stages = @(
{stages}
)

function Invoke-Run {{
    param($Stage, [string]$StageLabel)
    $cmd = @("train_rafdb_kd.py") + $Stage.Args

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {{
        Write-Host ""
        Write-Host "########## {tag} STAGE: $StageLabel, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        # PS 5.1 tuzagi: cagiran stderr'i pipeline'a sokarsa her satir NativeCommandError
        # olur ve Stop altinda oldurucu hale gelir. timm'in FutureWarning'i G0 kuyrugunu
        # ilk kosuda bu yuzden oldurdu. Basari zaten $LASTEXITCODE'dan okunuyor.
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & python -u @cmd | Out-Host
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $prevEAP
        Write-Host "[$StageLabel] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) {{ return $true }}
        Write-Host "[$StageLabel] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }}
    return $false
}}

Write-Host "=== {tag}: $($stages.Count) kosu, index $StartIndex'ten ==="
for ($i = $StartIndex; $i -lt $stages.Count; $i++) {{
    $stage = $stages[$i]
    $ok = Invoke-Run -Stage $stage -StageLabel "$($stage.Label) (idx $i)"
    if (-not $ok) {{
        Write-Host "=== {tag}: stage $($stage.Label) (index $i) $MaxRetries denemede basarisiz. Devam: -StartIndex $i ==="
        exit 1
    }}
}}
Write-Host ""
Write-Host "=== {tag} ($($stages.Count) kosu) tamamlandi. ==="
exit 0
"""


def ps_quote(s):
    return '"' + str(s).replace('"', '`"') + '"'


def render(path, tag, banner, varies, stages):
    lines = []
    for st in stages:
        args = ", ".join(ps_quote(a) for a in st["args"])
        lines.append(f'    @{{ Label = "{st["label"]}"; Args = @({args}) }}')
    path.write_text(HEADER.format(banner=banner, stages=",\n".join(lines),
                                  tag=tag, varies=varies),
                    encoding="utf-8")


# --------------------------------------------------------------------------- jobs

BASE = "_b070_T6_224_400e_swa200"

# A12 -- gercek-sinyal gate hucreleri n=1 -> n=3. Referans = her hucrenin KENDI seed42 kosusu.
A12_CELLS = [
    ("stage1",  "mean_logvar",   f"RAFDB_stage1_gate_noclassweight{BASE}"),
    ("stage1",  "target_logvar", f"RAFDB_stage1_gate_target_logvar{BASE}"),
    ("primary", "mean_logvar",   f"RAFDB_primary_gate_noclassweight{BASE}"),
    ("primary", "target_logvar", f"RAFDB_primary_gate_target_logvar{BASE}"),
    ("vae9182", "mean_logvar",   f"RAFDB_vae9182_gate_noclassweight{BASE}"),
]
A12_NEW_SEEDS = (1, 43)

# A13 -- 2.248 M scratch doz-yaniti. Referans = w100ns (scratch, T=1.0, zaten n=3).
# Eklenen: ayni scratch ogrenci, T=1.7 ve T=2.2, iki tohum -- w050'nin tasarimiyla ayni
# sicakliklar ve ayni tohumlar, boylece iki kapasite AYNI destek uzerinde karsilastirilir.
A13_REF = f"RAFDB_vae9182_frontier_w100ns{BASE}_seed42"
A13_POINTS = [("T170", 1.7), ("T220", 2.2)]
A13_SEEDS = (42, 1)


def main():
    # Konsol cp1252; hem rapor hem hata mesajlari Turkce tasiyor. Dosyalar zaten utf-8
    # yaziliyor, kiran yalniz konsola basmak (bu tuzaga bu kampanyada uc kez dusuldu).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = training_parser()
    rep = ["# Kuyruk üretim raporu", "",
           "Üretici: `diagnostics/build_replicate_queue.py`. Her komut satırı referans "
           "koşunun kendi `run_args.json`'undan üretildi; bayrak adları "
           "`train_rafdb_kd.py`'nin argparse nesnesinden okundu.", "",
           "**Gidiş-dönüş kapısı geçildi.** Her komut satırı parser'a geri verildi ve "
           "referans namespace'e birebir çözüldüğü doğrulandı (kasıtlı değişenler hariç); "
           "tutmasaydı bu dosya hiç yazılmazdı. Yani \"tarif birebir aynı\" ölçülmüş bir "
           "ifade, anlatılan bir iddia değil.", ""]

    # ---- A12
    a12 = []
    for teacher, signal, ref in A12_CELLS:
        ra, src = ref_args(ref)
        if int(ra["seed"]) != 42:
            raise RuntimeError(f"{ref}: referans tohumu 42 değil ({ra['seed']})")
        if not ra.get("gate_enable"):
            raise RuntimeError(f"{ref}: gate_enable False — yanlış referans")
        if ra.get("gate_uncertainty_source") != signal:
            raise RuntimeError(f"{ref}: sinyal {ra.get('gate_uncertainty_source')} ≠ {signal}")
        if ra.get("class_weight_mode") != "none":
            raise RuntimeError(f"{ref}: class_weight_mode {ra.get('class_weight_mode')} ≠ none")
        for seed in A12_NEW_SEEDS:
            name = f"{ref}_seed{seed}"
            args, fb, unrep, extra = build_cmd(parser, ra, {"seed": seed, "name": name})
            a12.append({"label": f"{teacher}/{signal}/seed{seed}", "args": args})
            rep += [f"### A12 · {name}", "",
                    f"- referans: `{Path(src).relative_to(ROOT)}`",
                    f"- değişen: `seed` 42 → {seed}, `name`",
                    f"- varsayılana düşen anahtar ({len(fb)}): "
                    + (", ".join(f"`{k}`={v!r}" for k, v in fb) or "yok"),
                    f"- ifade edilemeyen (None): "
                    + (", ".join(f"`{k}`" for k, _ in unrep) or "yok"),
                    f"- parser'da olmayan run_args anahtarı: "
                    + (", ".join(f"`{k}`" for k in extra) or "yok"), ""]

    # ---- A13
    a13 = []
    ra13, src13 = ref_args(A13_REF)
    if ra13.get("student_pretrained") is not False:
        raise RuntimeError(f"{A13_REF}: student_pretrained False değil — scratch referansı değil")
    if abs(float(ra13.get("width_mult", 0)) - 1.0) > 1e-9:
        raise RuntimeError(f"{A13_REF}: width_mult 1.0 değil")
    if abs(float(ra13.get("teacher_temperature_scale", 1.0)) - 1.0) > 1e-9:
        raise RuntimeError(f"{A13_REF}: referans T=1.0 değil")
    for tag, tval in A13_POINTS:
        for seed in A13_SEEDS:
            name = f"RAFDB_vae9182_frontier_w100ns_tempscale_{tag}{BASE}_seed{seed}"
            args, fb, unrep, extra = build_cmd(
                parser, ra13,
                {"seed": seed, "name": name, "teacher_temperature_scale": tval})
            a13.append({"label": f"w100ns/{tag}/seed{seed}", "args": args})
            rep += [f"### A13 · {name}", "",
                    f"- referans: `{Path(src13).relative_to(ROOT)}`",
                    f"- değişen: `teacher_temperature_scale` 1.0 → {tval}, "
                    f"`seed` 42 → {seed}, `name`",
                    f"- varsayılana düşen anahtar ({len(fb)}): "
                    + (", ".join(f"`{k}`={v!r}" for k, v in fb) or "yok"),
                    f"- ifade edilemeyen (None): "
                    + (", ".join(f"`{k}`" for k, _ in unrep) or "yok"),
                    f"- parser'da olmayan run_args anahtarı: "
                    + (", ".join(f"`{k}`" for k in extra) or "yok"), ""]

    render(ROOT / "rafdb_a12_realsignal_gate_queue.ps1", "A12",
           "# A12 -- gercek-sinyal gate hucreleri n=1 -> n=3 (5 hucre x 2 yeni tohum = 10 kosu).\n"
           "# Panel DA-3 / R1-W12: ozet 'bes mekanizma basarisiz' diyor ama iki hucre tek tohumlu.\n"
           "# Kontrol kollari (baseline_noclassweight) zaten n=3 -- yeni kontrol kosusu YOK.",
           "tohum", a12)
    render(ROOT / "rafdb_a13_scratch_dose_queue.ps1", "A13",
           "# A13 -- 2.248 M scratch doz-yaniti (2 sicaklik x 2 tohum = 4 kosu).\n"
           "# Panel R1-W7: 76x oraninda kapasite kolu scratch, sicaklik kolu on-egitimli.\n"
           "# T=1.0 zaten var (w100ns, n=3); eksik olan T=1.7 ve T=2.2.",
           "sicaklik ve tohum", a13)

    REPORT.write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"A12: {len(a12)} kosu -> rafdb_a12_realsignal_gate_queue.ps1")
    print(f"A13: {len(a13)} kosu -> rafdb_a13_scratch_dose_queue.ps1")
    print(f"rapor: {REPORT}")


if __name__ == "__main__":
    main()
