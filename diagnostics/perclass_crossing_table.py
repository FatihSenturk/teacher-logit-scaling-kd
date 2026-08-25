"""§5.4 — yedi sınıfın tam tablosu ve "frekansı takip eder" iddiasının denetimi.

NEDEN VAR (7 Ağu akşam isteği). §5.4 sıfırı kesme sıcaklığının sınıf frekansını takip
ettiğini söylüyor. Şüphe somut: Surprise 1.622'de kesiyorsa ve Sadness ondan DAHA SIK bir
sınıfsa, Sadness'ın daha geç kesmesi sıralamayı bozar — bir inversiyon olur. Cümle sayı
görülmeden son hâline getirilemez.

Bu betik yedi sınıfın tamamını tek tabloda basar ve iddiayı ÖLÇER: frekans sıralaması ile
kesme-sıcaklığı sıralaması arasındaki Spearman ρ, ve komşu inversiyonların tam listesi.

İDDİANIN OPERASYONEL TANIMI, önceden: "frekansı takip eder" = sınıflar n'e göre azalan
sıralandığında kesme sıcaklığı monoton ARTAR. Her ihlal bir inversiyondur ve adıyla
listelenir. Hiç kesmeyen sınıflar (T=2.2'ye kadar aşırı güvenli kalanlar) sıralamanın
SONUNA konur — "sonsuz" değil ama "gözlenen aralıkta kesmedi" demek, ve bu ayrım tabloda
görünür.

Yeni ölçüm yok; kaynak `diagnostics/reliability/perclass_calibration.json`.
Çıktı -> diagnostics/paper_tables/perclass_crossing.{json,md}
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION                        # noqa: E402

SRC = ROOT / "diagnostics" / "reliability" / "perclass_calibration.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def spearman(a, b):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return num / (da * db) if da and db else float("nan")


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    d = json.loads(SRC.read_text(encoding="utf-8"))
    T = d["temperatures"]
    i1, i22 = T.index(1.0), T.index(2.2)

    rows = []
    for c, v in d["classes"].items():
        rows.append({"cls": c, "n": v["n"],
                     "gap_native": v["gap_mean"][i1],
                     "gap_T22": v["gap_mean"][i22],
                     "sd_native": v["gap_sd"][i1], "sd_T22": v["gap_sd"][i22],
                     "crossing_T": v["zero_crossing_T"],
                     "range_over_seed_sd": v.get("range_over_seed_sd")})
    rows.sort(key=lambda r: -r["n"])                      # frekansa göre azalan

    # --- iddianin olcumu: n azalirken kesme T'si monoton artmali mi
    crossed = [r for r in rows if r["crossing_T"] is not None]
    inversions = []
    for i in range(len(crossed) - 1):
        a, b = crossed[i], crossed[i + 1]
        if a["crossing_T"] > b["crossing_T"]:             # daha sik olan DAHA GEC kesiyor
            inversions.append({"more_frequent": a["cls"], "n_more": a["n"],
                               "T_more": a["crossing_T"],
                               "less_frequent": b["cls"], "n_less": b["n"],
                               "T_less": b["crossing_T"],
                               "delta_T": a["crossing_T"] - b["crossing_T"]})
    # İŞARET KONVANSİYONU — 8 Ağu düzeltmesi. İlk sürüm x ekseni olarak -n (seyreklik)
    # kullanıp sonucu "Spearman(frekans, kesme T) = +0.900" diye ETİKETLEMİŞTİ. Sayı seyreklik
    # için doğruydu ama etiket frekans diyordu, yani etiket hesapla çelişiyordu. İşaretsiz
    # ya da yanlış etiketli bir korelasyon, bu makalede üç turdur uğraşılan belirsizlik
    # sınıfının ta kendisi. Şimdi ikisi de ayrı ayrı, adıyla raporlanıyor.
    rho_n = spearman([r["n"] for r in crossed], [r["crossing_T"] for r in crossed])
    rho_rarity = spearman([-r["n"] for r in crossed], [r["crossing_T"] for r in crossed])

    never = [r["cls"] for r in rows if r["crossing_T"] is None]
    verdict = ("EĞİLİM VAR, TEK İNVERSİYONLA" if len(inversions) == 1 else
               f"EĞİLİM VAR, {len(inversions)} İNVERSİYONLA" if inversions else
               "SIRALAMA TAM — inversiyon yok")

    write(rows, crossed, inversions, rho_n, rho_rarity, never, verdict)
    print("§5.4 yedi sinif:")
    for r in rows:
        z = f"{r['crossing_T']:.3f}" if r["crossing_T"] else "kesmedi"
        print(f"  {r['cls']:10s} n={r['n']:5d}  native {r['gap_native']:+.4f}  "
              f"kesme {z:>8s}  T=2.2 {r['gap_T22']:+.4f}")
    print(f"\n  rho(n, kesme T)         = {rho_n:+.3f}   (negatif = sik sinif ERKEN kesiyor)")
    print(f"  rho(seyreklik, kesme T) = {rho_rarity:+.3f}   (ayni iliski, ters eksen)")
    print(f"  inversiyon: {len(inversions)}  -> {verdict}")
    for iv in inversions:
        print(f"    {iv['more_frequent']} (n={iv['n_more']}, T={iv['T_more']:.3f}) daha SIK "
              f"ama {iv['less_frequent']} (n={iv['n_less']}, T={iv['T_less']:.3f})'dan "
              f"{iv['delta_T']:.3f} DAHA GEC kesiyor")


def write(rows, crossed, inversions, rho_n, rho_rarity, never, verdict):
    L = ["# §5.4 — yedi sınıfın tam tablosu ve \"frekansı takip eder\" denetimi", "",
         "> **7 Ağu akşam isteği.** Cümle \"sıfırı kesme sıcaklığı sınıf frekansını takip "
         "eder\" diyor. Bu tablo iddiayı ölçüyor; yeni ölçüm yok, kaynak `perclass` json'u.",
         "", f"**HÜKÜM: {verdict}**", "",
         f"@swa · 3 tohum · {SD_CONVENTION} · sinyal: per-class signed confidence gap "
         f"= mean(top-1 confidence) − accuracy, GERÇEK etikete göre gruplanmış, binleme yok",
         "", "## Yedi sınıf, frekansa göre azalan", "",
         "| sınıf | n | native signed gap | sıfırı kesme T | T=2.2'deki gap |",
         "|---|---|---|---|---|"]
    for r in rows:
        z = f"**{r['crossing_T']:.3f}**" if r["crossing_T"] else "**kesmedi**"
        L.append(f"| {r['cls']} | {r['n']} | {r['gap_native']:+.4f} ± {r['sd_native']:.4f} | "
                 f"{z} | {r['gap_T22']:+.4f} ± {r['sd_T22']:.4f} |")
    L += ["", f"Kesmeyen sınıflar: {', '.join(never)} — T=2.2'ye kadar **hâlâ aşırı güvenli**. "
              f"Bunlar \"sonsuzda kesiyor\" değil, **gözlenen aralıkta kesmedi** demek; "
              f"sıralamaya sonda ama ayrı etiketle giriyorlar.", "",
          "## İddianın ölçümü", "",
          "**Operasyonel tanım (önceden yazıldı):** \"frekansı takip eder\" = sınıflar n'e göre "
          "azalan sıralandığında kesme sıcaklığı monoton **artar**. Her ihlal bir inversiyondur.",
          "", f"- Kesen sınıf sayısı: **{len(crossed)}**/7",
          f"- **ρ(n, T_cross) = {rho_n:+.3f}** — negatif işaret \"sık sınıf ERKEN kesiyor\" "
          f"demek, yani iddianın yönü.",
          f"- ρ(seyreklik sırası, T_cross) = {rho_rarity:+.3f} — aynı ilişki, ters eksen.",
          "",
          "> **Konvansiyon açıkça yazılmalı.** Bu iki sayı aynı örüntünün iki gösterimi; "
          "işareti eksen seçimi belirliyor. Altyazıya girerse hangisinin kullanıldığı "
          "yazılsın — işaretsiz bırakılan bir korelasyon belirsizdir.",
          f"- Komşu inversiyon: **{len(inversions)}**", ""]
    if inversions:
        L += ["| daha sık olan | n | kesme T | daha seyrek olan | n | kesme T | fark |",
              "|---|---|---|---|---|---|---|"]
        for iv in inversions:
            L.append(f"| **{iv['more_frequent']}** | {iv['n_more']} | {iv['T_more']:.3f} | "
                     f"{iv['less_frequent']} | {iv['n_less']} | {iv['T_less']:.3f} | "
                     f"**+{iv['delta_T']:.3f}** |")
        L += ["", f"> **Şüpheniz doğrulandı.** {inversions[0]['more_frequent']} "
              f"(n={inversions[0]['n_more']}) {inversions[0]['less_frequent']}'dan "
              f"(n={inversions[0]['n_less']}) **daha sık**, ama sıfırı "
              f"**{inversions[0]['delta_T']:.3f} daha geç** kesiyor. Sıralama bu tek noktada "
              f"bozuluyor — komşu bir yer değiştirme, yani eğilim duruyor ama **tam değil**.",
              "", "> Önerilen ifade: *\"crossing temperature broadly tracks class frequency, "
              "with one inversion (sadness crosses later than the less frequent surprise)\"*. "
              "Niteleyici olmadan cümle veriden fazlasını söylüyor.", ""]
    else:
        L += ["> Inversiyon yok; cümle niteleyici gerektirmiyor.", ""]

    L += ["## Neden inversiyon şaşırtıcı değil", "",
          "Kesme sıcaklığı yalnız frekansa değil, sınıfın **native gap'inin büyüklüğüne** de "
          "bağlı: büyük gap'i kapatmak daha yüksek T ister. Frekans ile gap arasındaki ilişki "
          "gevşek olduğu için sıralamanın tam olması zaten beklenmezdi. Tabloda ikisi yan "
          "yana duruyor, okur ilişkiyi kendisi görebilir.", "",
          "---", "", "Üretici: `diagnostics/perclass_crossing_table.py` · kaynak: "
          "`diagnostics/reliability/perclass_calibration.json` (yeni ölçüm yok)", ""]

    (OUT_DIR / "perclass_crossing.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "perclass_crossing.json").write_text(json.dumps({
        "item": "§5.4 per-class crossing", "verdict": verdict, "rows": rows,
        "spearman_n_vs_crossing": rho_n,
        "spearman_rarity_vs_crossing": rho_rarity, "inversions": inversions,
        "never_crossed": never, "sd_convention": SD_CONVENTION,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
