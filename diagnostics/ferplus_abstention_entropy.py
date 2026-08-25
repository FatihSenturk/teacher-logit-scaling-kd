"""B7 — FERPlus insan entropisi, abstention (`unknown` + `NF`) kütlesi temsil edilerek.

İTİRAZ. Makale FERPlus oy toplamlarının 10'a tamamlanmamasını *"eksik oyların sebebi
belirlenemez"* diye geçiştiriyor. Kanonik `fer2013new.csv` başlığı bunu yalanlıyor: sekiz
ifade sütununun yanında **`unknown` ve `NF`** sütunları var, yani eksik oy bir kayıp değil,
anotatörün açık **\"bilemiyorum\" / \"yüz değil\"** yanıtı. Bizim türevimizde (
`configs/FERPlus_majority_metadata.csv`) o iki sütun yok — bu yüzden cümle yazıldı.

ÖLÇÜLDÜ, VARSAYILMADI. Doğrulama fold'unun 3153 satırının **hepsi** kanonik dosyada
bulundu ve on sütunun toplamı **her satırda tam 10**. Yani \"eksik oy\" diye bir şey yok;
oyların bir kısmı abstention kategorilerine gitmiş.

İKİ HEDEF, İKİSİ DE AÇIKÇA TANIMLI:
  (a) KOŞULLU (yayımlı): insan dağılımı sekiz ifadeye yeniden normalize edilir; öğretmen
      softmax'ı da sekiz boyutlu. Bu, *\"anotatör bir ifade seçtiyse hangisini seçti\"*
      sorusunun cevabıdır.
  (b) ABSTENTION TEMSİL EDİLMİŞ: insan dağılımı **on** kategori üzerinde; öğretmenin
      dağılımı iki ekstra kategoride sıfır olacak şekilde genişletilir. Bu, *\"anotatör ne
      yanıt verdi\"* sorusunun cevabıdır ve öğretmenin üretemeyeceği bir kütle taşır --
      dolayısıyla JSD'nin bir TABANI vardır. Taban T'den bağımsız, ama optimum T kayabilir;
      soru tam olarak budur.

BAĞIMSIZ BİR VERİ KÜMESİ DOSYASINA BAĞIMLILIK YARATMADAN. Kanonik CSV depoda yok ve
yayımlanmıyor. Betik onu YALNIZ `--rebuild` ile okur ve doğrulama fold'unun on oy sütununu
küçük bir yan dosyaya (`ferplus_jsd/ferplus_val_votes10.csv`, 3153 satır) çıkarır; bütün
analiz o yan dosyadan yürür. Böylece Level-1 değişmezi korunur: public depoda kanonik dosya
olmadan da tablo yeniden üretilebilir.

Salt-okunur, GPU yok (öğretmen logitleri önbellekten).
Çıktı -> diagnostics/paper_tables/ferplus_abstention_entropy.{md,json}
        + diagnostics/ferplus_jsd/ferplus_val_votes10.csv  (--rebuild ile)
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

JSD_DIR = ROOT / "diagnostics" / "ferplus_jsd"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
VOTES10 = JSD_DIR / "ferplus_val_votes10.csv"
CACHE = JSD_DIR / "ferplus_val_logits.pt"
META = ROOT / "configs" / "FERPlus_majority_metadata.csv"
# Kanonik FERPlus etiket dosyası. Depoda YOK, yayımlanmıyor; yalnız `--rebuild` okur.
# Aynı yol `tools/build_ferplus_majority_metadata.py`'nin argparse varsayılanı ve orada
# `public_repo_sync.DECLARED_ABS` içinde gerekçesiyle beyanlı.
CANONICAL = Path(r"C:\Users\mfati\Downloads\fer2013new.csv")

EMOTIONS = ["neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear",
            "contempt"]
ABSTAIN = ["unknown", "NF"]
EPS = 1e-12
# Aynı ızgara `ferplus_human_vote_jsd.py`'deki: 0.10..4.00, adım 0.02. Optimumun sınıra
# oturmadığı orada da burada da kontrol ediliyor.
TS = [round(0.10 + 0.02 * i, 2) for i in range(int((4.00 - 0.10) / 0.02) + 1)]


def jsd(p, q):
    m = 0.5 * (p + q)

    def kl(a, b):
        return (a * (torch.log(a + EPS) - torch.log(b + EPS))).sum(dim=1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def entropy(p):
    return -(p * torch.log(p + EPS)).sum(dim=1)


def rebuild():
    """Kanonik dosyadan doğrulama fold'unun ON oy sütununu çıkar (tek seferlik)."""
    import pandas as pd
    if not CANONICAL.exists():
        raise SystemExit(f"kanonik dosya yok: {CANONICAL}")
    can = pd.read_csv(CANONICAL)
    meta = pd.read_csv(META)
    blob = torch.load(CACHE, map_location="cpu", weights_only=False)
    order = [Path(p).name for p in blob["paths"]]
    val = meta[meta.fold == 2].copy()
    val["base"] = val.path.str.split("/").str[-1]
    idx = val.set_index("base").loc[order]
    # `Image name` KANONİK DOSYADA BENZERSİZ DEĞİL (35887 satır, 35710 ad -- adlar Usage
    # bölmeleri arasında tekrar ediyor). Ada göre birleştirmek bir satırı ikizleyip 3153
    # yerine 3154 satır üretiyordu. `source_row` kanonik satır indeksidir ve birebirdir;
    # ilk 2000 satırda sekiz oy sütununun tamamı ve dosya adı birebir doğrulandı.
    rows = can.iloc[idx.source_row.to_numpy()]
    assert (rows["Image name"].to_numpy() == np.asarray(order)).all(), "sıra bozuldu"
    assert np.allclose(rows[EMOTIONS].to_numpy(float), idx[EMOTIONS].to_numpy(float)), \
        "sekiz oy sütunu türevle uyuşmuyor"
    with VOTES10.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image", "source_row"] + EMOTIONS + ABSTAIN)
        for name, sr, vals in zip(rows["Image name"], idx.source_row.to_numpy(),
                                  rows[EMOTIONS + ABSTAIN].to_numpy(int)):
            w.writerow([name, int(sr)] + list(map(int, vals)))
    print(f"yazildi: {VOTES10}  ({len(rows)} satir)")


def load_votes():
    if not VOTES10.exists():
        raise SystemExit(f"{VOTES10} yok — once `--rebuild` calistirin (kanonik "
                         f"fer2013new.csv gerekir).")
    names, v = [], []
    with VOTES10.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            names.append(r["image"])
            v.append([float(r[c]) for c in EMOTIONS + ABSTAIN])
    return names, np.asarray(v)


def sweep(z, p_human, pad):
    """T ızgarasında ortalama JSD. `pad` -> öğretmen dağılımı iki sıfır sütunla genişletilir."""
    out = []
    for T in TS:
        q = F.softmax(z / T, dim=1)
        if pad:
            q = torch.cat([q, torch.zeros(q.shape[0], len(ABSTAIN))], dim=1)
        out.append({"T": T, "mean_jsd": float(jsd(p_human, q).mean())})
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true",
                    help="kanonik fer2013new.csv'den on-sutunlu yan dosyayi uret")
    args, _unknown = ap.parse_known_args()
    if args.rebuild:
        rebuild()

    names, v10 = load_votes()
    blob = torch.load(CACHE, map_location="cpu", weights_only=False)
    order = [Path(p).name for p in blob["paths"]]
    if order != names:
        raise RuntimeError("oy dosyasinin sirasi onbellekteki logit sirasiyla ayni degil")
    z = blob["logits"].float()

    v8 = v10[:, :len(EMOTIONS)]
    tot10, tot8 = v10.sum(1), v8.sum(1)
    p8 = torch.tensor(v8 / np.maximum(tot8, EPS)[:, None], dtype=torch.float32)
    p10 = torch.tensor(v10 / np.maximum(tot10, EPS)[:, None], dtype=torch.float32)
    h8, h10 = entropy(p8), entropy(p10)

    s8, s10 = sweep(z, p8, pad=False), sweep(z, p10, pad=True)
    b8 = min(s8, key=lambda r: r["mean_jsd"])
    b10 = min(s10, key=lambda r: r["mean_jsd"])
    at1_8 = next(r for r in s8 if r["T"] == 1.0)
    at1_10 = next(r for r in s10 if r["T"] == 1.0)

    ref = JSD_DIR / "per_sample_human_entropy.npy"
    dev = None
    if ref.exists():
        dev = float(np.abs(h8.numpy() - np.load(ref)).max())

    # BUTUN FOLD'LAR uzerinden ayni sayim (20 Agu 2026, N19). Makale §3.5 iki yuzde basiyor ve
    # PAYDALARI FARKLI: "%29,3 of all rows" TUREV dosyasinin tamami (uc fold), "%37,3 of the
    # validation fold" yalniz fold==2. Ikincisi bu artefaktta zaten vardi (eight_col_sums / n_val),
    # birincisinin URETICISI YOKTU: bu CSV'yi okuyan yedi betigin hepsi `fold == 2` suzuyor,
    # hicbiri butun satirlar uzerinde saymiyordu. N16'dan beri "ureticisi yok" diye kayitliydi;
    # burada kapaniyor. Sayim CSV'nin kendisinden, tek satir filtresiz.
    # `csv` ile okunuyor, pandas ile degil: bu betikte pandas BILEREK yalniz `rebuild()` icinde
    # yerel olarak import ediliyor (kanonik dosya yolu), varsayilan yol onsuz kosmali.
    with META.open(encoding="utf-8-sig", newline="") as _fh:
        _rows_all = [[float(r[e]) for e in EMOTIONS] for r in csv.DictReader(_fh)]
    _all8 = np.asarray(_rows_all).sum(1)
    d_all = {"n_rows_all_folds": int(len(_rows_all)),
             "rows_below_ten_all_folds": int((_all8 < 10 - 1e-9).sum()),
             "eight_col_sums_all_folds": {str(int(k)): int(c) for k, c in
                                          zip(*np.unique(_all8, return_counts=True))}}
    d_all["share_below_ten_all_folds"] = (
        100.0 * d_all["rows_below_ten_all_folds"] / d_all["n_rows_all_folds"])

    d = {"n_val": len(names),
         "rows_with_abstention": int((v10[:, len(EMOTIONS):].sum(1) > 0).sum()),
         **d_all,
         "abstention_votes": {"unknown": int(v10[:, len(EMOTIONS)].sum()),
                              "NF": int(v10[:, len(EMOTIONS) + 1].sum())},
         "vote_sum_10_always": bool((tot10 == 10).all()),
         "eight_col_sums": {str(int(k)): int(c) for k, c in
                            zip(*np.unique(tot8, return_counts=True))},
         "mean_entropy_conditional_8": float(h8.mean()),
         "mean_entropy_with_abstention_10": float(h10.mean()),
         "entropy_delta": float(h10.mean() - h8.mean()),
         "published_entropy_reproduced_max_dev": dev,
         "T_star_jsd_conditional_8": b8, "T_star_jsd_with_abstention_10": b10,
         "at_T1_conditional_8": at1_8, "at_T1_with_abstention_10": at1_10,
         "grid": {"lo": TS[0], "hi": TS[-1], "step": 0.02},
         "boundary_hit": bool(b8["T"] in (TS[0], TS[-1]) or b10["T"] in (TS[0], TS[-1])),
         "sweep_conditional_8": s8, "sweep_with_abstention_10": s10}
    write(d)

    print("=== ferplus_abstention_entropy ===")
    print(f"  val satiri              : {d['n_val']}")
    print(f"  abstention kutlesi olan : {d['rows_with_abstention']} "
          f"(%{100 * d['rows_with_abstention'] / d['n_val']:.1f})")
    print(f"  on sutun toplami hep 10 : {d['vote_sum_10_always']}")
    print(f"  ORT ENTROPI  kosullu-8  : {d['mean_entropy_conditional_8']:.4f} nat "
          f"(yayimliyla maks sapma {dev:.2e})" if dev is not None else "")
    print(f"  ORT ENTROPI  abstention : {d['mean_entropy_with_abstention_10']:.4f} nat "
          f"({d['entropy_delta']:+.4f}, %{100 * d['entropy_delta'] / d['mean_entropy_conditional_8']:+.1f})")
    print(f"  T*_JSD  kosullu-8       : {b8['T']:.2f}  (JSD {b8['mean_jsd']:.4f})")
    print(f"  T*_JSD  abstention-10   : {b10['T']:.2f}  (JSD {b10['mean_jsd']:.4f})")


def write(d):
    same = d["T_star_jsd_conditional_8"]["T"] == d["T_star_jsd_with_abstention_10"]["T"]
    L = ["# B7 — FERPlus insan entropisi, abstention kütlesi temsil edilerek", "",
         "Üretici: `diagnostics/ferplus_abstention_entropy.py` · öğretmen logitleri "
         "`ferplus_jsd/ferplus_val_logits.pt` önbelleğinden · oy sütunları "
         "`ferplus_jsd/ferplus_val_votes10.csv`", "",
         "> Makale FERPlus oylarının 10'a tamamlanmamasını *\"sebebi belirlenemez\"* diye "
         "geçiştiriyor. Kanonik `fer2013new.csv` başlığı bunu yalanlıyor: sekiz ifade "
         "sütununun yanında **`unknown`** ve **`NF`** var. Eksik oy bir kayıp değil, "
         "anotatörün açık *\"bilemiyorum\" / \"yüz değil\"* yanıtı.", "",
         "## Ölçüm", "", "| kalem | değer |", "|---|---|",
         f"| doğrulama satırı | {d['n_val']} |",
         f"| **on sütunun toplamı her satırda tam 10** | "
         f"**{'evet' if d['vote_sum_10_always'] else 'HAYIR'}** |",
         f"| abstention kütlesi taşıyan satır | {d['rows_with_abstention']} "
         f"(%{100 * d['rows_with_abstention'] / d['n_val']:.1f}) |",
         f"| `unknown` oyu | {d['abstention_votes']['unknown']} |",
         f"| `NF` oyu | {d['abstention_votes']['NF']} |", "",
         "Sekiz sütunun toplamı: "
         + ", ".join(f"**{k}** oy → {v} satır"
                     for k, v in sorted(d["eight_col_sums"].items(),
                                        key=lambda kv: -int(kv[0])))
         + ". Yani \"eksik\" görünen oy, on sütunda tam olarak geri geliyor.", "",
         "## (a) ve (b): iki hedef, iki entropi", "",
         "| hedef | tanım | ortalama insan entropisi (nat) |", "|---|---|---|",
         f"| **(a) koşullu (yayımlı)** | sekiz ifadeye yeniden normalize; *\"bir ifade "
         f"seçtiyse hangisi\"* | **{d['mean_entropy_conditional_8']:.4f}** |",
         f"| **(b) abstention temsil edilmiş** | on kategori; *\"ne yanıt verdi\"* | "
         f"**{d['mean_entropy_with_abstention_10']:.4f}** |", "",
         f"Fark **{d['entropy_delta']:+.4f} nat** "
         f"(%{100 * d['entropy_delta'] / d['mean_entropy_conditional_8']:+.1f}). "
         + (f"(a) yayımlanan `per_sample_human_entropy.npy` ile **birebir** yeniden "
            f"üretildi; en büyük sapma `{d['published_entropy_reproduced_max_dev']:.2e}` "
            f"(float32 saklama)." if d["published_entropy_reproduced_max_dev"] is not None
            else ""), "",
         "## T*_JSD ikisinde de 0.74'te mi kalıyor?", "",
         "(b)'de öğretmenin dağılımı iki ekstra kategoride **sıfır** olacak şekilde "
         "genişletiliyor — model `unknown`/`NF` üretemez, dolayısıyla JSD'nin T'den "
         "bağımsız bir **tabanı** var. Soru tabanın büyüklüğü değil, optimumun yeri.", "",
         "| hedef | T\\*_JSD | o T'de ortalama JSD | T=1'de JSD | ölçeklemenin kazancı |",
         "|---|---|---|---|---|"]
    for tag, key1, key2 in (("(a) koşullu-8", "T_star_jsd_conditional_8",
                             "at_T1_conditional_8"),
                            ("(b) abstention-10", "T_star_jsd_with_abstention_10",
                             "at_T1_with_abstention_10")):
        b, a1 = d[key1], d[key2]
        L.append(f"| {tag} | **{b['T']:.2f}** | {b['mean_jsd']:.4f} | "
                 f"{a1['mean_jsd']:.4f} | {a1['mean_jsd'] - b['mean_jsd']:+.4f} "
                 f"({100 * (a1['mean_jsd'] - b['mean_jsd']) / a1['mean_jsd']:+.1f}%) |")
    L += ["", ("> **T\\*_JSD değişmiyor.** Abstention kütlesi temsil edildiğinde optimum "
               "aynı sıcaklıkta kalıyor — yani hizalama sonucu, eksik oyların nasıl "
               "yorumlandığına **bağlı değil**. Değişen tek şey JSD'nin tabanı, ve o "
               "taban T'den bağımsız."
               if same else
               "> **T\\*_JSD KAYIYOR.** Abstention kütlesi temsil edildiğinde optimum "
               "başka bir sıcaklığa gidiyor; hizalama sonucu eksik oyların nasıl "
               "yorumlandığına bağlı ve makale bunu yazmalı."), "",
          f"Izgara [{d['grid']['lo']}, {d['grid']['hi']}], adım {d['grid']['step']} — "
          f"`ferplus_human_vote_jsd.py`'dekiyle aynı. Optimum sınırda mı: "
          f"**{'EVET (çözülmemiş)' if d['boundary_hit'] else 'hayır'}**.", "",
          "## Makaleye düşen", "",
          "*\"Eksik oyların sebebi belirlenemez\"* cümlesi **gereksiz ve yanlış**: sebep "
          "kanonik dosyada yazılı. Doğru cümle, sekiz sütunlu hedefin bir **koşullu** "
          "hedef olduğunu söylemek ve abstention kütlesinin ölçülmüş büyüklüğünü "
          f"(%{100 * d['rows_with_abstention'] / d['n_val']:.1f} satır, entropiye etkisi "
          f"{d['entropy_delta']:+.4f} nat) vermektir.", ""]

    (OUT_DIR / "ferplus_abstention_entropy.md").write_text("\n".join(L) + "\n",
                                                           encoding="utf-8")
    (OUT_DIR / "ferplus_abstention_entropy.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
