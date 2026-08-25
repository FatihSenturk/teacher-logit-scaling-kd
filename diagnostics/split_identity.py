"""Bölme kimliği: "aynı küme, dört ad" sorusuna ÖLÇÜLMÜŞ tek denklem.

NEDEN VAR (19 Ağu 2026, okuma turu 1). Makale ve depo aynı kümeyi dört ayrı adla anıyordu:
"RAF-DB's official test set" · "the reporting set" · "best validation accuracy" ·
"fold-3 validation split (n=3068)". Adlardan hangisinin DOĞRU olduğu bir üslup sorusu değil,
ölçülebilir bir olgudur: fold 3 gerçekten RAF-DB'nin resmî test bölümü müdür, ve seçim ile
raporlama gerçekten aynı bölmede mi yapılıyor? Bu betik o soruyu VERİDEN cevaplar.

Adı yazmak yetmezdi: bir raporda elle yazılmış tablo bir İDDİADIR. Kampanyanın kendi kuralı --
"dosya bir üreticinin çıktısı olmalı, iddianın değil" -- burada da geçerli; bu yüzden sayılar
bir artefakta çıkıyor ve deftere bağlanabiliyor.

ÖLÇÜLEN (ve ölçülmeyen). Ölçülen: her veri kümesi için fold->örnek sayısı, fold'ların hangi
resmî bölüme (dizin öneki) karşılık geldiği, raporlanan bölmenin sınıf dağılımı, ve eğitim
betiğinin BEYAN ETTİĞİ fold seçimi. Ölçülmeyen: adların makalede nerede geçtiği -- o bir metin
taramasıdır ve `paper_number_scan` tarafında durur.

LEVEL-1 ve LİSANS. RAF-DB'nin meta CSV'si GÖRÜNTÜ ADI taşır ve yayımlanamaz (RAF-DB lisansı:
"no part available to a third party"). Bu yüzden varsayılan yol CSV'yi OKUMAZ; yayımlanmış
SAYIM dosyasını okur (`split_identity/rafdb_fold_class_counts.json` -- yalnız fold x etiket
sayıları ve dizin-öneki sayıları; tek bir görüntü adı yoktur). CSV'yi okuyup o sayım dosyasını
tazelemek AÇIK bir eylemdir: `--from-data`. Aynı desen `ferplus_student_jsd.py`de kurulmuştu.
FERPlus'ın meta CSV'leri zaten public depoda izleniyor, dolayısıyla doğrudan okunur.

Kullanım: python diagnostics/split_identity.py [--from-data]
Çıktı  -> diagnostics/paper_tables/split_identity.{md,json}
          diagnostics/split_identity/rafdb_fold_class_counts.json   (yalnız --from-data ile yazılır)
"""
import argparse
import ast
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
PUB_DIR = ROOT / "diagnostics" / "split_identity"
RAFDB_COUNTS = PUB_DIR / "rafdb_fold_class_counts.json"

RAFDB_META = ROOT / "data" / "rafdb_aligned" / "metadata_rafdb_poster_var.csv"
FER_MAJORITY = ROOT / "configs" / "FERPlus_majority_metadata.csv"
FER_CREATED = ROOT / "configs" / "FERPlus_Created_metadata.csv"

RAFDB_KD = ROOT / "train_rafdb_kd.py"
FER_KD = ROOT / "train_ferplus_kd.py"
FER_TEACHER_CFG = ROOT / "configs" / "FERPlus_8_vich_teacher_vae_ce_kld.yaml"

# RAF-DB'nin YAYIMLANMIŞ resmî test dağılımı (Li et al., RAF-DB). Kaynak sabit olarak burada
# duruyor çünkü makale "per-class counts match the published distribution exactly" diyor ve bu
# cümlenin doğrulanabilir olması için karşılaştırılacak bir referans gerekiyor. Bu bir ÖLÇÜM
# DEĞİL, BEYANDIR ve öyle etiketlenir; ölçüm onunla karşılaştırılan taraftır.
RAFDB_PUBLISHED_TEST = {"Surprise": 329, "Fear": 74, "Disgust": 160, "Happiness": 1185,
                        "Sadness": 478, "Anger": 162, "Neutral": 680}
RAFDB_LABEL_NAMES = {0: "Surprise", 1: "Fear", 2: "Disgust", 3: "Happiness",
                     4: "Sadness", 5: "Anger", 6: "Neutral"}


def argparse_default(path, flag):
    """Bir betiğin `add_argument("<flag>", ..., default=<sabit>)` varsayılanını AST ile okur.

    Regex yerine AST: `--val-folds` varsayılanı makalenin raporladığı bölmeyi belirleyen tek
    beyandır; onu yorumlayarak değil, ayrıştırarak okumak gerekir. Bulunamazsa DURUR -- sessizce
    None dönmek, "bulunamadı"yı "yok" diye yazmak olurdu.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument" and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == flag):
            for kw in node.keywords:
                if kw.arg == "default":
                    return ast.literal_eval(kw.value)
    raise RuntimeError(f"{path.name}: `{flag}` icin default bulunamadi (AST). "
                       f"Beyan degismis olabilir; sayiyi tahmin etmektense DURUYORUZ.")


def assigned_constant(path, name):
    """`args.<name> = <sabit>` ya da `<name> = <sabit>` atamasini AST ile okur."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                got = t.attr if isinstance(t, ast.Attribute) else getattr(t, "id", None)
                if got == name:
                    return node.value.value
    raise RuntimeError(f"{path.name}: `{name}` atamasi bulunamadi (AST).")


def yaml_scalar_list(path, key):
    """Basit `key: [a, b]` / `key: a` satirini okur (utils/configs.py'nin duz setattr'i gibi)."""
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.split("#", 1)[0].strip()
        if s.startswith(key + ":"):
            v = s[len(key) + 1:].strip()
            return ast.literal_eval(v) if v.startswith("[") else ast.literal_eval(v)
    raise RuntimeError(f"{path.name}: `{key}` satiri bulunamadi.")


def read_meta(path, label_col="label", fold_col="fold", path_col="path"):
    """CSV -> [(fold, label, ilk_yol_bileseni)] sayimlari. Goruntu ADI DISARI CIKMAZ."""
    by_fold, prefix, per_class, n = Counter(), {}, {}, 0
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            f, lab = int(r[fold_col]), int(r[label_col])
            p = r[path_col].replace("\\", "/").split("/")[0]
            by_fold[f] += 1
            prefix.setdefault(f, Counter())[p] += 1
            per_class.setdefault(f, Counter())[lab] += 1
            n += 1
    return {"rows_total": n,
            "by_fold": {str(k): v for k, v in sorted(by_fold.items())},
            "prefix_by_fold": {str(k): dict(sorted(v.items())) for k, v in sorted(prefix.items())},
            "per_class_by_fold": {str(k): {str(a): b for a, b in sorted(v.items())}
                                  for k, v in sorted(per_class.items())}}


def rafdb_counts(from_data):
    if from_data:
        if not RAFDB_META.exists():
            raise RuntimeError(f"--from-data verildi ama {RAFDB_META} yok.")
        c = read_meta(RAFDB_META)
        c["source"] = str(RAFDB_META.relative_to(ROOT)).replace("\\", "/")
        PUB_DIR.mkdir(parents=True, exist_ok=True)
        RAFDB_COUNTS.write_text(json.dumps(c, indent=2) + "\n", encoding="utf-8")
        print(f"[--from-data] sayimlar tazelendi -> {RAFDB_COUNTS.relative_to(ROOT)}")
        return c
    if not RAFDB_COUNTS.exists():
        raise RuntimeError(
            f"{RAFDB_COUNTS.relative_to(ROOT)} yok. RAF-DB meta CSV'si goruntu adi tasidigi icin "
            f"yayimlanamaz; sayimlar bir kez `--from-data` ile uretilip yayimlanir.")
    return json.loads(RAFDB_COUNTS.read_text(encoding="utf-8"))


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-data", action="store_true",
                    help="RAF-DB meta CSV'sini oku ve yayimlanan sayim dosyasini tazele")
    args, _unknown = ap.parse_known_args()

    # ---------------- RAF-DB ----------------
    rc = rafdb_counts(args.from_data)
    r_train = argparse_default(RAFDB_KD, "--train-folds")
    r_val = argparse_default(RAFDB_KD, "--val-folds")
    if len(r_val) != 1:
        raise RuntimeError(f"RAF-DB val_folds tek fold degil: {r_val}")
    r_vf, r_tf = str(r_val[0]), str(r_train[0])
    r_report = rc["by_fold"][r_vf]
    r_prefix = rc["prefix_by_fold"][r_vf]
    # Resmi bolum kimligi: raporlanan fold'un HER satiri ayni dizin onekinde mi?
    r_official = max(r_prefix, key=r_prefix.get)
    r_pure = len(r_prefix) == 1
    r_named = {RAFDB_LABEL_NAMES[int(k)]: v for k, v in rc["per_class_by_fold"][r_vf].items()}
    r_match = r_named == RAFDB_PUBLISHED_TEST

    # ---------------- FERPlus ----------------
    fc_major = read_meta(FER_MAJORITY)
    fc_created = read_meta(FER_CREATED)
    f_train = yaml_scalar_list(FER_TEACHER_CFG, "train_folds")
    f_val = yaml_scalar_list(FER_TEACHER_CFG, "val_folds")
    f_vf = str(f_val[0])
    f_report = fc_major["by_fold"][f_vf]
    f_train_n = sum(fc_major["by_fold"][str(k)] for k in f_train)
    # Eğitim betiği bu iki sayıyı SERT BEYAN ediyor; ölçüm onunla karşılaştırılır.
    f_exp_val = assigned_constant(FER_KD, "expected_val_samples")
    f_exp_train = assigned_constant(FER_KD, "expected_train_samples")

    payload = {
        "note": "olculdu, beyan edilmedi; adlandirma karari makale tarafinda verilir",
        "datasets": {
            "RAF-DB": {
                "counts_source": rc.get("source", str(RAFDB_META.relative_to(ROOT))
                                        .replace("\\", "/")),
                "rows_total": rc["rows_total"],
                "by_fold": rc["by_fold"],
                "train_folds": r_train, "val_folds": r_val,
                "n_train": rc["by_fold"][r_tf], "n_reporting": r_report,
                "reporting_fold_prefixes": r_prefix,
                "reporting_partition": r_official,
                "reporting_fold_is_single_partition": r_pure,
                "reporting_per_class": r_named,
                "published_test_distribution": RAFDB_PUBLISHED_TEST,
                "per_class_matches_published": r_match,
                "n_partitions_in_metadata": len(rc["by_fold"]),
                "selection_set_is_reporting_set": True,
                "separate_holdout_exists": len(rc["by_fold"]) > 2,
                "selection_evidence": "train_rafdb_kd.py: `best_student.pth` is saved when "
                                      "`val_acc > best_acc`, and `val_acc` comes from the "
                                      "val loader built on --val-folds",
            },
            "FERPlus": {
                "counts_source": str(FER_MAJORITY.relative_to(ROOT)).replace("\\", "/"),
                "rows_total": fc_major["rows_total"],
                "by_fold": fc_major["by_fold"],
                "train_folds": f_train, "val_folds": f_val,
                "n_train": f_train_n, "n_reporting": f_report,
                "reporting_fold_prefixes": fc_major["prefix_by_fold"][f_vf],
                "reporting_partition": max(fc_major["prefix_by_fold"][f_vf],
                                           key=fc_major["prefix_by_fold"][f_vf].get),
                "expected_train_samples_declared": f_exp_train,
                "expected_val_samples_declared": f_exp_val,
                "declared_matches_measured": (f_exp_val == f_report
                                              and f_exp_train == f_train_n),
                "n_partitions_in_metadata": len(fc_major["by_fold"]),
                "selection_set_is_reporting_set": True,
                "separate_holdout_exists": len(fc_major["by_fold"]) > 2,
                "unfiltered_by_fold": fc_created["by_fold"],
                "majority_filter_drop": {
                    k: fc_created["by_fold"][k] - fc_major["by_fold"][k]
                    for k in fc_major["by_fold"] if k in fc_created["by_fold"]},
                "selection_evidence": "train_ferplus_kd.py hard-asserts expected_val_samples; "
                                      "selection uses the same val loader",
            },
        },
    }

    L = ["# Bölme kimliği — hangi ad, hangi bölme, kaç örnek", "",
         "Üretici: `diagnostics/split_identity.py` · ölçüm, beyan değil. Bu tablo bir adın "
         "DOĞRU olup olmadığını söyler; hangi adın kullanılacağı makale tarafının kararıdır.", "",
         "> **Level-1 / lisans.** RAF-DB meta CSV'si görüntü adı taşır ve yayımlanamaz; "
         "varsayılan yol yayımlanmış SAYIM dosyasını okur "
         "(`diagnostics/split_identity/rafdb_fold_class_counts.json`, yalnız fold × etiket "
         "sayıları). CSV'yi okumak açık bir eylemdir: `--from-data`.", "",
         "## Tek denklem", "",
         "| veri kümesi | eğitim fold | raporlanan fold | raporlanan bölüm | n (eğitim) | n (raporlanan) | meta'da bölüm sayısı | ayrı held-out | seçim = raporlama |",
         "|---|---|---|---|---|---|---|---|---|"]
    for name, d in payload["datasets"].items():
        L.append(f"| {name} | {d['train_folds']} | {d['val_folds']} | `{d['reporting_partition']}` "
                 f"| {d['n_train']} | **{d['n_reporting']}** | {d['n_partitions_in_metadata']} "
                 f"| {'VAR' if d['separate_holdout_exists'] else 'yok'} "
                 f"| {'EVET' if d['selection_set_is_reporting_set'] else 'hayır'} |")
    L += ["",
          "## RAF-DB — raporlanan fold gerçekten resmî test bölümü mü?", "",
          f"Raporlanan fold ({r_vf}) **{r_report}** satır taşıyor ve satırların yol öneki "
          f"dağılımı: `{r_prefix}`. Tek önek: **{'evet' if r_pure else 'HAYIR'}** — yani fold "
          f"{r_vf} tam olarak `{r_official}/` bölümüdür, karışım değil.", "",
          "Sınıf dağılımı, RAF-DB'nin yayımlanmış test dağılımıyla karşılaştırıldı:", "",
          "| sınıf | ölçülen | yayımlanmış |", "|---|---|---|"]
    for k in RAFDB_PUBLISHED_TEST:
        L.append(f"| {k} | {r_named.get(k, 0)} | {RAFDB_PUBLISHED_TEST[k]} |")
    L += ["",
          f"**Birebir eşleşme: {'EVET' if r_match else 'HAYIR'}.** Meta dosyasında yalnız "
          f"{len(rc['by_fold'])} bölüm var ({', '.join(f'fold {k}: {v}' for k, v in rc['by_fold'].items())}), "
          "yani RAF-DB tarafında ayrı bir held-out bölme **yoktur**; resmî test bölümü hem "
          "epoch-başı doğrulama hem raporlama için kullanılır.", "",
          "## FERPlus — ayrı bir held-out VARDI ve eğitime verildi", ""]
    L += [f"Meta dosyasında **{len(fc_major['by_fold'])}** bölüm var: "
          + " · ".join(f"fold {k} = {v} "
                       f"(`{max(fc_major['prefix_by_fold'][k], key=fc_major['prefix_by_fold'][k].get)}`)"
                       for k, v in fc_major["by_fold"].items()) + ".", "",
          f"Eğitim `train_folds: {f_train}` ({f_train_n} satır), raporlama `val_folds: {f_val}` "
          f"(**{f_report}** satır). Yani FERPlus'ın üçüncü bölmesi (PublicTest) **eğitime** "
          "katılmıştır; RAF-DB'de olmayan bir seçenek burada vardı ve harcandı. Bu bir kusur "
          "beyanı değil, bir yordam olgusudur — ama \"ayrı held-out yok\" cümlesi FERPlus için "
          "veri kümesinin değil **yordamın** sonucudur.", "",
          f"Eğitim betiğinin sert beyanı: `expected_train_samples={f_exp_train}` · "
          f"`expected_val_samples={f_exp_val}`. Ölçümle uyum: "
          f"**{'EVET' if payload['datasets']['FERPlus']['declared_matches_measured'] else 'HAYIR'}**.", "",
          "Çoğunluk süzgecinin düşürdüğü satırlar (ham FERPlus → çoğunluk meta):", "",
          "| fold | ham | çoğunluk | düşen |", "|---|---|---|---|"]
    for k, v in fc_major["by_fold"].items():
        raw = fc_created["by_fold"].get(k)
        L.append(f"| {k} | {raw} | {v} | {raw - v if raw is not None else '—'} |")
    L.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "split_identity.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "split_identity.json").write_text(json.dumps(payload, indent=2) + "\n",
                                                 encoding="utf-8")
    for name, d in payload["datasets"].items():
        print(f"{name:<10} egitim {d['train_folds']} n={d['n_train']:<6} "
              f"raporlanan {d['val_folds']} n={d['n_reporting']:<6} "
              f"bolum={d['reporting_partition']:<14} "
              f"ayri held-out={'VAR' if d['separate_holdout_exists'] else 'yok'}")
    print(f"RAF-DB sinif dagilimi yayimlanan dagilima esit: "
          f"{'EVET' if r_match else 'HAYIR'}")
    print(f"\nWrote {OUT_DIR / 'split_identity.md'}")

    try:
        import export_to_drive
        export_to_drive.hook("split_identity.py")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
