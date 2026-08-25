"""N16 — `requirements.txt` ÜRETİCİSİ: elle yazılmış bir iddia değil, ölçülmüş bir çıktı.

NEDEN. Deponun eski `requirements_27may.txt` dosyası elle yazılmış ve SÜRÜMSÜZ bir listeydi
(`torch`, `numpy`, ...). Böyle bir dosya bir beyandır: "bunlar gerekiyor" der ama neyle koştuğumuzu
söylemez, ve yanlış olduğunda hiçbir şey bağırmaz. Level-1 kuralının kendisi burada da geçerli:
bir dosya bir üreticinin ÇIKTISI olmalı.

TANIM — hangi paket girer, açıkça:
  1. Deponun kendi `.py` dosyaları taranır ve TOP-LEVEL import adları toplanır.
  2. Standart kütüphane ve deponun kendi modülleri (`diagnostics/`, `models/`, `utils/`, ...)
     düşülür.
  3. Kalan her import adı, KURULU dağıtıma `importlib.metadata.packages_distributions()` ile
     eşlenir -- `cv2 -> opencv-python`, `PIL -> pillow`, `yaml -> PyYAML` gibi eşlemeler
     böylece elle yazılmaz, ölçülür.
  4. Sürüm, o anda KURULU olan sürümdür ve `==` ile sabitlenir.

Eşlenemeyen import adı SESSİZCE ATILMAZ: dosyanın altına `# eşlenemedi:` diye yazılır.
"Bulunamadı" yazmak, tahmin etmekten iyidir. ÇIKIŞ KODU YİNE DE 0'dır ve gerekçesi main()'in
sonunda yazılı: eşlenememiş isteğe bağlı bir bağımlılık, üreticinin çalışmaması değildir.

18 Ağu 2026: `requirements_27may.txt` Fatih'in kararıyla depodan SİLİNDİ (iki requirements
dosyası hakemi hangisinin geçerli olduğu konusunda tereddütte bırakır -- "aynı ad, iki nicelik"
kalıbının dosya seviyesindeki hâli). Ona atıf yapan üç yaşayan dosya (`README_27MAY_RAFDB.md`,
`README_27MAY_REPRODUCTION.md`, `tools/build_repro_export.py`) `requirements.txt`e çevrildi;
TARİHLİ kayıtlardaki (raporlar, `STATUS.md`) atıflar o günün gerçeği olduğu için değiştirilmedi.

24 Ağu 2026 — İKİ DÜZELTME, ikisi de ÖLÇÜLMÜŞ bir arızadan:

  (a) `pip install -r requirements.txt` ÇALIŞMIYORDU. `torch==2.10.0+cu128` ve
      `torchvision==0.25.0+cu128` PyPI'de yok; bu tekerlekler yalnız PyTorch'un kendi
      dizininde durur. README'nin Level-1 için verdiği ilk komut bir hakemin elinde
      "No matching distribution" ile düşerdi. Dosya artık `--extra-index-url` satırını
      da BASAR ve URL elle yazılmaz: sürümün yerel etiketinden (`+cu128`) türetilir.

  (b) README "çözümleme katmanı yalnız CPU bloğuna ihtiyaç duyar" diyordu; öyle bir
      blok YOKTU. Artık var: `requirements-level1.txt`. TANIMI için `L1_ENTRIES`e bak
      -- ve o tanımın İLK HÂLİ YANLIŞTI; neden yanlış olduğu ve nasıl yakalandığı orada
      yazılı. `torch` DÜŞMÜYOR: kapanışta olduğu için var, GPU istendiği için değil.
      CPU dosyasında yerel etiket (`+cu128`) SİLİNİR — PEP 440'a göre `==2.10.0`
      her `2.10.0+*` yapıyla eşleşir, `==2.10.0+cu128` yalnız CUDA'yla.

Salt-okunur (yalnız `requirements.txt` ve `requirements-level1.txt` yazar), GPU yok.
Kullanım: python diagnostics/requirements_lock.py [--check]
Çıktı -> requirements.txt, requirements-level1.txt
"""
import argparse
import ast
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "requirements.txt"
OUT_L1 = ROOT / "requirements-level1.txt"

# Level-1 TANIMI: README'nin Level-1 için verdiği İKİ komutun GEÇİŞLİ import kapanışı.
#
# 24 Ağu 2026, ikinci deneme. İlk tanım `diagnostics/*.py` glob'uydu ve YANLIŞTI --
# TEK SIÇRAMA. Ürettiği dosyayla kurulan bir ortamda Level-1 giriş noktası ÇÖKÜYOR;
# yayım öncesi denetimde yakalandı ve blokçu bir `sys.meta_path` ile yeniden üretildi:
#
#   paper_tables.py:1413 main() -> :1370 r3_sections() -> :410 calibration_metrics
#     -> calibration_metrics.py:41 -> teacher_temperature_scaling_fit.py:38
#     -> train_rafdb_kd.py:14  import cv2   ->  ModuleNotFoundError: 'cv2'
#
# `train_rafdb_kd` deponun KENDİ modülü olduğu için glob onu üçüncü-parti saymıyor ve
# ORADAN ÇIKAN cv2/tqdm/timm/thop hiç görünmüyordu. Ders v1.0.2'nin dersiyle aynı, bir
# katman derinde: "hangi paketler gerekiyor" bir GLOB'la değil, İZLEYEREK ölçülür.
#
# Kapanış statiktir, yani ÜST kümedir: hiç çağrılmayan bir fonksiyonun içindeki import
# da sayılır. Bir kurulum dosyası için doğru yön budur -- fazladan bir paket kurulur,
# eksik bir paket koşuyu düşürür.
L1_ENTRIES = ("diagnostics/paper_tables.py", "diagnostics/table_diff_gate.py")

# Deponun KENDİ modülleri ÖLÇÜLEREK bulunur, elle listelenmez. Betikler `sys.path`e
# `diagnostics/` ekliyor, dolayısıyla `import stats_convention` yerel bir modüldür; elle
# tutulan bir liste bunları kaçırır ve hepsi "eşlenemedi" diye görünürdü (ilk koşuda tam
# olarak bu oldu: 40 satırın 37'si aslında kendi dosyalarımızdı).
SYS_PATH_DIRS = ("", "diagnostics", "tools", "utils", "models", "dataset_utils", "trails",
                 "trials")

SKIP_DIRS = {".git", "__pycache__", "results", "data", "dataset_cache", "checkpoints",
             "pretrained", "swanlog", "run_logs", "launcher_logs", "pipeline_logs",
             "evaluation_runs", "reference_90_74", "kd_logs_rafdb", "kd_logs_affectnet8",
             "kd_logs_rafdb_multiseed", "kd_logs_rafdb_newrecipe_lightle_swa",
             "kd_logs_rafdb_newrecipe_noerasing", "kd_logs_rafdb_phase0_smoke", "paper",
             "reports"}


def local_names():
    """Depoda modül/paket olarak ÇÖZÜLEBİLEN adlar. Betiklerin `sys.path`e eklediği dizinler
    dolaşılır; oradaki her `x.py` ve her paket dizini yerel bir import adıdır."""
    out = set()
    for d in SYS_PATH_DIRS:
        base = ROOT / d if d else ROOT
        if not base.is_dir():
            continue
        for p in base.iterdir():
            if p.suffix == ".py":
                out.add(p.stem)
            elif p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith("."):
                out.add(p.name)
    return out


def local_paths():
    """Yerel import adı -> dosya yolu. `local_names()` yalnız ADLARI veriyor; kapanışı
    yürümek için hangi dosyaya gidileceği de lazım."""
    out = {}
    for d in SYS_PATH_DIRS:
        base = ROOT / d if d else ROOT
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.suffix == ".py":
                out.setdefault(p.stem, p)
            elif p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith("."):
                init = p / "__init__.py"
                if init.exists():
                    out.setdefault(p.name, init)
    return out


def file_imports(path):
    """Tek dosyanın top-level import adları (fonksiyon içindekiler DAHİL -- `ast.walk`)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            out.append((node.module or "").split(".")[0])
    return [n for n in out if n]


def l1_third_party():
    """Level-1 giriş noktalarından GEÇİŞLİ kapanış -> {üçüncü-parti import adı: [dosya]}.

    Yerel bir ada rastlayınca o dosyaya İNER. Çözülemeyen yerel ad sessizce atlanır:
    `export_to_drive` public depoda yok ve orada da doğru cevabı vermek gerekiyor."""
    lp = local_paths()
    seen, third = set(), {}
    stack = [ROOT / e for e in L1_ENTRIES]
    while stack:
        f = stack.pop()
        if f in seen or not f.exists():
            continue
        seen.add(f)
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        for n in file_imports(f):
            if n in sys.stdlib_module_names:
                continue
            if n in lp:
                stack.append(lp[n])
            else:
                third.setdefault(n, []).append(rel)
    return third, len(seen)


def top_imports():
    """Deponun `.py` dosyalarındaki top-level import adları -> {ad: [dosya, ...]}."""
    local = local_names()
    found = {}
    for p in sorted(ROOT.rglob("*.py")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                # `from . import x` -> level>0, deponun kendisi
                names = [] if node.level else [(node.module or "").split(".")[0]]
            else:
                continue
            for n in names:
                if n and n not in sys.stdlib_module_names and n not in local:
                    found.setdefault(n, []).append(str(rel).replace("\\", "/"))
    return found


def index_lines(dists, cpu=False):
    """Yerel sürüm etiketi (`2.10.0+cu128` -> `cu128`) taşıyan pin varsa, o tekerleğin
    hangi dizinden geldiğini SÖYLE. URL elle yazılmıyor: etiket URL'nin son parçasıdır.
    `cpu=True` ise etiket `cpu`ya çevrilir -- çözümleme katmanı CUDA istemiyor."""
    labels = sorted({v.split("+", 1)[1] for v in dists.values() if "+" in v})
    if not labels:
        return []
    tag = "cpu" if cpu else (labels[0] if len(labels) == 1 else None)
    if tag is None:
        return ["# UYARI: birden çok yerel etiket (%s); dizin satırı YAZILMADI." %
                ", ".join(labels)]
    return ["# Aşağıdaki pin'lerden bazıları PyPI'de YOK (yerel etiket: %s)." %
            ", ".join(labels),
            "# Bu satır olmadan `pip install -r` \"No matching distribution\" ile düşer.",
            "--extra-index-url https://download.pytorch.org/whl/" + tag, ""]


def strip_local(v):
    """`2.10.0+cu128` -> `2.10.0`. PEP 440: `==2.10.0` her yerel etiketle eşleşir."""
    return v.split("+", 1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="yazma, yalnız depodaki dosyayla karşılaştır")
    args, _unknown = ap.parse_known_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    imports = top_imports()
    pkgmap = metadata.packages_distributions()
    dists, unmapped = {}, {}
    for name, files in sorted(imports.items()):
        cands = pkgmap.get(name)
        if not cands:
            unmapped[name] = sorted(set(files))[:3]
            continue
        for d in cands:
            try:
                dists[d] = metadata.version(d)
            except metadata.PackageNotFoundError:
                unmapped[name] = sorted(set(files))[:3]

    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    L = ["# ÜRETİLDİ — elle düzenlemeyin.",
         "# Üretici: diagnostics/requirements_lock.py",
         "# Tanım: deponun .py dosyalarındaki top-level import adları -> kurulu dağıtım",
         "#        (importlib.metadata.packages_distributions), sürüm o anda KURULU olan.",
         f"# Python: {py}",
         f"# Taranan import adı: {len(imports)} · eşlenen dağıtım: {len(dists)}", ""]
    L += index_lines(dists)
    L += [f"{d}=={v}" for d, v in sorted(dists.items(), key=lambda kv: kv[0].lower())]
    if unmapped:
        L += ["", "# eşlenemedi (kurulu bir dağıtıma bağlanamayan import adları):"]
        L += [f"#   {n}  <- {', '.join(f)}" for n, f in sorted(unmapped.items())]
    text = "\n".join(L) + "\n"

    # --- Level-1 alt kümesi: giriş noktalarının GEÇİŞLİ kapanışı ---
    l1_third, l1_files = l1_third_party()
    l1, l1_unmapped = {}, {}
    for n in sorted(l1_third):
        cands = [d for d in (pkgmap.get(n) or []) if d in dists]
        if not cands:
            l1_unmapped[n] = sorted(set(l1_third[n]))[:2]
            continue
        for d in cands:
            l1[d] = dists[d]
    L1 = ["# ÜRETİLDİ — elle düzenlemeyin.",
          "# Üretici: diagnostics/requirements_lock.py",
          "# Tanım: README'nin Level-1 için verdiği iki komutun GEÇİŞLİ import kapanışı",
          f"#        ({' + '.join(L1_ENTRIES)}), yerel modüllere inilerek.",
          f"# Python: {py}",
          f"# Kapanış: {l1_files} yerel dosya · {len(l1)} dağıtım",
          f"# Tam ortamdan düşen: "
          f"{', '.join(sorted(set(dists) - set(l1), key=str.lower)) or 'yok'}",
          "# CUDA gerekmez: `torch` kapanışta olduğu için var, GPU istendiği için değil;",
          "# yerel etiket silindi (bkz. üreticinin başlığı).", ""]
    if l1_unmapped:
        L1 += ["# eşlenemedi (kapanışta olup kurulu bir dağıtıma bağlanamayan adlar):"]
        L1 += [f"#   {n}  <- {', '.join(f)}" for n, f in sorted(l1_unmapped.items())]
        L1 += [""]
    L1 += index_lines(l1, cpu=True)
    L1 += [f"{d}=={strip_local(v)}" for d, v in sorted(l1.items(), key=lambda kv: kv[0].lower())]
    text_l1 = "\n".join(L1) + "\n"

    if args.check:
        cur = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        cur1 = OUT_L1.read_text(encoding="utf-8") if OUT_L1.exists() else ""
        same, same1 = cur == text, cur1 == text_l1
        print(f"requirements.txt {'AYNI' if same else 'AYRIŞMIŞ'}")
        print(f"requirements-level1.txt {'AYNI' if same1 else 'AYRIŞMIŞ'}")
        return 0 if (same and same1) else 1

    OUT_L1.write_text(text_l1, encoding="utf-8")
    print(f"{len(l1)} dağıtım (Level-1 alt kümesi) -> {OUT_L1.relative_to(ROOT)}")
    OUT.write_text(text, encoding="utf-8")
    print(f"{len(dists)} dağıtım sabitlendi -> {OUT.relative_to(ROOT)}  (Python {py})")
    for d, v in sorted(dists.items(), key=lambda kv: kv[0].lower()):
        print(f"  {d}=={v}")
    if unmapped:
        # ÇIKIŞ KODU 0. Eşlenememiş bir import adı bu ÜRETİCİNİN hatası değil, kaydedilecek bir
        # OLGUDUR ve olgu dosyanın içine yazıldı. Burada 1 dönmek, "üç isteğe bağlı bağımlılık
        # kurulu değil" ile "üretici çalışmadı"yı aynı sinyale bindirirdi -- ve Level-1 kapısı
        # bu betiği "başka hata" diye sınıflardı.
        print(f"\n  EŞLENEMEDİ {len(unmapped)} (dosyaya yazıldı, çıkış kodu 0):")
        for n, f in sorted(unmapped.items()):
            print(f"    {n}  <- {', '.join(f)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
