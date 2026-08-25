"""R0-2: §4'te vaat edilen çıkarımsal testler — eşleştirilmiş t + Holm, tek ailede.

İTİRAZ: "§4 m7 eşleştirilmiş t ve Holm düzeltmesi bildiriyor; §5'te hiçbiri raporlanmıyor."
Bu betik vaat edilen raporu üretir. n=3 / df=2'nin zayıflığı bilinen kabuldür ve tabloda
açıkça yazılır — amaç güç iddiası değil, bildirilen prosedürün dürüstçe uygulanması.

AİLE (hepsi tohum-içi eşleştirilmiş, @swa, ECE ekseni; Holm ailesi = bu liste):
  1. stage1: T* (1.3406) vs T=1            [RAF-DB doz-yanıtının nedensel çekirdeği]
  2. logit_std vs kontrol — stage1
  3. logit_std vs kontrol — primary
  4. logit_std vs kontrol — vae9182
  5. gate:oracle_error vs temiz kontrol — vae9182   [P2, ön-kayıtlı]
  6. FERPlus: T*_NLL (0.5063) vs T=1

"Her öğretmen için T* vs T=1" istendi; iki öğretmen için bu kontrast DİSKTE YOK ve tablo
bunu satır olarak söyler: primary'nin hiç sıcaklık-ölçekli kolu koşulmadı (doz-yanıt
kampanyası stage1+vae9182 idi), vae9182'nin T*'ı 0.983 ≈ 1 — kontrast tanımlı ama içeriksiz
(headroom ≈ 0; bkz. headroom_review). Yokluk sessizce atlanmaz, satırda gerekçelenir.

d=13.7 İÇİN: tohum-bazlı iki belirsizlik de veriliyor — eşleştirilmiş d_z = ort(d)/sd(d) ve
havuzlanmış-sd Cohen d — artı kolların tohum min/maks aralıkları (özetteki "no overlap"
ifadesinin dayanağı: iki kolun aralıkları kesişmiyor).

Salt-okunur, GPU yok. Çıktı -> paper_tables/inferential_tests.{md,json}
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

D = ROOT / "diagnostics"
A_AUDIT = D / "selection_audit" / "selection_audit_unfrozen.csv"
A_RUNS = ROOT / "runs.csv"
A_P2 = D / "p2_gate_oracle" / "p2_verdict.json"
A_FER = D / "ferplus_jsd" / "ferplus_student_jsd.json"
OUT_DIR = D / "paper_tables"
CK = "swa"
SEEDS = (42, 1, 43)


def load_runs():
    return list(csv.DictReader(open(A_RUNS, encoding="utf-8")))


def load_audit():
    out = {}
    for r in csv.DictReader(open(A_AUDIT, encoding="utf-8")):
        if r["checkpoint"] == CK:
            out[r["run_name"]] = float(r["ece"])
    return out


def pick(runs, **flags):
    """runs.csv'den bayrak eşleşmesiyle seç; seed -> run_name.

    TOHUM TEKİLLİĞİ KAPISI (6 Ağu 2026'da eklendi, gerçek bir hatadan sonra).
    Bu fonksiyon eskiden `out[seed] = run_name` diye SESSİZCE üzerine yazıyordu: bir tohuma
    birden çok koşu uyuyorsa runs.csv'de EN SON gelen kazanıyordu. Yani sonuç, defterin satır
    sırasına bağlıydı.

    Bu teorik bir risk değil, gerçekleşti. P6'nın 42 koşusu (`p6alpha_*`, `p6tau_*`) deftere
    girdiğinde 1 numaralı kontrastın yordamına uydular — `*_ts100` olanlar KONTROL yordamına
    (t_scale=1.0, manipulation=none), `*_ts134` olanlar TEDAVİ yordamına. Defter 6 Ağu'da
    yeniden kurulunca seçilen koşular değişti ve "RAF-DB doz-yanıtının nedensel çekirdeği"
    diye etiketlenen kontrastın Holm p'si 0.0020'den 0.0192'ye taşındı. Hiçbir hata mesajı
    çıkmadı; her hücre kendi içinde tutarlıydı.

    Aynı hata sınıfı bu kampanyada bir kez daha yaşandı (P3'ün T10 hücresine karışması) ve
    `paper_tables.py`'ye tam olarak bu kapı eklenmişti. Buraya taşınmamıştı; şimdi taşındı.

    Bir tohuma birden çok koşu uyuyorsa yordam yeterince dar değildir — bu, seçimi sıraya
    bırakmak yerine YÜKSELTİLECEK bir hatadır.
    """
    out, seen = {}, {}
    for r in runs:
        if all(str(r.get(k, "")) == str(v) for k, v in flags.items()):
            s = int(r["seed"])
            seen.setdefault(s, []).append(r["run_name"])
            out[s] = r["run_name"]
    dup = {s: n for s, n in seen.items() if len(n) > 1}
    if dup:
        detail = "\n".join(f"    seed {s}: " + ", ".join(sorted(n)) for s, n in sorted(dup.items()))
        raise RuntimeError(
            "pick(): bir tohuma birden çok koşu uyuyor — yordam yeterince dar değil, ve "
            "hangisinin seçileceği defterin satır sırasına kalırdı.\n"
            f"  yordam: {flags}\n{detail}")
    return out


def paired_from(audit, treat, ctrl):
    d = []
    for s in SEEDS:
        if s in treat and s in ctrl and treat[s] in audit and ctrl[s] in audit:
            d.append(audit[treat[s]] - audit[ctrl[s]])
    return d


def t_test(d):
    """Eşleştirilmiş t: ort(d) / (sd(d)/sqrt(n)), df = n-1, çift kuyruk."""
    n = len(d)
    m, sd = st.mean(d), sample_sd(d)
    t = m / (sd / n ** 0.5) if sd > 0 else float("inf")
    p = 2 * stats.t.sf(abs(t), df=n - 1)
    return {"n": n, "mean": m, "sd": sd, "t": t, "df": n - 1, "p_raw": p}


def holm(results):
    """Holm step-down; aile = verilen liste. adj_i = max_j<=i (m-j)(p_(j)) kuralı, 1'de kırpılır."""
    m = len(results)
    order = sorted(range(m), key=lambda i: results[i]["p_raw"])
    running = 0.0
    for rank, i in enumerate(order):
        adj = (m - rank) * results[i]["p_raw"]
        running = max(running, adj)
        results[i]["p_holm"] = min(1.0, running)


def main():
    runs = load_runs()
    audit = load_audit()

    contrasts = []

    # ORTAK YORDAM. `alpha` ve `kd_temperature` 6 Ağu 2026'da EKLENDİ, çünkü onlarsız yordam
    # P6'nın α-modülasyon (α ∈ {0.10,0.50,0.70,0.90}) ve τ-faktöriyel (T ∈ {0.3,1.2}) kollarını
    # da yakalıyordu: o koşular tam olarak bu iki ekseni oynatmak için koşuldu, dolayısıyla
    # kampanyanın standart tarifini (α=0.3, T_KD=6) şart koşmak onları tanım gereği dışarıda
    # bırakır. Bu bir sonuç-sonrası daraltma DEĞİL; eksik kalmış bir tarif şartının
    # tamamlanması — ve doğruluğu, P6 öncesi sayıları birebir yeniden üretmesiyle sınandı.
    BASE = dict(epochs="400", swa_start="200", student_head="vich",
                class_weight_mode="effective_number", alpha="0.3", kd_temperature="6.0")

    # 1. stage1 T* vs T=1
    treat = pick(runs, teacher="stage1", t_scale="1.3406", **BASE)
    ctrl = pick(runs, teacher="stage1", family="baseline", manipulation="none", **BASE)
    contrasts.append(("stage1: T*(1.3406) vs T=1", paired_from(audit, treat, ctrl)))

    # 2-4. logit_std vs kontrol, üç öğretmen
    for t in ("stage1", "primary", "vae9182"):
        treat = pick(runs, teacher=t, family="mechanism_ablation", manipulation="logit_std",
                     **{k: v for k, v in BASE.items() if k != "student_head"})
        ctrl = pick(runs, teacher=t, family="baseline", manipulation="none", **BASE)
        contrasts.append((f"{t}: logit_std vs kontrol", paired_from(audit, treat, ctrl)))

    # 5. vae9182 oracle vs temiz kontrol — P2'nin ön-kayıtlı verdict artefaktından
    p2 = json.loads(A_P2.read_text(encoding="utf-8"))
    per = p2["by_checkpoint"][CK]["per_seed"]
    contrasts.append(("vae9182: gate:oracle_error vs temiz kontrol (P2)",
                      [per[str(s)]["d_ece"] for s in SEEDS if str(s) in per]))

    # 6. FERPlus T*_NLL vs T=1
    fer = json.loads(A_FER.read_text(encoding="utf-8"))["per_run"]
    fe = {(float(r["t_scale"]), int(r["seed"])): r["ece"]
          for r in fer if r["checkpoint"] == CK}
    d_fer = [fe[(0.5063, s)] - fe[(1.0, s)] for s in SEEDS if (0.5063, s) in fe and (1.0, s) in fe]
    contrasts.append(("FERPlus: T*_NLL(0.5063) vs T=1", d_fer))

    results = []
    for name, d in contrasts:
        if len(d) != 3:
            raise RuntimeError(f"{name}: 3 eşleşmiş tohum bekleniyordu, {len(d)} bulundu")
        r = t_test(d)
        r["name"] = name
        r["per_seed"] = dict(zip(map(str, SEEDS), d))
        results.append(r)
    holm(results)

    # d=13.7 bağlamı: FERPlus kalibre-vs-doğal, iki etki büyüklüğü + kol aralıkları
    a_star = [fe[(0.5063, s)] for s in SEEDS]
    a_nat = [fe[(1.0, s)] for s in SEEDS]
    d_vals = [a - b for a, b in zip(a_star, a_nat)]
    dz = abs(st.mean(d_vals)) / sample_sd(d_vals)
    pooled = ((sample_sd(a_star) ** 2 + sample_sd(a_nat) ** 2) / 2) ** 0.5
    d_pooled = abs(st.mean(a_star) - st.mean(a_nat)) / pooled
    fer_ranges = {"tstar_arm": [min(a_star), max(a_star)], "natural_arm": [min(a_nat), max(a_nat)],
                  "overlap": not (max(a_star) < min(a_nat) or max(a_nat) < min(a_star)),
                  "d_z_paired": dz, "d_pooled": d_pooled}

    L = ["# R0-2 — Inferential tests: paired t + Holm", "",
         f"Producer: `diagnostics/inferential_tests.py` · @{CK} · ECE axis · {SD_CONVENTION} · "
         "Holm family = the six rows of this table", "",
         "> **n=3, df=2 — a known limitation.** This table is not a claim about power; it is the "
         "report of the procedure declared in §4. The campaign's actual decision instrument is "
         "pre-registered sign consistency plus 2×sd bars; the p values here sit alongside them, "
         "not in their place.", "",
         "| # | contrast | ΔECE mean ± sd | per seed | t | df | p (raw) | p (Holm) |",
         "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        per = " / ".join(f"{r['per_seed'][str(s)]:+.4f}" for s in SEEDS)
        L.append(f"| {i} | {r['name']} | {r['mean']:+.4f} ± {r['sd']:.4f} | {per} | "
                 f"{r['t']:+.2f} | {r['df']} | {r['p_raw']:.4f} | **{r['p_holm']:.4f}** |")
    L += ["",
          "**The two contrasts that were requested but cannot be supplied, with reasons:**",
          "- *primary: T\\* vs T=1* — primary has no temperature-scaled arm on disk; the "
          "dose-response campaign ran stage1+vae9182. The contrast is not measurable (it would "
          "require runs, ~7 h × 3).",
          "- *vae9182: T\\* vs T=1* — T\\*=0.983 ≈ 1 and Eq.8 headroom ≈ 0.002 "
          "(`headroom_review`): the contrast is defined but empty — there is no miscalibration to "
          "scale away. The row was not opened because a 'no difference' conclusion does not follow "
          "from it; the teacher is already calibrated.",
          "",
          "## Context for d = 13.7 (FERPlus calibrated-vs-native)", "",
          f"| quantity | value |", "|---|---|",
          f"| paired d_z = \\|mean Δ\\| / sd(Δ) | **{dz:.1f}** |",
          f"| pooled-sd Cohen d | **{d_pooled:.1f}** |",
          f"| T\\*-arm seed range | [{min(a_star):.4f}, {max(a_star):.4f}] |",
          f"| native-arm seed range | [{min(a_nat):.4f}, {max(a_nat):.4f}] |",
          f"| do the ranges overlap | **{'yes' if fer_ranges['overlap'] else 'NO'}** |", "",
          "Basis for the wording in the abstract: between the two arms' seed ranges there is "
          f"{'no gap' if fer_ranges['overlap'] else 'no intersection — \"no overlap across seeds\" can be written'}"
          ". At n=3 the point value of d is unstable (its sd denominator is estimated on two "
          "degrees of freedom); in the text, give d together with the range separation rather "
          "than on its own.", ""]

    payload = {"sd_convention": SD_CONVENTION, "checkpoint": CK, "axis": "ece",
               "family_size": len(results), "results": results, "ferplus_effect": fer_ranges,
               "not_computable": {
                   "primary_Tstar_vs_T1": "no temperature-scaled primary arm on disk",
                   "vae9182_Tstar_vs_T1": "T*=0.983~1, Eq.8 headroom ~0.002 -- contrast empty"}}
    (OUT_DIR / "inferential_tests.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "inferential_tests.json").write_text(json.dumps(payload, indent=2),
                                                   encoding="utf-8")
    for r in results:
        print(f"{r['name']:<48} d {r['mean']:+.4f}+/-{r['sd']:.4f}  t {r['t']:+7.2f}  "
              f"p {r['p_raw']:.4f}  holm {r['p_holm']:.4f}")
    print(f"\nFERPlus d_z {dz:.1f}  pooled-d {d_pooled:.1f}  overlap "
          f"{fer_ranges['overlap']}")
    print(f"Wrote {OUT_DIR / 'inferential_tests.md'}")


if __name__ == "__main__":
    main()
