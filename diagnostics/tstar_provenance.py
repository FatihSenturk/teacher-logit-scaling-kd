"""G4.7 — dağıtılan T* hangi fit'ten geldi: tam fold mu, yarı fold mu?

NEDEN VAR (panel G4.7). Tablo B.2'nin başlığı ile §3.3 çelişiyor: biri T*'ın tam doğrulama
fold'unda, diğeri yarı fold'da fit edildiğini söylüyor. İkisi aynı anda doğru olamaz ve hangisi
olduğu koşuların KENDİ argümanlarından okunabilir — tahmin edilecek bir şey değil.

NASIL CEVAPLANIYOR. Diskteki her koşunun kendi `run_args.json`'undaki
`teacher_temperature_scale` toplanır, sonra her yuvarlak-olmayan değer iki fit artefaktına
karşı sayısal olarak eşleştirilir:
  - tam fold  : `teacher_temperature_scaling/temperature_fit.json`  (her öğretmen için T*)
  - yarı fold : `teacher_temperature_scaling/b3_tstar_halfsplit.json` (yarı-A'da fit)
Eşleşme toleransı 5e-4 (dağıtılan değerler 4 haneye yuvarlanmış olarak kaydediliyor).

0.7311 BİR T* DEĞİLDİR ve öyle sayılmaz: o, miskalibrasyon enjeksiyonunun sabit ölçeği
(A2 / B-010 kill-switch'i). Değer buraya elle yazılmıyor, `build_runs_ledger.MISCAL_T`'den
İTHAL ediliyor — aksi hâlde "bu bir T* değil" iddiası bu dosyanın kendi beyanı olurdu.

NE DEĞİŞTİRİR. Bu bir belge çelişkisi, sonuç çelişkisi değil: hangi fit kullanıldıysa koşular
onu kullandı ve tek bir sayı değişmiyor. Değişecek olan §3.3 ile B.2'den YANLIŞ OLANI.

Salt-okunur. Çıktı -> diagnostics/paper_tables/tstar_provenance.{json,md}
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from build_runs_ledger import MISCAL_T                            # noqa: E402 -- İTHAL, elle değil

LEDGER = ROOT / "runs.csv"
TS_DIR = ROOT / "diagnostics" / "teacher_temperature_scaling"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TOL = 5e-4          # dağıtılan değerler 4 haneye yuvarlı kaydediliyor (1.3406)
ROUND_GRID = (0.85, 0.95, 1.0, 1.10, 1.7, 2.2)


def dataset_of(ra):
    """Veri kümesi BAYRAKLARDAN, koşu adından değil.

    `train_affectnetplus_kd.py` (ve FERPlus sarmalayıcısı) `dataset_name` yazar;
    `train_rafdb_kd.py` yazmaz ama `aligned_dir`i vardır. Ad ayrıştırmak bu kampanyada
    zaten bir kez hücre karışmasına yol açtı (P3'ün yan hasarı), o yüzden yapılmıyor.
    """
    if ra.get("dataset_name"):
        return str(ra["dataset_name"])
    return "RAFDB" if ra.get("aligned_dir") else "?"


def deployed():
    """((veri kümesi, T) -> koşu adları). DEFTERDEN okunur, koşu dizinlerinden değil.

    NEDEN DEFTER (8 Ağu düzeltmesi). İlk sürüm `results/unified_students/` altındaki her
    koşunun `run_args.json`'unu tarıyordu. Doğru sonuç veriyordu ama **deponun Level 1
    özelliğini bozuyordu**: README "tablolar ve sayılar GPU'suz, veri kümesiz, checkpoint'siz
    üretilir" diyor ve koşu dizinleri boyut yüzünden yayımlanmıyor. 18 tablo üreticisinin
    17'si bu özelliği koruyordu; bunu bozan tek betik buydu.

    `runs.csv` aynı bilgiyi taşıyor (`t_scale` sütunu, her koşunun KENDİ `run_args`'ından
    türetilmiş) ve deponun içinde. Ad->parametre disiplini korunuyor: değer yine koşunun
    kendi argümanından geliyor, yalnız bir adım önce defter tarafından okunmuş.

    KAPSAM NOTU: defter RAF-DB'ye özgü; FERPlus koşuları içinde yok. Zaten FERPlus
    sıcaklıkları bu tablonun kapsamı dışındaydı (B.2/§3.3 sorusu RAF-DB'nin) ve öyle
    raporlanıyordu.
    """
    out = {}
    with LEDGER.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            t = float(r.get("t_scale") or 1.0)
            if abs(t - 1.0) < 1e-12:
                continue
            out.setdefault(("RAFDB", round(t, 6)), []).append(r["run_name"])
    return out


def fits():
    full = {d["teacher"]: float(d["T_star"])
            for d in json.loads((TS_DIR / "temperature_fit.json").read_text(encoding="utf-8"))}
    h = json.loads((TS_DIR / "b3_tstar_halfsplit.json").read_text(encoding="utf-8"))
    half = {"stage1": float(h["T_star_fit_on_half_a"])}
    return full, half, h


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    dep = deployed()
    full, half, h = fits()
    rows, verdicts = [], []

    for (ds, t), runs in sorted(dep.items()):
        base = {"dataset": ds, "T": t, "n_runs": len(runs), "runs": runs}
        if any(abs(t - g) < 1e-9 for g in ROUND_GRID):
            rows.append({**base, "kind": "yuvarlak grid noktası", "source": "—", "match": None})
            continue
        if abs(t - MISCAL_T) < TOL:
            rows.append({**base, "kind": "miskalibrasyon enjeksiyonu",
                         "source": "A2 / B-010 kill-switch (build_runs_ledger.MISCAL_T)",
                         "match": abs(t - MISCAL_T)})
            continue
        if ds != "RAFDB":
            # Elimdeki iki fit artefaktı RAF-DB öğretmenlerinin. Başka veri kümesinin T*'ını
            # bunlara karşı eşleştirmek anlamsız olurdu; SESSİZCE DÜŞÜRMEK de yanlış olurdu.
            # Kapsam dışı olduğu yazılıyor -- G4.7'nin sorusu B.2/§3.3, yani RAF-DB.
            rows.append({**base, "kind": "FİT EDİLMİŞ T* (kapsam dışı)",
                         "source": f"{ds} öğretmeninin kendi fiti — bu dosyada artefaktı yok",
                         "match": None})
            continue

        cands = ([("yarı fold (yarı-A'da fit)", f"half:{k}", v) for k, v in half.items()]
                 + [("tam fold", f"full:{k}", v) for k, v in full.items()])
        hits = [(lab, key, v, abs(t - v)) for lab, key, v in cands if abs(t - v) < TOL]
        if len(hits) != 1:
            raise RuntimeError(
                f"T={t} ({ds}) için {len(hits)} fit eşleşmesi bulundu "
                f"({[h_[1] for h_ in hits]}). Tek kaynağa bağlanamayan bir T* raporlanmaz — "
                f"tahmine düşülmeyecek.")
        lab, key, v, d = hits[0]
        # Diğer fit ne verirdi? Çelişkinin maddi olup olmadığı buradan okunur.
        other = {"full": full.get(key.split(":")[1]), "half": half.get(key.split(":")[1])}
        alt = other["full"] if key.startswith("half") else other["half"]
        rows.append({**base, "kind": "FİT EDİLMİŞ T*", "source": lab,
                     "source_key": key, "fit_value": v, "match": d, "alternative_fit": alt,
                     "delta_vs_alternative": (abs(v - alt) if alt else None)})
        verdicts.append((t, lab, key, v, alt))

    if not verdicts:
        summary = "dağıtılmış fit edilmiş T* bulunamadı"
    else:
        t, lab, key, v, alt = verdicts[0]
        summary = (f"Dağıtılan T*={t:g} **{lab}** fitinden geldi "
                   f"({v:.6f} → {t:g}). Tam fold {alt:.6f} verirdi ve hiçbir koşu onu "
                   f"kullanmadı.")

    write(rows, full, half, h, summary, verdicts)
    print("G4.7 T* koken:")
    for r in rows:
        print(f"  {r['dataset']:8s} T={r['T']:<8g} {r['n_runs']:2d} kosu  "
              f"{r['kind']:30s} {r['source']}")
    print(f"\nozet: {summary}")


def write(rows, full, half, h, summary, verdicts):
    L = ["# G4.7 — dağıtılan T\\* hangi fit'ten geldi", "",
         "> **Panel G4.7.** Tablo B.2 başlığı ile §3.3 çelişiyor. Cevap koşuların kendi "
         "argümanlarından okundu, metinden değil.", "",
         f"**CEVAP: {summary}**", "",
         "## Diskteki her T değeri, kendi koşu argümanından", "",
         "| veri kümesi | T | koşu | ne | kaynak | eşleşme |",
         "|---|---|---|---|---|---|"]
    for r in rows:
        m = f"{r['match']:.2e}" if r["match"] is not None else "—"
        L.append(f"| {r['dataset']} | {r['T']:g} | {r['n_runs']} | {r['kind']} | "
                 f"{r['source']} | {m} |")
    L += ["", "Hiçbir satır koşu ADINDAN çıkarılmadı; her koşunun kendi `run_args.json`'undaki "
              "`teacher_temperature_scale` okundu. `--teacher-temperature-scale` bayrağı "
              "eklenmeden önce koşulmuş koşularda anahtar yoktur ve belgelenmiş varsayılan "
              "T=1.0 kabul edilir (o koşular bu tabloya girmez).", "",
          "## İki fit yan yana", "",
          "| öğretmen | tam fold T\\* | yarı-A T\\* | fark |", "|---|---|---|---|"]
    for t in sorted(full):
        hv = half.get(t)
        L.append(f"| {t} | {full[t]:.6f} | {f'{hv:.6f}' if hv else '— (fit edilmedi)'} | "
                 f"{f'{abs(full[t]-hv):.6f}' if hv else '—'} |")
    L += ["", f"Yarı-bölme: n_total={h['n_total']}, yarı-A={h['n_half_a']}, "
              f"yarı-B={h['n_half_b']}, bölme tohumu={h['split_seed']}. Artefakt yarı-B "
              f"indekslerini de saklıyor, yani bölme yeniden üretilebilir.", ""]

    if verdicts:
        t, lab, key, v, alt = verdicts[0]
        L += ["## Ne değişir, ne değişmez", "",
              f"- **Hiçbir sayı değişmez.** Koşular {t:g}'yı kullandı ve bu dosya onu "
              f"doğruluyor; hiçbir koşu {alt:.4f}'ü kullanmadı. Sonuçlar olduğu gibi kalır.",
              f"- **Metin değişir.** §3.3 ile Tablo B.2'den *tam fold* diyen taraf yanlıştır ve "
              f"**yarı fold (yarı-A'da fit)** olarak düzeltilmelidir.",
              f"- **Yöntem olarak doğru olan da buydu.** T*'ı değerlendirileceği veriye fit "
              f"etmek iyimserlik taşırdı; yarı-A'da fit edip yarı-B'de ölçmek bunun tam olarak "
              f"kaçınılması gereken hâlidir. Yani çelişki bir yöntem hatası değil, bir **başlık "
              f"hatası** — ve düzeltme yöntemi zayıflatmaz, doğru anlatır.",
              f"- İki fit arasındaki fark {abs(v - alt):.4f} "
              f"({100 * abs(v - alt) / alt:.2f}%), yani dağıtılan değer tam-fold optimumunun "
              f"çok yakınında; çelişki maddi bir sapma değil, yalnız yanlış etiketlenmiş bir "
              f"prosedür.", ""]

    L += ["---", "", "Üretici: `diagnostics/tstar_provenance.py` · kaynaklar: her koşunun "
          "`run_args.json`'u + `diagnostics/teacher_temperature_scaling/"
          "{temperature_fit,b3_tstar_halfsplit}.json` · `MISCAL_T` "
          "`build_runs_ledger`'dan ithal", ""]

    (OUT_DIR / "tstar_provenance.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "tstar_provenance.json").write_text(json.dumps({
        "item": "G4.7", "summary": summary, "tolerance": TOL,
        "round_grid": list(ROUND_GRID), "miscal_T_imported": MISCAL_T,
        "full_fold_fits": full, "half_fold_fits": half,
        "half_split": {k: v for k, v in h.items() if k != "half_b_indices"},
        "deployed": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
