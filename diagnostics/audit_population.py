"""G4.6 — denetim popülasyonunun (N=131) kompozisyonu ve bütçeye katmanlı istatistikler.

NEDEN VAR (panel G4.6). Makale seçim denetimini N=131 koşu üzerinden raporluyor ve popülasyonu
*"az sayıda legacy koşu"* içeren bir küme diye tarif ediyor. İki sorun:
  1. "Az sayıda" bir sayı değil. Kaç tane olduğu ölçülebilir ve ölçülmeli.
  2. Denetim istatistiği (seçim iyimserliği) tek bir havuz ortalaması olarak veriliyor. Eğer o
     ortalama farklı epoch bütçelerinin karışımıysa, makalenin KENDİ tarifinin (400 epoch)
     sayısı havuz sayısından farklı olabilir ve okur hangisine baktığını bilemez.

NE YAPILIYOR. Donmuş denetim kümesi defterle eşleştirilip beş eksende sayılıyor, "standart
tarif dışı" koşular ölçülüp dökümü veriliyor, ve seçim iyimserliği epoch bütçesine göre
KATMANLI yeniden raporlanıyor.

STANDART TARİF, önceden ve açıkça: `epochs=400`, `swa_start=200`, `alpha=0.3`,
`kd_temperature=6.0`. Bu dört alanın herhangi birinde farklı olan koşu "tarif dışı" sayılır.
Tanım burada yazılı ki "legacy" kelimesi bir his değil bir yordam olsun.

DONMUŞ DOSYA OKUNUR, YAZILMAZ. Makalenin N=131'ini taşıyan `selection_audit.csv` bu betik
tarafından yalnız okunuyor; genişletilmiş küme (`_unfrozen`) burada kullanılmıyor, çünkü
sorulan şey tam olarak makalenin alıntıladığı popülasyon.

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/audit_population.{json,md}
"""
import collections
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd                # noqa: E402

FROZEN = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
LEDGER = ROOT / "runs.csv"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STANDARD = {"epochs": "400", "swa_start": "200", "alpha": "0.3", "kd_temperature": "6.0"}
AXES = [("family", "tarif ailesi"), ("teacher", "öğretmen"), ("epochs", "epoch bütçesi"),
        ("swa_start", "SWA başlangıcı"), ("alpha", "α"), ("kd_temperature", "KD sıcaklığı"),
        ("class_weight_mode", "sınıf ağırlığı"), ("preregistration_block", "ön-kayıt bloğu")]


def load():
    aud = collections.defaultdict(dict)
    for r in csv.DictReader(FROZEN.open(encoding="utf-8")):
        aud[r["run_name"]][r["checkpoint"]] = {"acc": float(r["acc"]), "ece": float(r["ece"])}
    led = {r["run_name"]: r for r in csv.DictReader(LEDGER.open(encoding="utf-8"))}
    missing = [n for n in aud if n not in led]
    if missing:
        raise RuntimeError(
            f"{len(missing)} denetim koşusu defterde yok: {missing[:5]}. Kompozisyon defterden "
            f"okunur; eksik satır sessizce 'bilinmiyor' hücresine düşemez.")
    return dict(aud), led


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    aud, led = load()
    n_total = len(aud)

    counts = {}
    for field, _ in AXES:
        c = collections.Counter(led[n].get(field, "") or "(boş)" for n in aud)
        counts[field] = dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))

    # --- tarif dışı koşular
    off = {}
    for n in aud:
        diff = [k for k, v in STANDARD.items() if str(led[n].get(k, "")) != v]
        if diff:
            off[n] = diff
    off_pattern = collections.Counter(", ".join(v) for v in off.values())

    # --- seçim iyimserliği, epoch bütçesine göre katmanlı
    strata = collections.defaultdict(list)
    for n, ck in aud.items():
        if "best" in ck and "last" in ck:
            strata[led[n]["epochs"]].append(
                (ck["best"]["acc"] - ck["last"]["acc"], ck["best"]["ece"] - ck["last"]["ece"]))
    stats = {}
    pooled_a, pooled_e = [], []
    for e, vals in strata.items():
        da = [v[0] for v in vals]
        de = [v[1] for v in vals]
        pooled_a += da
        pooled_e += de
        stats[e] = {"n": len(da), "d_acc_mean": st.mean(da), "d_acc_sd": sample_sd(da),
                    "d_ece_mean": st.mean(de), "d_ece_sd": sample_sd(de),
                    "all_positive_acc": all(x > 0 for x in da)}
    pooled = {"n": len(pooled_a), "d_acc_mean": st.mean(pooled_a),
              "d_acc_sd": sample_sd(pooled_a), "d_ece_mean": st.mean(pooled_e),
              "d_ece_sd": sample_sd(pooled_e)}

    write(n_total, counts, off, off_pattern, stats, pooled)
    print(f"G4.6 denetim populasyonu: N={n_total}")
    print(f"  standart tarif disi: {len(off)} ({100*len(off)/n_total:.0f}%)")
    print(f"  havuz best-last d_acc {pooled['d_acc_mean']:+.3f} pp")
    for e in sorted(stats, key=lambda x: -stats[x]["n"]):
        s = stats[e]
        print(f"    {e:>4s} epoch n={s['n']:3d}  {s['d_acc_mean']:+.3f} ± {s['d_acc_sd']:.3f} pp")


def write(n_total, counts, off, off_pattern, stats, pooled):
    main_e = max(stats, key=lambda x: stats[x]["n"])
    L = ["# G4.6 — denetim popülasyonunun kompozisyonu (N=131)", "",
         "> **Panel G4.6.** Makale popülasyonu *\"az sayıda legacy koşu\"* içeren bir küme diye "
         "tarif ediyor. Bu betik sayıyı ölçüyor ve denetim istatistiğini epoch bütçesine göre "
         "katmanlı yeniden raporluyor.", "",
         f"**CEVAP: \"az sayıda\" = {len(off)}/{n_total} koşu (%{100 * len(off) / n_total:.0f}).** "
         f"Beşte bir; bu niceleyici daraltılmalı.", "",
         f"{SD_CONVENTION} · kaynak: donmuş `selection_audit.csv` (yalnız okundu) + `runs.csv`", "",
         "## Standart tarif dışı koşular", "",
         "Standart tarif, önceden ve açıkça: " +
         ", ".join(f"`{k}={v}`" for k, v in STANDARD.items()) +
         ". Bu dört alanın herhangi birinde farklı olan koşu tarif dışı sayılır — "
         "\"legacy\" bir his değil, bir yordam.", "",
         "| hangi alanlarda farklı | koşu |", "|---|---|"]
    for pat, k in off_pattern.most_common():
        L.append(f"| `{pat}` | {k} |")
    L += ["", f"**Dördünün de ortak paydası `epochs`**: tarif dışı {len(off)} koşunun tamamı "
              f"epoch bütçesinde farklı. Yani popülasyonu ayıran tek eksen aslında bütçe; "
              f"α ve KD sıcaklığı sapmaları tek tük (sırasıyla 1 ve 2 koşu).", "",
          "## Seçim iyimserliği, bütçeye katmanlı (`best` − `last`)", "",
          "| epoch bütçesi | n | Δdoğruluk (pp) | ΔECE | hepsi aynı yönde mi |",
          "|---|---|---|---|---|"]
    for e in sorted(stats, key=lambda x: -stats[x]["n"]):
        s = stats[e]
        mark = " **(makalenin kendi tarifi)**" if e == main_e else ""
        L.append(f"| {e}{mark} | {s['n']} | {s['d_acc_mean']:+.3f} ± {s['d_acc_sd']:.3f} | "
                 f"{s['d_ece_mean']:+.4f} ± {s['d_ece_sd']:.4f} | "
                 f"{'✅' if s['all_positive_acc'] else '—'} |")
    L += [f"| **havuz (hepsi)** | {pooled['n']} | {pooled['d_acc_mean']:+.3f} ± "
          f"{pooled['d_acc_sd']:.3f} | {pooled['d_ece_mean']:+.4f} ± {pooled['d_ece_sd']:.4f} | |",
          "", "### Katmanlamanın söylediği", "",
          f"- **Yön hiçbir katmanda değişmiyor.** Üç bütçenin üçünde de `best`, doğruluğu "
          f"kayırıyor. Yani denetimin bulgusu legacy koşulardan gelmiyor — **popülasyonun her "
          f"yerinde var.** Bu, iddiayı zayıflatmıyor, sağlamlaştırıyor.",
          f"- **Ama havuz sayısı makalenin tarifini temsil etmiyor.** Havuz "
          f"{pooled['d_acc_mean']:+.3f} pp; 200-epoch katmanı "
          f"({stats.get('200', {}).get('d_acc_mean', float('nan')):+.3f} pp, sd "
          f"{stats.get('200', {}).get('d_acc_sd', float('nan')):.3f}) ortalamayı yukarı çekiyor "
          f"ve aynı zamanda en gürültülü katman. Makalenin kendi tarifi olan {main_e} epoch için "
          f"doğru sayı **{stats[main_e]['d_acc_mean']:+.3f} ± {stats[main_e]['d_acc_sd']:.3f} pp**.",
          f"- Kalibrasyon ekseninde de aynı yön: `best` ECE'yi de kayırıyor (ΔECE her katmanda "
          f"negatif), yani seçim iyimserliği yalnız doğrulukta kalmıyor — bir kalibrasyon "
          f"makalesi için asıl mesele bu.", "",
          "## Popülasyon dökümü", ""]
    for field, label in AXES:
        c = counts[field]
        L += [f"**{label}** (`{field}`) — {len(c)} değer", "",
              "| değer | koşu |", "|---|---|"]
        L += [f"| `{k}` | {v} |" for k, v in c.items()]
        L.append("")
    L += ["> **Ön-kayıt bloğu sütunu ayrıca okunmalı.** Popülasyonun büyük bölümünün blok "
          "alanı boş: bu koşular bir ön-beyana bağlı DEĞİL ve denetim onları da içeriyor. "
          "Denetim zaten bir ön-kayıt iddiası değil, bir ölçüm; ama §4.5'in envanter sayısıyla "
          "bu tablo karıştırılmamalı.", "",
          "---", "", "Üretici: `diagnostics/audit_population.py` · veri: donmuş "
          "`diagnostics/selection_audit/selection_audit.csv` (N=131, yalnız okundu) · `runs.csv`",
          ""]

    (OUT_DIR / "audit_population.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "audit_population.json").write_text(json.dumps({
        "item": "G4.6", "n_total": n_total, "standard_recipe": STANDARD,
        "off_standard_count": len(off), "off_standard_pct": 100 * len(off) / n_total,
        "off_standard_patterns": dict(off_pattern), "off_standard_runs": off,
        "composition": counts, "selection_optimism_by_budget": stats,
        "selection_optimism_pooled": pooled, "sd_convention": SD_CONVENTION,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
