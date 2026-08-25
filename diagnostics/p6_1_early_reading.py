"""P6.1 ERKEN OKUMASI — eşleşmiş T·τ çiftlerine dondurulmuş kuralın uygulanması.

STATÜ: Bu bir ERKEN OKUMADIR (kuyruk ~10/42 iken; Fatih'in 2 Ağu isteği). Yön bilgisi
üretir; makaleye GİRMEZ (P6 tez / 3. çalışma verisidir). Resmi hüküm kuyruk 42/42
bitince PREREGISTRATIONS A9'a işlenir — per-run önbellek (selection_audit.json) aynı
ölçümleri yeniden kullandığı için resmi hüküm bu okumayla sayı sayıya aynı olmalıdır;
farklıysa bu betik değil, veri değişmiş demektir ve bunun kendisi rapor edilir.

KURAL (rafdb_p6_tau_alpha_queue.ps1 beyanından, 1 Ağu 2026, kelimesi kelimesine):
  P6.1 (ÇÖKME tahmini): öğrenci ECE'si (T, τ)'ya yalnız T·τ çarpımı üzerinden bağlıdır.
  KARAR KURALI (@swa, tohum-içi eşleştirilmiş):
    Her eşleşmiş çift için:
      |ort dECE| <= 2 x kontrol ECE tohum sd'si  VE  işaretler 3/3 uyuşmuyor
          -> ÇÖKME DOĞRULANDI (o çift için)
    İki çiftte birden 3/3 aynı işaret VE |ort dECE| >= 2 x bar
          -> ÇÖKME YANLIŞLANDI (ayrışmanın kendisi bulgu)
    Başka her durum -> ÇÖZÜNMEDİ; çift başına raporlanır, genel iddia YAZILMAZ.
  BAR: stage1/effective_number kontrol kolunun ECE tohum sd'si @swa = 0.0012
       (diagnostics/paper_tables/denominator_table.json) -> 2xbar 0.0024.

dECE YÖN SÖZLEŞMESİ (burada sabitleniyor; kural işaret-simetrik olduğundan hükmü
etkilemez): d = ECE(küçük-τ hücresi) - ECE(büyük-τ hücresi).
  Çift 5.10 : d = ECE(τ=3, T=1.70) - ECE(τ=6, T=0.85)
  Çift 10.20: d = ECE(τ=6, T=1.70) - ECE(τ=12, T=0.85)

Veri: selection_audit_unfrozen.csv @swa (yeni hücreler CPU'da ölçüldü, GPU'daki
kuyruğa dokunulmadı). τ=6 hücreleri mevcut tempscale kollarından yeniden kullanılır
(beyanda böyle). Salt-okunur, GPU yok.
Çıktı -> diagnostics/reports/2026-08-02_p6_1_early_reading.md
       + diagnostics/p6_tau_alpha/p6_1_early_reading.json
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

A_AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit_unfrozen.csv"
A_DENOM = ROOT / "diagnostics" / "paper_tables" / "denominator_table.json"
OUT_MD = ROOT / "diagnostics" / "reports" / "2026-08-02_p6_1_early_reading.md"
OUT_JSON = ROOT / "diagnostics" / "p6_tau_alpha" / "p6_1_early_reading.json"

SEEDS = (42, 1, 43)
DECLARED_BAR = 0.0012          # beyandan; aşağıda denominator_table'a karşı doğrulanır
TWO_BAR = 2 * DECLARED_BAR     # 0.0024

# çift adı -> (küçük-τ hücre şablonu, büyük-τ hücre şablonu, τ'lar, T'ler)
PAIRS = {
    "T·τ = 5.10": {
        "lo": ("RAFDB_stage1_p6tau_T03_ts170_b070_224_400e_swa200_seed{s}", 3, "1.70"),
        "hi": ("RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed{s}", 6, "0.85"),
    },
    "T·τ = 10.20": {
        "lo": ("RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed{s}", 6, "1.70"),
        "hi": ("RAFDB_stage1_p6tau_T12_ts085_b070_224_400e_swa200_seed{s}", 12, "0.85"),
    },
}


def load_swa():
    out = {}
    for r in csv.DictReader(open(A_AUDIT, encoding="utf-8")):
        if r["checkpoint"] == "swa":
            out[r["run_name"]] = {"ece": float(r["ece"]), "acc": float(r["acc"])}
    return out


def judge_pair(d):
    """Beyandaki üç durumun çift-düzeyi bileşenleri."""
    m = st.mean(d)
    same_sign = all(x > 0 for x in d) or all(x < 0 for x in d)
    confirm = abs(m) <= TWO_BAR and not same_sign
    falsify_leg = same_sign and abs(m) >= TWO_BAR
    if confirm:
        status = "ÇÖKME DOĞRULANDI (bu çift için)"
    elif falsify_leg:
        status = "YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar)"
    else:
        status = "ÇÖZÜNMEDİ (bu çift için)"
    return {"mean": m, "sd": sample_sd(d), "same_sign_3of3": same_sign,
            "confirm": confirm, "falsify_leg": falsify_leg, "status": status}


def main():
    # bar, beyanın gösterdiği kaynakla hâlâ uyuşuyor mu?
    denom = json.loads(A_DENOM.read_text(encoding="utf-8"))
    src_sd = denom["control_arms"]["stage1/effective_number"]["ece_sd"]
    assert denom["checkpoint"] == "swa", "denominator_table @swa değil"
    if round(src_sd, 4) != DECLARED_BAR:
        raise RuntimeError(f"bar uyuşmazlığı: beyan {DECLARED_BAR}, kaynak {src_sd:.6f} — "
                           "kural yeniden yorumlanamaz, önce uyuşmazlığı raporla")

    swa = load_swa()
    pairs_out, rows = {}, []
    for pname, cells in PAIRS.items():
        d, per_seed = [], {}
        for s in SEEDS:
            lo_run = cells["lo"][0].format(s=s)
            hi_run = cells["hi"][0].format(s=s)
            for rn in (lo_run, hi_run):
                if rn not in swa:
                    raise RuntimeError(f"{pname}: {rn} denetimde yok — erken okuma eksik "
                                       "veriyle YAPILMAZ")
            dv = swa[lo_run]["ece"] - swa[hi_run]["ece"]
            d.append(dv)
            per_seed[str(s)] = {"d_ece": dv,
                                "lo": {"run": lo_run, **swa[lo_run]},
                                "hi": {"run": hi_run, **swa[hi_run]}}
        v = judge_pair(d)
        v["per_seed"] = per_seed
        v["tau_lo"], v["T_lo"] = cells["lo"][1], cells["lo"][2]
        v["tau_hi"], v["T_hi"] = cells["hi"][1], cells["hi"][2]
        pairs_out[pname] = v

    both_falsify = all(v["falsify_leg"] for v in pairs_out.values())
    both_confirm = all(v["confirm"] for v in pairs_out.values())
    if both_falsify:
        overall = ("ÇÖKME YANLIŞLANDI — iki çiftte birden 3/3 aynı işaret ve |ort dECE| ≥ "
                   "2×bar. Beyanın kendi sözleriyle: ayrışmanın kendisi bulgu — sıra bilgisi "
                   "ile yumuşaklık ayrı kanallar.")
    elif both_confirm:
        overall = ("Her iki çift için AYRI AYRI ÇÖKME DOĞRULANDI. (Kural DOĞRULANDI'yı çift "
                   "başına tanımlar; genel iddia yine de yazılmaz.)")
    else:
        overall = ("Karışık tablo → çift başına raporlanır, genel iddia YAZILMAZ "
                   "(beyandaki 'başka her durum' kolu).")

    L = ["# P6.1 erken okuması — T·τ çökme testi (2 Ağu 2026)", "",
         "> **ERKEN OKUMA.** Kuyruk ~10/42'deyken, Fatih'in 2 Ağu isteğiyle üretildi. "
         "Yön bilgisidir; **makaleye girmez** (P6 → T11/T12, tez / 3. çalışma). Resmi hüküm "
         "kuyruk 42/42 bitince PREREGISTRATIONS A9'a işlenir; per-run önbellek aynı ölçümleri "
         "kullandığından sayılar orada birebir aynı çıkmalıdır.", "",
         f"Üretici: `diagnostics/p6_1_early_reading.py` · @swa · {SD_CONVENTION} · "
         f"bar {DECLARED_BAR} (kaynak sd {src_sd:.6f}, `denominator_table.json`) · "
         f"2×bar {TWO_BAR}", "",
         "Kural beyandan kelimesi kelimesine (`rafdb_p6_tau_alpha_queue.ps1`, 1 Ağu, "
         "commit 3d9dbee): çift için |ort dECE| ≤ 2×bar VE işaretler 3/3 uyuşmuyor → ÇÖKME "
         "DOĞRULANDI (o çift için); iki çiftte birden 3/3 aynı işaret VE |ort| ≥ 2×bar → "
         "ÇÖKME YANLIŞLANDI; başka her durum → ÇÖZÜNMEDİ, genel iddia yazılmaz.", "",
         "Yön sözleşmesi: d = ECE(küçük-τ) − ECE(büyük-τ); kural işaret-simetrik, sözleşme "
         "hükmü etkilemez.", ""]
    for pname, v in pairs_out.items():
        L += [f"## Çift {pname}: (τ={v['tau_lo']}, T={v['T_lo']}) − "
              f"(τ={v['tau_hi']}, T={v['T_hi']})", "",
              "| tohum | ECE küçük-τ | ECE büyük-τ | dECE |", "|---|---|---|---|"]
        for s in SEEDS:
            ps = v["per_seed"][str(s)]
            L.append(f"| {s} | {ps['lo']['ece']:.4f} | {ps['hi']['ece']:.4f} | "
                     f"{ps['d_ece']:+.4f} |")
        L += ["",
              f"ort dECE **{v['mean']:+.4f} ± {v['sd']:.4f}** · işaretler "
              f"{'3/3 aynı' if v['same_sign_3of3'] else '3/3 aynı DEĞİL'} · "
              f"|ort|/2×bar = {abs(v['mean']) / TWO_BAR:.2f}×", "",
              f"**{v['status']}**", ""]
    L += ["## Genel", "", overall, ""]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"status": "EARLY_READING", "queue_state": "~10/42", "checkpoint": "swa",
         "sd_convention": SD_CONVENTION, "bar": DECLARED_BAR, "two_bar": TWO_BAR,
         "bar_source_sd": src_sd, "pairs": pairs_out, "overall": overall},
        indent=2, ensure_ascii=False), encoding="utf-8")
    for pname, v in pairs_out.items():
        print(f"{pname}: ort {v['mean']:+.4f} ± {v['sd']:.4f}  "
              f"{'3/3' if v['same_sign_3of3'] else 'karışık'}  -> {v['status']}")
    print(f"\nGENEL: {overall}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
