"""Level-1 sınır geçidi: koşu dizinlerindeki örnek-başına logit önbelleklerini YAYIMLAR.

NEDEN VAR (8 Ağu 2026). Level-1 değişmezi -- "makaledeki her sayı ham koşu dizinleri
olmadan türetilebilir" -- iki üreticide kırılıydı: `robustness_metrics.py` (R3-1, yedi
metrik x 42 koşu) ve `r3w1_joint_optimum.py` (R3-W1, FERPlus ortak optimum). İkisi de
sayıyı `results/unified_students/<koşu>/<zaman>/logits_swa.npz` dosyasından üretiyordu.
Koşu dizinleri boyut yüzünden yayımlanmıyor, dolayısıyla bu iki tablo public depoda
yeniden üretilemez durumdaydı. Yol düzeltmesiyle kapanmıyordu: eksik olan dosyanın
KENDİSİydi.

KARAR (8 Ağu, onaylı). 42 dosya / 3,4 MiB yayımlanır. Sınıfı `rafdb_calibration_backfill/
logits/` ile aynı: **model çıktısı, veri kümesi içeriği değil** -- her dosya 3153 (FERPlus)
ya da 3068 (RAF-DB) satırlık logit matrisi ve etiket vektörüdür; görüntü yoktur, oy
dağılımı yoktur, dosya adı yoktur.

BU BETİK KOŞU DİZİNİ OKUR ve okumak ZORUNDADIR -- işi o. Level 3'tür, `level1_gate.ALLOWED`
içinde beyanlıdır, tıpkı `build_runs_ledger.py` gibi. Sınır tam burasıdır: bilgi bir kez
burada çıkarılır, tüketiciler bir daha koşu dizinine bakmaz.

ÖZDEŞLİK KAPISI. Kopya BAYT KOPYASIDIR, yeniden paketleme değil: kaynağın ve yayımlanan
dosyanın sha256'sı ayrı ayrı hesaplanır ve eşit olmak ZORUNDADIR. Eşit değilse betik durur.
Yeniden paketlemek `meta` alanını (koşu dizini, ckpt epoch, ece_recomputed) kaybetme ya da
kayan-nokta biçimini değiştirme riski taşırdı; bayt kopyası bu riskin ikisini de kaldırır.

TEKİLLİK KAPISI. Eskiden `robustness_metrics.rafdb_curve()` "bir koşu adına tam bir bitmiş
dizin düşmeli" kapısını kendisi koşturuyordu. Tüketici artık koşu dizinini görmediği için o
kapı BURAYA taşındı -- kaybolmadı. İki bitmiş dizni olan bir koşu adı, tohum dışında bir
değişkenin de oynadığı anlamına gelir; betik durur.

Kullanım: python diagnostics/publish_student_logits.py [--ck swa] [--force]
Çıktı  -> diagnostics/student_logits/<koşu_adı>.npz (bayt kopyası)
          diagnostics/student_logits/MANIFEST.json  (sha256 + köken defteri)
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDENTS = ROOT / "results" / "unified_students"
CACHE_DIR = ROOT / "diagnostics" / "student_logits"
MANIFEST = CACHE_DIR / "MANIFEST.json"
CK = "swa"


# --------------------------------------------------------------------------- okuma tarafı
# Bu iki fonksiyon koşu dizinine DOKUNMAZ; tüketiciler (robustness_metrics.py,
# r3w1_joint_optimum.py) yalnız bunları çağırır. Modül düzeyinde hiçbir dosya açılmaz,
# böylece Level-1 kapısı altında import etmek ihlal üretmez.

def published_npz(run_name, ck=CK):
    """Yayımlanan kopyanın yolu. Yoksa toplayıcı komutunu söyleyerek düşer."""
    p = CACHE_DIR / f"{run_name}.npz"
    if not p.exists():
        raise FileNotFoundError(
            f"{run_name}: yayımlanmış logit önbelleği yok ({p.relative_to(ROOT)}). "
            f"Önce toplayıcıyı koştur: python diagnostics/publish_student_logits.py --ck {ck}")
    return p


def manifest_entry(run_name):
    """MANIFEST'teki köken kaydı -- hangi koşu dizininden geldi, sha256'sı ne."""
    if not MANIFEST.exists():
        raise FileNotFoundError(
            f"{MANIFEST.relative_to(ROOT)} yok — python diagnostics/publish_student_logits.py")
    runs = json.loads(MANIFEST.read_text(encoding="utf-8"))["runs"]
    if run_name not in runs:
        raise KeyError(f"{run_name}: MANIFEST'te yok. Toplayıcıyı yeniden koştur.")
    return runs[run_name]


# --------------------------------------------------------------------------- yayımlama
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sources(ck):
    """{koşu_adı: kaynak npz yolu} -- TEKİLLİK KAPISI burada koşar.

    Koşu dizinlerini okur (Level 3). `metrics_best.json` taşıyan alt dizinler "bitmiş"
    sayılır; bir koşu adının npz'si varsa bitmiş dizin sayısı tam 1 olmak ZORUNDA.
    """
    out = {}
    for name_dir in sorted(STUDENTS.iterdir()):
        if not name_dir.is_dir():
            continue
        finished = [d for d in sorted(name_dir.iterdir())
                    if d.is_dir() and (d / "metrics_best.json").exists()]
        with_npz = [d for d in finished if (d / f"logits_{ck}.npz").exists()]
        if not with_npz:
            continue
        if len(finished) != 1:
            raise RuntimeError(
                f"{name_dir.name}: {len(finished)} bitmiş koşu dizini var, 1 bekleniyordu "
                f"({[d.name for d in finished]}). Aynı koşu adına iki bitmiş dizin, tohum "
                f"dışında bir değişkenin de oynadığı anlamına gelir — seçim dizin sırasına "
                f"bırakılmaz. (Bu kapı eskiden robustness_metrics.rafdb_curve() içindeydi.)")
        out[name_dir.name] = with_npz[0] / f"logits_{ck}.npz"
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ck", default=CK)
    ap.add_argument("--force", action="store_true",
                    help="özdeş olsa bile yeniden kopyala")
    args = ap.parse_args()

    src = sources(args.ck)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    import numpy as np
    runs, identical, copied, total_bytes = {}, 0, 0, 0
    for run_name, s in src.items():
        dst = CACHE_DIR / f"{run_name}.npz"
        h_src = sha256(s)
        wrote = args.force or not dst.exists() or sha256(dst) != h_src
        if wrote:
            shutil.copyfile(s, dst)
            copied += 1
        h_dst = sha256(dst)
        if h_dst != h_src:
            raise RuntimeError(
                f"{run_name}: kopya kaynakla ÖZDEŞ DEĞİL ({h_src[:12]} != {h_dst[:12]}). "
                f"Bu bir bayt kopyası olmak zorunda — durduruldu.")
        identical += 1
        total_bytes += dst.stat().st_size

        z = np.load(dst, allow_pickle=False)
        meta = json.loads(str(z["meta"]))
        runs[run_name] = {
            "published": str(dst.relative_to(ROOT)).replace("\\", "/"),
            "origin_run_dir": str(Path(meta["run_dir"]).relative_to(ROOT)).replace("\\", "/"),
            "sha256": h_src,
            "bytes": dst.stat().st_size,
            "checkpoint": meta["checkpoint"],
            "n_val": meta["n_val"],
            "acc_recomputed": meta["acc_recomputed"],
            "ece_recomputed": meta["ece_recomputed"],
            "t_scale": meta.get("t_scale"),
            "seed": meta.get("seed"),
        }
        print(f"  {'yazıldı' if wrote else 'özdeş':>8}  {run_name}")

    payload = {
        "produced_by": "diagnostics/publish_student_logits.py",
        "checkpoint": args.ck,
        "content_class": ("model output (per-sample logits + labels), not dataset content — "
                          "no images, no vote distributions, no file names"),
        "identity_gate": ("byte copy; sha256 of source and published copy computed separately "
                          "and required equal"),
        "uniqueness_gate": ("exactly one finished run dir per run name (moved here from "
                            "robustness_metrics.rafdb_curve on 8 Aug 2026)"),
        "consumers": ["diagnostics/robustness_metrics.py", "diagnostics/r3w1_joint_optimum.py"],
        "total": len(runs),
        "identical": identical,
        "copied_this_run": copied,
        "total_bytes": total_bytes,
        "runs": runs,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  sha256 ÖZDEŞLİK: {identical}/{len(src)}")
    print(f"  toplam {len(runs)} dosya · {total_bytes:,} bayt "
          f"({total_bytes / 1024 / 1024:.2f} MiB) · bu koşuda {copied} kopyalandı")
    print(f"  defter -> {MANIFEST.relative_to(ROOT)}")
    return 0 if identical == len(src) else 1


if __name__ == "__main__":
    sys.exit(main())
