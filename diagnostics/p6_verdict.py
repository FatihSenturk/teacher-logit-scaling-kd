"""P6 RESMİ HÜKMÜ — A9'un dondurulmuş üç kuralının tam örnekleme uygulanması.

STATÜ: Bu, 2 Ağu'daki erken okumanın (kuyruk ~10/42) yerini alan RESMİ hükümdür. Kuyruk
5 Ağu 16:16'da 42/42 kapandı. Kurallar 1 Ağu'da `p6-predeclared` tag'iyle (commit 3d9dbee)
dondurulmuştu; bu betik onları YENİDEN YORUMLAMAZ, yalnız uygular.

KURALLAR (PREREGISTRATIONS A9 ve `rafdb_p6_tau_alpha_queue.ps1` başlığından, harfiyen):

  P6.1 (ÇÖKME): öğrenci ECE'si (T, τ)'ya yalnız T·τ çarpımı üzerinden bağlıdır.
    @swa, tohum-içi eşleştirilmiş. Her çift için:
      |ort ΔECE| <= 2×bar VE işaretler 3/3 uyuşmuyor  -> ÇÖKME DOĞRULANDI (o çift)
      İki çiftte birden 3/3 aynı işaret VE >= 2×bar   -> ÇÖKME YANLIŞLANDI
      Başka her durum -> ÇÖZÜNMEDİ; çift başına raporlanır, genel iddia YAZILMAZ.
    BAR: 0.0012 (stage1/effective_number kontrol kolu ECE tohum sd'si @swa) -> 2×bar 0.0024.

  P6.2 (MONOTONLUK): gap(α) := ECE(T=1) − ECE(T=1.3406), tohum-içi. α arttıkça gap monoton
    azalır — α ∈ {0.1, 0.3, 0.5, 0.7, 0.9}, her tohumda ardıl her adımda ARTMAYAN;
    3/3 tohumda sağlanırsa DOĞRULANDI.

  P6.3 (UÇLAR): gap(0.9) < gap(0.1), KESİN eşitsizlik, 3/3 tohumda.

NEDEN P6.1 BURADA YENİDEN KODLANMIYOR. Beyan, resmî hükmün "erken okumayla aynı üreticiyle"
uygulanmasını şart koşuyor. Bu yüzden P6.1'in karar mantığı ve çift tanımları
`p6_1_early_reading.py`'den İTHAL EDİLİR, kopyalanmaz — böylece birebir yeniden üretim bir
söz değil, yapısal bir zorunluluk olur. Erken okumanın JSON'u varsa sayı sayıya karşılaştırılır
ve sapma OLURSA sessizce geçilmez: rapora "erken okuma yeniden üretilemedi" diye yazılır.
Erken okuma 10/42'de üretildiği için Grid 1'in o an bitmiş hücrelerini kullanmıştı; Grid 1'in
6 yeni hücresi ilk koşulan grup olduğundan (kuyruk sırası bilinçli) çiftler o gün zaten tamdı,
dolayısıyla sayıların değişmemesi BEKLENİR.

AD -> PARAMETRE KAPISI. Hiçbir hücre adından çıkarılmaz. Her koşunun kendi `run_args.json`'u
okunur ve (alpha, teacher_temperature_scale, temperature, seed) beklenenle karşılaştırılır;
uyuşmazlıkta hüküm ÜRETİLMEZ. Ad sözleşmeleri kampanya boyunca iki kez değişti (seed42
sonekli/soneksiz), bu kapı onun için var.

Veri: diagnostics/selection_audit/selection_audit_unfrozen.csv @swa (donmuş denetim dosyasına
DOKUNULMAZ; o ayrı dosyadır ve N=131 orada sabittir). Salt-okunur, GPU yok.

Çıktı -> diagnostics/paper_tables/p6_collapse_test.md   (T11 + T12)
       + diagnostics/paper_tables/p6_collapse_test.json
Kullanım: python diagnostics/p6_verdict.py
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from p6_1_early_reading import (  # noqa: E402  -- TEK KAYNAK: P6.1 mantığı ithal edilir
    DECLARED_BAR, PAIRS, SEEDS, TWO_BAR, judge_pair,
)
from p1_two_teacher_overlay import CURVES  # noqa: E402  -- TEK KAYNAK: koşu -> (öğretmen, T)
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

A_AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit_unfrozen.csv"
A_DENOM = ROOT / "diagnostics" / "paper_tables" / "denominator_table.json"
A_EARLY = ROOT / "diagnostics" / "p6_tau_alpha" / "p6_1_early_reading.json"
OUT_MD = ROOT / "diagnostics" / "paper_tables" / "p6_collapse_test.md"
OUT_JSON = ROOT / "diagnostics" / "paper_tables" / "p6_collapse_test.json"

# --- Grid 2: α modülasyonu -------------------------------------------------------------
# gap(α) := ECE(T=1) − ECE(T=1.3406), tohum-içi. α=0.3 çifti beyan gereği YENİDEN KULLANILIR
# ve adı CURVES'ten gelir (seed42 hücreleri eski, soneksiz adlar taşıyor).
ALPHA_ORDER = ["0.1", "0.3", "0.5", "0.7", "0.9"]
ALPHA_CELLS = {
    "0.1": ("RAFDB_stage1_p6alpha_a010_ts100_b070_T6_224_400e_swa200_seed{s}",
            "RAFDB_stage1_p6alpha_a010_ts134_b070_T6_224_400e_swa200_seed{s}"),
    "0.3": (None, None),          # CURVES'ten doldurulur
    "0.5": ("RAFDB_stage1_p6alpha_a050_ts100_b070_T6_224_400e_swa200_seed{s}",
            "RAFDB_stage1_p6alpha_a050_ts134_b070_T6_224_400e_swa200_seed{s}"),
    "0.7": ("RAFDB_stage1_p6alpha_a070_ts100_b070_T6_224_400e_swa200_seed{s}",
            "RAFDB_stage1_p6alpha_a070_ts134_b070_T6_224_400e_swa200_seed{s}"),
    "0.9": ("RAFDB_stage1_p6alpha_a090_ts100_b070_T6_224_400e_swa200_seed{s}",
            "RAFDB_stage1_p6alpha_a090_ts134_b070_T6_224_400e_swa200_seed{s}"),
}
TAU_GRID2 = 6.0                    # Grid 2 boyunca τ sabit


def load_swa():
    """run_name -> {ece, acc, run_dir} @swa."""
    out = {}
    for r in csv.DictReader(open(A_AUDIT, encoding="utf-8")):
        if r["checkpoint"] == "swa":
            out[r["run_name"]] = {"ece": float(r["ece"]), "acc": float(r["acc"]),
                                  "run_dir": r["run_dir"]}
    return out


def _ledger():
    """run_name -> defter satırı. Ad->parametre kapısının kaynağı (Level-1, 8 Ağu)."""
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = {r["run_name"]: r
                   for r in csv.DictReader(open(ROOT / "runs.csv", encoding="utf-8"))}
    return _LEDGER


_LEDGER = None


def check_params(run_name, rec, *, alpha=None, t_scale=None, tau=None, seed=None):
    """Ad -> parametre kapısı. Koşunun KAYITLI parametreleri beklenenle uyuşmalı.

    LEVEL-1 (8 Ağu). Bu kapı koşunun `run_args.json`'unu açıyordu ve tek başına bu betiği
    yayımlanmayan `results/unified_students/`'a bağımlı yapıyordu. İhtiyaç duyduğu dört alan
    (`alpha`, `teacher_temperature_scale`, `temperature`, `seed`) DEFTERDE zaten var ve
    defter onları aynı `run_args.json`'lardan çıkarıyor -- yani kapı hiçbir şey kaybetmiyor,
    yalnız aynı bilgiyi yayımlanan katmandan okuyor. Ad tahmini yapılmıyor: eşleşen defter
    satırı yoksa hüküm durur.
    """
    row = _ledger().get(run_name)
    if row is None:
        raise RuntimeError(
            f"AD/PARAMETRE KAPISI — {run_name} runs.csv'de yok. Defter eski olabilir "
            f"(`python diagnostics/build_runs_ledger.py`); ad tahminine düşülmeyecek.")
    got = {"alpha": float(row["alpha"]),
           "t_scale": float(row["t_scale"] or 1.0),
           "tau": float(row["kd_temperature"]),
           "seed": int(row["seed"])}
    want = {"alpha": alpha, "t_scale": t_scale, "tau": tau, "seed": seed}
    for k, v in want.items():
        if v is None:
            continue
        if abs(got[k] - float(v)) > 1e-9:
            raise RuntimeError(
                f"AD/PARAMETRE UYUŞMAZLIĞI — {run_name}: {k} beklenen {v}, run_args {got[k]}. "
                "Hüküm üretilmedi; önce eşlemeyi düzelt.")
    return got


def p6_1(swa):
    """Dondurulmuş P6.1 — mantık p6_1_early_reading'den ithal, burada yeniden yazılmaz."""
    pairs_out = {}
    for pname, cells in PAIRS.items():
        d, per_seed = [], {}
        for s in SEEDS:
            lo_run = cells["lo"][0].format(s=s)
            hi_run = cells["hi"][0].format(s=s)
            for rn in (lo_run, hi_run):
                if rn not in swa:
                    raise RuntimeError(f"{pname}: {rn} denetimde yok — hüküm EKSİK VERİYLE "
                                       "üretilmez. Önce selection_audit_table.py --ignore-cutoff")
            check_params(lo_run, swa[lo_run], tau=cells["lo"][1],
                         t_scale=cells["lo"][2], alpha=0.3, seed=s)
            check_params(hi_run, swa[hi_run], tau=cells["hi"][1],
                         t_scale=cells["hi"][2], alpha=0.3, seed=s)
            dv = swa[lo_run]["ece"] - swa[hi_run]["ece"]
            d.append(dv)
            per_seed[str(s)] = {"d_ece": dv,
                                "lo": {"run": lo_run, "ece": swa[lo_run]["ece"]},
                                "hi": {"run": hi_run, "ece": swa[hi_run]["ece"]}}
        v = judge_pair(d)                       # <- dondurulmuş karar fonksiyonu, ithal
        v["per_seed"] = per_seed
        v["tau_lo"], v["T_lo"] = cells["lo"][1], cells["lo"][2]
        v["tau_hi"], v["T_hi"] = cells["hi"][1], cells["hi"][2]
        pairs_out[pname] = v

    both_falsify = all(v["falsify_leg"] for v in pairs_out.values())
    both_confirm = all(v["confirm"] for v in pairs_out.values())
    if both_falsify:
        overall = ("ÇÖKME YANLIŞLANDI — iki çiftte birden 3/3 aynı işaret ve |ort ΔECE| ≥ "
                   "2×bar. Beyanın kendi sözleriyle: ayrışmanın kendisi bulgu — sıra bilgisi "
                   "ile yumuşaklık ayrı kanallar.")
    elif both_confirm:
        overall = ("Her iki çift için AYRI AYRI ÇÖKME DOĞRULANDI. (Kural DOĞRULANDI'yı çift "
                   "başına tanımlar; genel iddia yine de yazılmaz.)")
    else:
        overall = ("Karışık tablo → çift başına raporlanır, genel iddia YAZILMAZ "
                   "(beyandaki 'başka her durum' kolu).")
    return pairs_out, overall


def reproduces_early(pairs_out):
    """Erken okumayı birebir yeniden üretiyor muyuz? Sapma gizlenmez, raporlanır."""
    if not A_EARLY.exists():
        return {"checked": False, "reason": "erken okuma JSON'u yok"}
    early = json.loads(A_EARLY.read_text(encoding="utf-8"))
    diffs = []
    for pname, v in pairs_out.items():
        ev = early.get("pairs", {}).get(pname)
        if ev is None:
            diffs.append(f"{pname}: erken okumada yok")
            continue
        for s in SEEDS:
            a = v["per_seed"][str(s)]["d_ece"]
            b = ev["per_seed"][str(s)]["d_ece"]
            if abs(a - b) > 1e-12:
                diffs.append(f"{pname} tohum {s}: ΔECE {b:.6f} -> {a:.6f}")
        if ev["status"] != v["status"]:
            diffs.append(f"{pname}: statü {ev['status']} -> {v['status']}")
    return {"checked": True, "identical": not diffs, "diffs": diffs}


def p6_2_3(swa):
    """gap(α) tablosu + P6.2 (monotonluk) ve P6.3 (uçlar) hükümleri."""
    cells = dict(ALPHA_CELLS)
    # CURVES anahtarları float (T) ve int (tohum) — string değil. Değeri literalden değil,
    # yakınlıkla seçiyoruz ki ileride 1.3406 -> 1.34 gibi bir yazım değişikliği sessizce
    # yanlış hücre getirmesin.
    def curve_at(T):
        ks = [k for k in CURVES["stage1"] if abs(float(k) - T) < 1e-9]
        if len(ks) != 1:
            raise RuntimeError(f"CURVES['stage1'] içinde T={T} için {len(ks)} eşleşme")
        return CURVES["stage1"][ks[0]]
    cells["0.3"] = (curve_at(1.0), curve_at(1.3406))   # dict: tohum(int) -> koşu adı

    gaps, per_alpha = {}, {}
    for a in ALPHA_ORDER:
        lo_t, hi_t = cells[a]
        row = {}
        for s in SEEDS:
            lo = lo_t[s] if isinstance(lo_t, dict) else lo_t.format(s=s)
            hi = hi_t[s] if isinstance(hi_t, dict) else hi_t.format(s=s)
            for rn in (lo, hi):
                if rn not in swa:
                    raise RuntimeError(f"α={a}: {rn} denetimde yok — hüküm EKSİK VERİYLE "
                                       "üretilmez.")
            check_params(lo, swa[lo], alpha=float(a), t_scale=1.0, tau=TAU_GRID2, seed=s)
            check_params(hi, swa[hi], alpha=float(a), t_scale=1.3406, tau=TAU_GRID2, seed=s)
            row[str(s)] = {"gap": swa[lo]["ece"] - swa[hi]["ece"],
                           "ece_T1": swa[lo]["ece"], "ece_T134": swa[hi]["ece"],
                           "run_T1": lo, "run_T134": hi}
        gaps[a] = {str(s): row[str(s)]["gap"] for s in SEEDS}
        per_alpha[a] = row

    # P6.2 — her tohumda ardıl adımlarda ARTMAYAN
    mono = {}
    for s in SEEDS:
        seq = [gaps[a][str(s)] for a in ALPHA_ORDER]
        steps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
        ok = all(x <= 0 for x in steps)
        mono[str(s)] = {"sequence": seq, "steps": steps, "non_increasing": ok,
                        "violations": [f"{ALPHA_ORDER[i]}→{ALPHA_ORDER[i + 1]} ({steps[i]:+.4f})"
                                       for i, x in enumerate(steps) if x > 0]}
    n_mono = sum(1 for s in SEEDS if mono[str(s)]["non_increasing"])
    p62 = {"per_seed": mono, "n_seeds_ok": n_mono,
           "verdict": ("DOĞRULANDI" if n_mono == 3 else "DOĞRULANMADI"),
           "rule": "gap(α) α arttıkça monoton azalır (ardıl adımlarda artmayan), 3/3 tohumda"}

    # P6.3 — gap(0.9) < gap(0.1), kesin, 3/3
    ends = {}
    for s in SEEDS:
        lo_a, hi_a = gaps["0.1"][str(s)], gaps["0.9"][str(s)]
        ends[str(s)] = {"gap_0.1": lo_a, "gap_0.9": hi_a, "strict_less": hi_a < lo_a,
                        "delta": hi_a - lo_a}
    n_ends = sum(1 for s in SEEDS if ends[str(s)]["strict_less"])
    p63 = {"per_seed": ends, "n_seeds_ok": n_ends,
           "verdict": ("DOĞRULANDI" if n_ends == 3 else "DOĞRULANMADI"),
           "rule": "gap(0.9) < gap(0.1), kesin eşitsizlik, 3/3 tohumda"}
    return per_alpha, gaps, p62, p63


def main():
    # Konsol cp1252; bu betiğin çıktısı τ/α/± taşıyor. Dosyalar utf-8 yazılıyor, kıran
    # yalnız print'ti (status_heartbeat.py'de aynı hata).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    denom = json.loads(A_DENOM.read_text(encoding="utf-8"))
    src_sd = denom["control_arms"]["stage1/effective_number"]["ece_sd"]
    assert denom["checkpoint"] == "swa", "denominator_table @swa değil"
    if round(src_sd, 4) != DECLARED_BAR:
        raise RuntimeError(f"bar uyuşmazlığı: beyan {DECLARED_BAR}, kaynak {src_sd:.6f} — "
                           "kural yeniden yorumlanamaz, önce uyuşmazlığı raporla")

    swa = load_swa()
    pairs_out, overall_61 = p6_1(swa)
    repro = reproduces_early(pairs_out)
    per_alpha, gaps, p62, p63 = p6_2_3(swa)

    L = ["# P6 — resmî hüküm: T·τ çökme testi ve α modülasyonu (T11 + T12)", "",
         "Kuyruk **42/42** kapandı (5 Ağu 2026 16:16). Kurallar 1 Ağu'da `p6-predeclared` "
         "tag'iyle donduruldu (commit `3d9dbee`); bu tablo onları uygular, yeniden yorumlamaz.",
         "",
         f"Üretici: `diagnostics/p6_verdict.py` · @swa · {SD_CONVENTION} · "
         f"bar {DECLARED_BAR} (kaynak sd {src_sd:.6f}, `denominator_table.json`) · "
         f"2×bar {TWO_BAR}", "",
         "P6.1'in karar mantığı ve çift tanımları `p6_1_early_reading.py`'den **ithal edilir**, "
         "kopyalanmaz — beyanın 'aynı üreticiyle' şartı böylece yapısal olarak sağlanır.", "",
         "> **Hangi hakem itirazına karşılık geliyor.** Round-2 panelinin Devil's Advocate "
         "raporu, \"yapılmamış belirleyici deney\" olarak tam olarak bu testi gösteriyor: "
         "*\"varying τ at fixed T (or α) would separate 'confidence structure' from "
         "composite-softness/optimization accounts within a single teacher\"* "
         "(DA-C2 ve Ignored-Alternatives). P6 bu deneydir ve 42 koşuyla koşulmuştur; hüküm "
         "aşağıdadır. Beyan koşulardan önce (1 Ağu, `p6-predeclared`), itiraz ise sonra "
         "(5 Ağu) geldi — yani test itiraza göre tasarlanmadı, itirazdan bağımsız olarak "
         "zaten ön-kayıtlıydı.", "",
         "---", "", "## T11 — Grid 1: eşleşmiş T·τ çiftleri (P6.1)", ""]

    for pname, v in pairs_out.items():
        L += [f"### Çift {pname}: (τ={v['tau_lo']}, T={v['T_lo']}) − "
              f"(τ={v['tau_hi']}, T={v['T_hi']})", "",
              "| tohum | ECE küçük-τ | ECE büyük-τ | ΔECE |", "|---|---|---|---|"]
        for s in SEEDS:
            ps = v["per_seed"][str(s)]
            L.append(f"| {s} | {ps['lo']['ece']:.4f} | {ps['hi']['ece']:.4f} | "
                     f"{ps['d_ece']:+.4f} |")
        L += ["",
              f"ort ΔECE **{v['mean']:+.4f} ± {v['sd']:.4f}** · işaretler "
              f"{'3/3 aynı' if v['same_sign_3of3'] else '3/3 aynı DEĞİL'} · "
              f"|ort|/2×bar = {abs(v['mean']) / TWO_BAR:.2f}×", "",
              f"**{v['status']}**", ""]

    L += ["### P6.1 hükmü", "", overall_61, ""]
    if repro["checked"]:
        if repro["identical"]:
            L += ["**Erken okuma birebir yeniden üretildi** (2 Ağu, kuyruk ~10/42): altı ΔECE "
                  "değerinin tamamı ve iki çift statüsü aynı. Beyanın öngördüğü gibi — koşu-başına "
                  "önbellek aynı ölçümleri taşıyor.", ""]
        else:
            L += ["> ⚠️ **Erken okuma yeniden ÜRETİLEMEDİ.** Beyan bunun bir bulgu olarak "
                  "yazılmasını gerektiriyor; gizlenmez:", ""]
            L += [f"> - {d}" for d in repro["diffs"]] + [""]
    else:
        L += [f"_Erken okuma karşılaştırması yapılamadı: {repro['reason']}._", ""]

    L += ["---", "", "## T12 — Grid 2: α modülasyonu (P6.2, P6.3)", "",
          "gap(α) := ECE(T=1) − ECE(T=1.3406), tohum-içi · τ=6 sabit", "",
          "| α | tohum 42 | tohum 1 | tohum 43 | ort |", "|---|---|---|---|---|"]
    for a in ALPHA_ORDER:
        vals = [gaps[a][str(s)] for s in SEEDS]
        L.append(f"| {a} | " + " | ".join(f"{v:+.4f}" for v in vals) +
                 f" | **{st.mean(vals):+.4f}** |")
    L += ["", f"_α=0.3 satırı beyan gereği mevcut doz-yanıt kollarından yeniden kullanıldı "
              f"(`CURVES`), yeni koşu değil._", "",
          "### P6.2 — monotonluk", "", f"Kural: {p62['rule']}", "",
          "| tohum | gap dizisi (α=0.1→0.9) | ardıl adımlar | artmayan? |", "|---|---|---|---|"]
    for s in SEEDS:
        m = p62["per_seed"][str(s)]
        L.append(f"| {s} | " + ", ".join(f"{x:+.4f}" for x in m["sequence"]) + " | " +
                 ", ".join(f"{x:+.4f}" for x in m["steps"]) + " | " +
                 ("✅" if m["non_increasing"] else "❌ " + "; ".join(m["violations"])) + " |")
    L += ["", f"**P6.2 {p62['verdict']}** — {p62['n_seeds_ok']}/3 tohumda sağlandı.", "",
          "### P6.3 — uçlar", "", f"Kural: {p63['rule']}", "",
          "| tohum | gap(0.1) | gap(0.9) | gap(0.9) − gap(0.1) | gap(0.9) < gap(0.1)? |",
          "|---|---|---|---|---|"]
    for s in SEEDS:
        e = p63["per_seed"][str(s)]
        L.append(f"| {s} | {e['gap_0.1']:+.4f} | {e['gap_0.9']:+.4f} | {e['delta']:+.4f} | " +
                 ("✅" if e["strict_less"] else "❌") + " |")
    L += ["", f"**P6.3 {p63['verdict']}** — {p63['n_seeds_ok']}/3 tohumda sağlandı.", "",
          "---", "",
          "Kaynak: `diagnostics/selection_audit/selection_audit_unfrozen.csv` @swa. Donmuş "
          "denetim dosyası (`selection_audit.csv`, N=131) bu turda **değişmedi** — ayrı dosyadır.",
          ""]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"status": "OFFICIAL_VERDICT", "queue_state": "42/42", "checkpoint": "swa",
         "sd_convention": SD_CONVENTION, "bar": DECLARED_BAR, "two_bar": TWO_BAR,
         "bar_source_sd": src_sd,
         "p6_1": {"pairs": pairs_out, "overall": overall_61,
                  "reproduces_early_reading": repro},
         "p6_2": p62, "p6_3": p63,
         "grid2_cells": per_alpha, "alpha_order": ALPHA_ORDER},
        indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== P6.1 ===")
    for pname, v in pairs_out.items():
        print(f"  {pname}: ort {v['mean']:+.4f} ± {v['sd']:.4f} -> {v['status']}")
    print(f"  GENEL: {overall_61}")
    print(f"  erken okuma birebir mi: {repro}")
    print(f"=== P6.2 === {p62['verdict']} ({p62['n_seeds_ok']}/3)")
    print(f"=== P6.3 === {p63['verdict']} ({p63['n_seeds_ok']}/3)")
    print(f"\nWrote {OUT_MD}")


if __name__ == "__main__":
    main()
