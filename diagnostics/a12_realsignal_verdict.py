"""A12 hükmü: gerçek-sinyal gate hücreleri n=3'te ölçütü karşılıyor mu?

NE TEST EDİLİYOR. Özet cümlesi "beş mekanizma başarısız" diyor, ama gate'in
*gerçekleştirilebilir* sinyalle koşan beş hücresi de tek tohumluydu (n=1). P5 yalnız **oracle**
kolunu n=3'e çıkarmıştı. Bu blok beş hücreyi de iki yeni tohumla (1, 43) n=3'e çıkarıyor;
kontroller zaten n=3 olduğu için yeni kontrol koşusu yok.

DONMUŞ KURAL — koşulardan önce (PREREGISTRATIONS A12, commit b71e6ad, etiket
a12-a13-predeclared). Ölçüt YENİDEN YAZILMIYOR, G3.1'de resmîleşen hâlinden İTHAL ediliyor
(`criterion_applied.verdict`) ve eşleştirme makinesi P5'ten ithal ediliyor
(`p5_oracle_replication_verdict`): aynı kod yolu, aynı payda tanımı.

    KURULU     : n/n tohumda aynı işaret VE |ortalama fark| >= 2 x o kolun KENDİ
                 `cw=none` kontrolünün AYNI METRİKTEKİ tohum sd'si
    ÇÖZÜNMEDİ  : aksi her durumda

İKİ EKSEN AYRI AYRI: ΔECE ve Δdoğruluk. Her eksen kendi paydasını kullanır -- doğruluk farkını
ECE sd'sine bölmek birimsiz bir sayı üretirdi ama anlamsız olurdu.

BARLAR BURADA DONDURULDU, sonuçtan önce ve A12'nin dokunmadığı koşulardan ölçülerek. Kontrol
kolları (`baseline_noclassweight`, üç öğretmen, tohum 42/1/43) P5 için koşulmuştu ve A12 onlara
dokunmuyor; dolayısıyla payda A12'nin tek bir sonucu görülmeden ölçülebilirdi ve ölçüldü.
Betik bunları veriden YENİDEN ölçüp karşılaştırır; uyuşmazlık olursa DONMUŞ değer kullanılır
(ön-kayıt odur) ve fark rapora yazılır -- sessizce yeniden ölçülene geçmek, paydayı sonuca göre
seçmek olurdu.

ÇÖZÜNMEDİ NE DEMEK DEĞİL. "Etki yok" demek değil. Bar tek bir kolun tohum gürültüsünün iki
katıdır; altında kalan bir etki *ölçülemedi* demektir, *yoktur* demek değil. Beyanda da böyle
yazıldı, metinde de böyle yazılacak.

AD -> PARAMETRE KAPISI. Hiçbir hücre koşu ADINDAN çıkarılmaz: her koşunun kendi
`run_args.json`'u okunur ve referans hücreyle karşılaştırılır (P6'da tanıtılan, G0'da
tekrarlanan kural). Uyuşmazlık hükmü durdurur.

@swa BİRİNCİL; best/last yalnız hükmün checkpoint seçimine bağlı olmadığını göstermek için.

Salt-okunur, GPU yok. Çıktı -> diagnostics/a12_realsignal_gate/a12_verdict.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

import p5_oracle_replication_verdict as p5                       # noqa: E402
from criterion_applied import THRESHOLD                          # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd            # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "a12_realsignal_gate"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR = ROOT / "results" / "unified_students"

SEEDS = (42, 1, 43)
CKPTS = ("swa", "best", "last")
PRIMARY_CKPT = "swa"
BASE = "_b070_T6_224_400e_swa200"

# --- DONMUŞ BARLAR (2026-08-06 21:4x, A12'nin hiçbir koşusu bitmeden ölçüldü) ---------------
# Kaynak: her öğretmenin `baseline_noclassweight` kontrol kolu, tohum 42/1/43, @swa.
# A12 bu kollara dokunmuyor, o yüzden payda sonuçtan önce ölçülebilirdi.
DECLARED_BAR_ECE = {"stage1": 0.00211, "primary": 0.00333, "vae9182": 0.00270}
DECLARED_BAR_ACC = {"stage1": 0.0996,  "primary": 0.3943,  "vae9182": 0.2070}
# Not: stage1/primary ECE barları P5'in bağımsız donmuş barlarıyla (0.0021 / 0.0033) aynı
# çıktı -- aynı kollar, aynı sd konvansiyonu. Tutarlılık kontrolü olarak kayda geçti.

CELLS = [
    ("stage1",  "mean_logvar",   f"RAFDB_stage1_gate_noclassweight{BASE}"),
    ("stage1",  "target_logvar", f"RAFDB_stage1_gate_target_logvar{BASE}"),
    ("primary", "mean_logvar",   f"RAFDB_primary_gate_noclassweight{BASE}"),
    ("primary", "target_logvar", f"RAFDB_primary_gate_target_logvar{BASE}"),
    ("vae9182", "mean_logvar",   f"RAFDB_vae9182_gate_noclassweight{BASE}"),
]
CONTROL = {t: f"RAFDB_{t}_baseline_noclassweight{BASE}" for t in ("stage1", "primary", "vae9182")}

# Ölçülmüş sinyal kalitesi (rafdb_signal_quality_table). Beyanda tahminler bunlara dayandırıldı;
# raporda yan yana dursun ki "kalite yüksekti ama yine de geçmedi" denetlenebilir olsun.
AUROC = {("stage1", "mean_logvar"): None, ("stage1", "target_logvar"): 0.70,
         ("primary", "mean_logvar"): None, ("primary", "target_logvar"): 0.84,
         ("vae9182", "mean_logvar"): 0.46}


# --------------------------------------------------------------------------- ad->parametre

def attempts(run_name):
    d = RUNS_DIR / run_name
    return sorted([x for x in d.iterdir() if x.is_dir()], key=lambda x: x.name) if d.is_dir() else []


def run_dirs_available():
    """Koşu dizinleri erişilebilir mi? Level-1 kapısı onları bilerek engelliyor.

    AD->PARAMETRE KAPISI BİR TABLO ÜRETMEZ, bir KÖKEN DENETİMİDİR. Çıktısı "uyuşmazlık yok"
    cümlesidir, makaledeki bir sayı değil. Level-1 değişmezi "makaledeki her sayı ham koşu
    dizini olmadan türetilebilmeli" diyor; bu denetim o kapsamda değil. Denetim kapanış günü
    KOŞTU ve sonucu artefaktın `exit_check.param_problems` alanında YAYIMLANDI -- yani
    okuyucu, kontrolün yapıldığını ve ne bulduğunu koşu dizinlerine hiç bakmadan görebilir.
    Dizinler erişilemezse hüküm yine hesaplanır (sayılar denetim CSV'sinden gelir) ve
    denetimin atlandığı raporda ADIYLA yazılır -- sessizce "sorun yok" demez.
    """
    try:
        return RUNS_DIR.is_dir() and any(True for _ in RUNS_DIR.iterdir())
    except (OSError, RuntimeError):
        return False


def param_gate(run_name, ref_name, expect_seed):
    """Koşunun kendi run_args'ı referansla aynı mı (yalnız seed/name farklı olmalı)?"""
    atts = [a for a in attempts(run_name) if (a / "run_args.json").exists()]
    if not atts:
        return None, [f"{run_name}: run_args.json yok"]
    ra = json.loads((atts[-1] / "run_args.json").read_text(encoding="utf-8"))
    ref_atts = [a for a in attempts(ref_name) if (a / "run_args.json").exists()]
    if not ref_atts:
        return ra, [f"{ref_name}: referans run_args.json yok"]
    ref = json.loads((ref_atts[-1] / "run_args.json").read_text(encoding="utf-8"))

    problems = []
    if int(ra.get("seed", -1)) != expect_seed:
        problems.append(f"{run_name}: kayıtlı seed {ra.get('seed')} ≠ beklenen {expect_seed}")
    ignore = {"seed", "name"}
    for k in sorted(set(ref) | set(ra)):
        if k in ignore:
            continue
        a, b = ref.get(k, "<yok>"), ra.get(k, "<yok>")
        if a == "<yok>" or b == "<yok>":
            # Bir tarafta olmayan anahtar: referans koşudan SONRA eklenmiş bayrak. Sessiz
            # geçmiyoruz -- G0 çıkış kontrolündeki kuralın aynısı, varsayım raporlanır.
            problems.append(f"{run_name}: `{k}` yalnız bir tarafta (ref={a!r}, koşu={b!r}) "
                            f"— referans koşudan sonra eklenmiş bayrak, varsayılana düştü")
            continue
        if isinstance(a, float) or isinstance(b, float):
            try:
                if abs(float(a) - float(b)) > 1e-9:
                    problems.append(f"{run_name}: `{k}` {a!r} ≠ {b!r}")
                continue
            except (TypeError, ValueError):
                pass
        if a != b:
            problems.append(f"{run_name}: `{k}` {a!r} ≠ {b!r}")
    return ra, problems


# --------------------------------------------------------------------------- hüküm

def judge_axis(diffs, bar):
    """DONMUŞ KURAL, ithal edilmiş hâliyle. n<3 ise hüküm YOK -- 'çözünmedi' değil, 'eksik'."""
    n = len(diffs)
    if n == 0:
        return {"n": 0, "status": "eksik", "verdict": "EKSİK"}
    m = st.mean(diffs)
    sg = p5.signs(diffs)
    ratio = abs(m) / bar if bar else None
    out = {"n": n, "mean": m, "sd": sample_sd(diffs) if n > 1 else None, "signs": sg,
           "bar": bar, "two_bar": 2 * bar, "ratio": ratio,
           "same_sign": len(set(sg)) == 1, "big_enough": ratio is not None and ratio >= THRESHOLD}
    if n < 3:
        out["status"] = "eksik"
        out["verdict"] = "EKSİK"
        return out
    # İTHAL: hükmü criterion_applied veriyor, burada yeniden yazılmıyor.
    from criterion_applied import verdict as criterion_verdict
    out["status"] = "tam"
    out["verdict"] = criterion_verdict(ratio, list(sg), n).upper().replace("ESTABLISHED", "KURULU") \
        .replace("UNRESOLVED", "ÇÖZÜNMEDİ")
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    p5.SEED_INDEX = p5.build_seed_index()
    audit = p5.load_audit()

    # --- barları yeniden ölç ve donmuşla karşılaştır
    bar_check = []
    for t, ctrl in CONTROL.items():
        s = p5.arm_stats(audit, ctrl, PRIMARY_CKPT)
        bar_check.append({
            "teacher": t, "n": s["n"],
            "ece_measured": s["ece_sd"], "ece_declared": DECLARED_BAR_ECE[t],
            "ece_match": abs(s["ece_sd"] - DECLARED_BAR_ECE[t]) < 5e-5,
            "acc_measured": s["acc_sd"], "acc_declared": DECLARED_BAR_ACC[t],
            "acc_match": abs(s["acc_sd"] - DECLARED_BAR_ACC[t]) < 5e-4})

    # --- ad->parametre kapısı + çıkış kontrolü
    gate_problems, multi_attempt, partial, missing = [], [], [], []
    dirs_ok = run_dirs_available()
    for teacher, signal, treat in CELLS:
        if not dirs_ok:
            break
        for seed in (1, 43):
            rn = f"{treat}_seed{seed}"
            if not (RUNS_DIR / rn).is_dir():
                missing.append(rn)
                continue
            atts = attempts(rn)
            if len(atts) > 1:
                multi_attempt.append(f"{rn}: {len(atts)} deneme")
            for a in atts:
                if not (a / "metrics_swa.json").exists():
                    log = a / "training_log.csv"
                    ep = (sum(1 for _ in log.open(encoding="utf-8", errors="replace")) - 1
                          if log.exists() else 0)
                    partial.append(f"{rn}/{a.name}: {ep} epoch, metrics_swa.json yok — elendi")
            _, probs = param_gate(rn, treat, seed)
            gate_problems += probs

    # --- hücre hükümleri
    cells = []
    for teacher, signal, treat in CELLS:
        row = {"teacher": teacher, "signal": signal, "treat": treat,
               "control": CONTROL[teacher], "auroc": AUROC.get((teacher, signal))}
        # Kuyruk henüz koşarken bu betik çalışabilmeli (uygulayıcı sonuçtan ÖNCE yazılıyor).
        # P5'in `resolve`'u eksik tohumda bilerek hata veriyor -- isim tahminine düşmemek için.
        # O katılığı bozmuyoruz: önce üç tohumun da çözülüp çözülmediğine bakıyoruz, hepsi
        # varsa ITHAL EDILEN `p5.paired` çağrılıyor (aritmetik birebir aynı kod yolu), yoksa
        # hücre EKSİK işaretlenip hiç hesap yapılmıyor. Yani "eksik" ile "çözünmedi" asla
        # birbirine karışmıyor.
        have = [s for s in SEEDS if (treat, s) in p5.SEED_INDEX]
        row["seeds_on_disk"] = have
        for ck in CKPTS:
            if len(have) < len(SEEDS):
                row[ck] = {"per_seed": {}, "ece": {"n": 0, "status": "eksik", "verdict": "EKSİK"},
                           "acc": {"n": 0, "status": "eksik", "verdict": "EKSİK"},
                           "missing_seeds": [s for s in SEEDS if s not in have]}
                continue
            d_acc, d_ece, per_seed = p5.paired(audit, treat, CONTROL[teacher], ck)
            row[ck] = {"per_seed": per_seed,
                       "ece": judge_axis(d_ece, DECLARED_BAR_ECE[teacher]),
                       "acc": judge_axis(d_acc, DECLARED_BAR_ACC[teacher])}
        cells.append(row)

    complete = all(c[PRIMARY_CKPT]["ece"]["status"] == "tam" for c in cells)
    est_harm, est_benefit = [], []
    for c in cells:
        for axis in ("ece", "acc"):
            j = c[PRIMARY_CKPT][axis]
            if j.get("verdict") == "KURULU":
                # ECE'de artı = zarar; doğrulukta artı = fayda.
                harmful = (axis == "ece" and j["mean"] > 0) or (axis == "acc" and j["mean"] < 0)
                (est_harm if harmful else est_benefit).append(f"{c['teacher']}/{c['signal']}/{axis}")

    if not complete:
        summary = "EKSİK — koşular bitmeden hüküm yazılmaz"
    elif est_benefit:
        summary = "ÖZET CÜMLESİ YANLIŞLANDI (en az bir hücre fayda yönünde ölçütü karşıladı)"
    elif est_harm:
        summary = "ÖZET CÜMLESİ AYAKTA — ve ilk kez n=3 dayanağı var"
    else:
        summary = "HİÇBİR HÜCRE ÖLÇÜTÜ KARŞILAMADI — cümle 'başarısız'dan 'n=3'te kurulamadı'ya çevrilir"

    write(cells, bar_check, gate_problems, multi_attempt, partial, missing, summary, complete,
          dirs_ok)
    print(f"A12: {sum(1 for c in cells if c[PRIMARY_CKPT]['ece']['status'] == 'tam')}/5 hücre tam")
    print(f"cikis: coklu-attempt {len(multi_attempt)} · elenen yarim {len(partial)} · "
          f"parametre uyusmazligi {len(gate_problems)} · eksik kosu {len(missing)}")
    print(f"ozet : {summary}")


def write(cells, bar_check, gate_problems, multi, partial, missing, summary, complete,
          dirs_ok=True):
    L = ["# A12 — gerçek-sinyal gate hücreleri n=3", "",
         "> **ÖN-BEYANLI.** `PREREGISTRATIONS.md` A12, commit `b71e6ad`, etiket "
         "`a12-a13-predeclared` — ölçüt, üç tahmin ve üç cümle-sonucu koşulardan önce "
         "donduruldu. Bu betik de ilk sonuç okunmadan commit'lendi.", "",
         f"**HÜKÜM: {summary}**", "",
         "## Donmuş kural", "",
         "n/n tohumda aynı işaret **VE** |ortalama eşleştirilmiş fark| ≥ 2 × o kolun **kendi** "
         "`cw=none` kontrolünün **aynı metrikteki** tohum sd'si. İki eksen (ΔECE, Δdoğruluk) "
         "ayrı ayrı, her biri kendi paydasıyla. Hüküm `criterion_applied.verdict`'ten, "
         "eşleştirme `p5_oracle_replication_verdict`'ten **ithal** — yeniden yazılmadı.", "",
         f"sd konvansiyonu: {SD_CONVENTION}", "",
         "**ÇÖZÜNMEDİ ≠ etkisiz.** Bar tek bir kolun tohum gürültüsünün iki katı; altında kalan "
         "bir etki *ölçülemedi*, *yok gösterilmedi*.", "",
         "## Paydalar — sonuçtan önce donduruldu", "",
         "| öğretmen | n | ECE sd ölçülen | donmuş | ✓ | doğruluk sd ölçülen | donmuş | ✓ |",
         "|---|---|---|---|---|---|---|---|"]
    for b in bar_check:
        L.append(f"| {b['teacher']} | {b['n']} | {b['ece_measured']:.5f} | "
                 f"{b['ece_declared']:.5f} | {'✅' if b['ece_match'] else '⚠️'} | "
                 f"{b['acc_measured']:.4f} | {b['acc_declared']:.4f} | "
                 f"{'✅' if b['acc_match'] else '⚠️'} |")
    L += ["", "Kontrol kolları A12'den etkilenmiyor (P5 için koşulmuştu), o yüzden payda "
              "A12'nin tek bir sonucu görülmeden ölçülebildi. Uyuşmazlık olursa donmuş değer "
              "kullanılır ve fark burada görünür.", ""]

    L += ["## Hücreler (@swa birincil)", "",
          "| öğretmen | sinyal | AUROC | n | ΔECE ort | işaret | oran | hüküm | "
          "Δdoğruluk ort (pp) | işaret | oran | hüküm |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in cells:
        e, a = c["swa"]["ece"], c["swa"]["acc"]
        au = f"{c['auroc']:.2f}" if c["auroc"] is not None else "—"
        def fmt(j, prec):
            if j["n"] == 0:
                return "— | — | — | EKSİK"
            return (f"{j['mean']:+.{prec}f} | `{j['signs']}` | "
                    f"{j['ratio']:.2f}× | {j['verdict']}")
        L.append(f"| {c['teacher']} | `{c['signal']}` | {au} | {e['n']} | "
                 f"{fmt(e, 4)} | {fmt(a, 2)} |")
    L += ["", "AUROC: o sinyalin o öğretmendeki ölçülmüş ayırt etme gücü "
              "(`rafdb_signal_quality_table`). `mean_logvar` için stage1/primary değerleri bu "
              "tabloda ayrıca raporlanmıştır; buraya yalnız beyanda tahmine dayanak yapılanlar "
              "yazıldı.", ""]

    L += ["## Çıkış kontrolü", "", "| kalem | sayı |", "|---|---|",
          f"| beklenen yeni koşu | 10 |",
          f"| diskte olmayan | {len(missing)} |",
          f"| birden çok denemesi olan koşu (çökme izi) | {len(multi)} |",
          f"| elenen yarım deneme (metrics_swa.json yok) | {len(partial)} |",
          f"| ad→parametre uyuşmazlığı | {len(gate_problems)} |", ""]
    for lab, items in (("Çoklu deneme", multi), ("Elenen yarım denemeler", partial),
                       ("Parametre notları", gate_problems), ("Diskte olmayan", missing)):
        if items:
            L += [f"**{lab}:**", ""] + [f"- {x}" for x in items] + [""]
    L += ["> Yarıda kalan koşu **devam ettirilmez**, temiz yeniden başlar: kesilip devam eden "
          "bir koşu optimizer durumu ve veri sırası bakımından temiz koşuyla aynı değildir ve "
          "aynı-tarif karşılaştırılabilirliğini bozar. Elenen her deneme kaç epoch'ta öldüğüyle "
          "yukarıda görünür — sessizce atılmaz.", ""]

    if complete:
        L += ["## Duyarlılık: best / last", "",
              "| öğretmen | sinyal | ckpt | ΔECE ort | işaret | oran | hüküm |",
              "|---|---|---|---|---|---|---|"]
        for c in cells:
            for ck in ("best", "last"):
                j = c[ck]["ece"]
                if j["n"] == 0:
                    continue
                L.append(f"| {c['teacher']} | `{c['signal']}` | {ck} | {j['mean']:+.4f} | "
                         f"`{j['signs']}` | {j['ratio']:.2f}× | {j['verdict']} |")
        L += ["", "@best 3068 görüntüde argmax val-acc ile seçilir, yani seçim iyimserliği "
                  "taşır; birincil hüküm @swa'dadır.", ""]

    L += ["---", "", "Üretici: `diagnostics/a12_realsignal_verdict.py` · veri: "
          "`diagnostics/selection_audit/selection_audit_unfrozen.csv` · kuyruk: "
          "`rafdb_a12_realsignal_gate_queue.ps1` (üretilmiş, elle yazılmamış — üretim raporu "
          "`diagnostics/replicate_queue_build.md`)", ""]

    (OUT_DIR / "a12_verdict.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "a12_verdict.json").write_text(json.dumps({
        "preregistered": True, "block": "A12", "commit": "b71e6ad",
        "tag": "a12-a13-predeclared", "summary": summary, "complete": complete,
        "rule": "n/n same sign AND |mean paired diff| >= 2 x own cw=none control seed sd "
                "(same metric); imported from criterion_applied.verdict",
        "sd_convention": SD_CONVENTION, "seeds": list(SEEDS),
        "declared_bar_ece": DECLARED_BAR_ECE, "declared_bar_acc": DECLARED_BAR_ACC,
        "bar_check": bar_check, "cells": cells,
        "exit_check": {"expected_new_runs": 10, "missing": missing, "multi_attempt": multi,
                       "partial_excluded": partial, "param_problems": gate_problems,
                       "param_gate_ran": dirs_ok,
                       "param_gate_note": ("koşu dizinleri erişilebilir, kapı koştu" if dirs_ok
                                           else "koşu dizinleri erişilemez -- ad→parametre "
                                                "kapısı ATLANDI; kapanış günündeki sonucu bu "
                                                "dosyanın önceki sürümünde kayıtlıdır")},
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
