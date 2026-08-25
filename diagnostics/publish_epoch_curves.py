"""Level-1 sınır geçidi: epok-başına doğrulama eğrilerini YAYIMLAR.

NEDEN VAR (9 Ağu 2026). Level-1 kapısının harness'ı düzeltilince (`glob` sarmalayıcısı,
`parse_args`, konsol kodlaması, `sys.path`) `başka hata` sütunu 9'dan 0'a indi ve arkasından
iki GERÇEK ihlal çıktı:

  · `order_stat_trend.py`          -- donmuş denetimin 131 koşusunun `training_log.csv`'sinden
                                      epok-başına `val_acc` serisi (sıra istatistiği, K=50/100)
  · `selection_gain_estimator.py`  -- RAF-DB'nin bitmiş koşularının `val_acc` + `val_loss`
                                      serileri (seçim kazancı, val-NLL vekili)

İkisi de 8 Ağu'da da ihlaldi; GÖRÜNMÜYORLARDI çünkü kapı o iki betiği hiç koşturamıyordu.
"İHLAL 0" kısmen sorulmamış sorulara dayanıyordu. Yol düzeltmesiyle kapanmıyordu: eksik olan
dosyanın kendisiydi.

KARAR (9 Ağu, onaylı, Fatih). Eğriler yayımlanır. Sınıfı `student_logits/` ile aynı: **model
çıktısı, veri kümesi içeriği değil** -- her koşu için üç dizi (epok numarası, o epoktaki
doğrulama doğruluğu, o epoktaki doğrulama kaybı). Görüntü yok, etiket yok, dosya adı yok.

BİÇİM SEÇİMİ ÖLÇÜLEREK YAPILDI, 126.200 epok satırı için:
  · 216 tam `training_log.csv` (10 sütun)      15.599.427 bayt (14,88 MiB)
  · 3 sütunlu tek CSV                          14.985.525 bayt (14,29 MiB)  <- ad her satırda
  · aynısı gzip                                 2.273.314 bayt ( 2,17 MiB)
  · koşu başına dizi, sıkıştırılmış .npz          761.408 bayt ( 0,73 MiB)  <- SEÇİLEN
Son biçim 42 logit önbelleği partisinden (3,4 MiB) küçük ve deponun zaten kullandığı biçim.

`float64` ŞART, `float32` DEĞİL -- ve bu varsayımla değil ÖLÇÜMLE bulundu. İlk sürüm
`float32` yazdı; iki tüketicinin çıktısı da oynadı ve iki farklı büyüklükte oynadı:
  · `a2_raw` gibi ortalamalar 7. haneden kaydı (0,6445305843 -> 0,6445301854). Küçük, ama bu
    kampanyanın ölçütü bayt-özdeşlik;
  · `argmax_in_last_K_frac` K=50'de 0,3417'den 0,3266'ya, K=100'de 0,6482'den 0,6281'e
    düştü -- 1,5-2 puan. Sebep: `training_log.csv` `val_acc`'i tam float64 gösterimiyle
    yazıyor (`81.28766245165968`); `float32`'ye indirince ayrı olan değerler EŞİTLENİYOR ve
    `acc.index(max(acc))` daha ERKEN bir epoku seçiyor. Yani hassasiyet kaybı bir ortalamayı
    değil bir SEÇİMİ değiştirdi, ve onunla birlikte `loss[gargmax]`'i de.
Ders, 42 npz'yi bayt kopyası tutma gerekçesinin aynısı: sayı üreten bir dosyayı yeniden
paketlemek "sadece biçim" değildir.

BU BETİK KOŞU DİZİNİ OKUR ve okumak ZORUNDADIR -- işi o. Level 3'tür, `level1_gate.ALLOWED`
içinde beyanlıdır, `build_runs_ledger.py` ve `publish_student_logits.py` gibi.

POPÜLASYON İKİ TÜKETİCİNİN BİRLEŞİMİDİR ve buradan türetilir, elle yazılmaz:
donmuş denetim (`selection_audit.csv`'nin koşu dizinleri) ∪ RAF-DB'nin bitmiş koşuları.
Böylece "hangi koşular yayımlandı" sorusu tüketicilerin kendi tanımlarına bağlı kalır.

Kullanım: python diagnostics/publish_epoch_curves.py
Çıktı  -> diagnostics/epoch_curves.npz            (koşu başına 3 dizi)
          diagnostics/epoch_curves_MANIFEST.json  (köken + satır sayıları + sha256)
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDENTS = ROOT / "results" / "unified_students"
AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
OUT_NPZ = ROOT / "diagnostics" / "epoch_curves.npz"
OUT_MAN = ROOT / "diagnostics" / "epoch_curves_MANIFEST.json"

COLS = ("epoch", "val_acc", "val_loss")


# --------------------------------------------------------------------------- okuma tarafı
# Tüketiciler YALNIZ bunu çağırır; koşu dizinine dokunulmaz. Modül düzeyinde hiçbir dosya
# açılmaz, böylece Level-1 kapısı altında import etmek ihlal üretmez.

def load(run_name, timestamp):
    """(epoch, val_acc, val_loss) — yayımlanan diziden. Yoksa toplayıcı komutunu söyler."""
    z = _blob()
    key = f"{run_name}|{timestamp}"
    if f"{key}|epoch" not in z:
        raise KeyError(
            f"{key}: yayımlanan epok eğrisi yok. Toplayıcıyı koştur: "
            f"python diagnostics/publish_epoch_curves.py")
    return tuple(z[f"{key}|{c}"] for c in COLS)


def has(run_name, timestamp):
    return f"{run_name}|{timestamp}|epoch" in _blob()


_CACHE = {}


def _blob():
    if "z" not in _CACHE:
        if not OUT_NPZ.exists():
            raise FileNotFoundError(
                f"{OUT_NPZ.relative_to(ROOT)} yok — "
                f"python diagnostics/publish_epoch_curves.py")
        _CACHE["z"] = np.load(OUT_NPZ, allow_pickle=False)
    return _CACHE["z"]


# --------------------------------------------------------------------------- yayımlama
def frozen_dirs():
    """Donmuş denetimin koşu dizinleri — `order_stat_trend.frozen_run_dirs()` ile aynı kural."""
    return {Path(r["run_dir"]) for r in csv.DictReader(open(AUDIT, encoding="utf-8"))}


def rafdb_dirs():
    """RAF-DB'nin bitmiş koşuları — `selection_gain_estimator` ile aynı filtre.

    `metrics_best.json`'daki `dataset` alanı normalize edilerek RAFDB'ye eşitlenir; oradaki
    ifadenin birebir kopyası, çünkü iki betiğin popülasyonu ayrışırsa yayımlanan küme
    tüketicilerden biri için eksik kalır.
    """
    out = set()
    for rn in sorted(STUDENTS.iterdir()):
        if not rn.is_dir():
            continue
        for ts in sorted(rn.iterdir()):
            mb, tl = ts / "metrics_best.json", ts / "training_log.csv"
            if not (ts.is_dir() and mb.exists() and tl.exists()):
                continue
            try:
                ds = str(json.loads(mb.read_text()).get("dataset", ""))
            except (OSError, ValueError):
                continue
            if ds.upper().replace("-", "") == "RAFDB":
                out.add(ts)
    return out


def series(log_path):
    ep, va, vl = [], [], []
    for r in csv.DictReader(open(log_path, encoding="utf-8")):
        try:
            e, a, l = int(r["epoch"]), float(r["val_acc"]), float(r["val_loss"])
        except (KeyError, ValueError):
            continue
        ep.append(e)
        va.append(a)
        vl.append(l)
    # float64: bkz. modül başlığı. float32 `argmax_in_last_K_frac`'i 1,5-2 puan oynatıyordu.
    return (np.asarray(ep, dtype=np.int32),
            np.asarray(va, dtype=np.float64),
            np.asarray(vl, dtype=np.float64))


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    frozen, rafdb = frozen_dirs(), rafdb_dirs()
    need = sorted(frozen | rafdb)
    arrs, runs, rows_total = {}, {}, 0
    for d in need:
        tl = d / "training_log.csv"
        if not tl.exists():
            raise FileNotFoundError(f"{d}: training_log.csv yok — popülasyon tanımı tutmuyor")
        ep, va, vl = series(tl)
        key = f"{d.parent.name}|{d.name}"
        for c, arr in zip(COLS, (ep, va, vl)):
            arrs[f"{key}|{c}"] = arr
        rows_total += ep.size
        runs[key] = {
            "run_name": d.parent.name, "timestamp": d.name,
            "origin_run_dir": str(d.relative_to(ROOT)).replace("\\", "/"),
            "epochs": int(ep.size),
            "in_frozen_audit": d in frozen,
            "in_rafdb_finished": d in rafdb,
        }

    np.savez_compressed(OUT_NPZ, **arrs)
    h = hashlib.sha256(OUT_NPZ.read_bytes()).hexdigest()
    size = OUT_NPZ.stat().st_size

    OUT_MAN.write_text(json.dumps({
        "produced_by": "diagnostics/publish_epoch_curves.py",
        "content_class": ("model output (per-epoch validation accuracy and loss), not dataset "
                          "content — no images, no labels, no file names"),
        "arrays_per_run": list(COLS),
        "dtypes": {"epoch": "int32", "val_acc": "float64", "val_loss": "float64"},
        "dtype_note": ("float64 is required, not a preference: float32 ties distinct val_acc "
                       "values, which moves acc.index(max(acc)) to an earlier epoch and "
                       "shifted argmax_in_last_K_frac by 1.5-2 points (measured, 9 Aug)"),
        "population": ("frozen selection audit run dirs UNION RAF-DB finished runs — derived "
                       "from the two consumers' own definitions, never hand-listed"),
        "consumers": ["diagnostics/order_stat_trend.py",
                      "diagnostics/selection_gain_estimator.py"],
        "n_runs": len(runs),
        "n_frozen_audit": sum(1 for r in runs.values() if r["in_frozen_audit"]),
        "n_rafdb_finished": sum(1 for r in runs.values() if r["in_rafdb_finished"]),
        "n_epoch_rows": rows_total,
        "npz_bytes": size,
        "npz_sha256": h,
        "runs": runs,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  koşu           : {len(runs)}  (donmuş denetim "
          f"{sum(1 for r in runs.values() if r['in_frozen_audit'])} ∪ RAF-DB bitmiş "
          f"{sum(1 for r in runs.values() if r['in_rafdb_finished'])})")
    print(f"  epok satırı    : {rows_total:,}  ·  dizi {len(arrs)}")
    print(f"  {OUT_NPZ.name:<24s}: {size:,} bayt ({size / 1024 / 1024:.2f} MiB)")
    print(f"  sha256         : {h}")
    print(f"  defter         -> {OUT_MAN.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
