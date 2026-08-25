"""R0-1: FERPlus öğrenci-tarafı sıcaklık ölçekleme (TS) karşılaştırma kolu — eğitimsiz.

İTİRAZ (panel): "dağıtım varsayılanı, öğrenciyi post-hoc ölçeklemek; bu kol yok." Haklı —
T=1 öğrencisini alıp kendi logitlerine TS uygulamak sıfır eğitim maliyetli bir alternatif ve
makale bunu karşılaştırmadan 'öğretmen tarafında kalibre et' diyemez.

SIZINTISIZ PROTOKOL (çapraz-fit). TS sıcaklığı raporlama kümesinde FİT EDİLEMEZ — aynı 3153
görüntüde hem fit hem ölçüm, seçim iyimserliğinin (T8) birebir tekrarı olurdu. Bölme kuralı:
  - raporlama kümesindeki her görüntünün DOSYA ADI sha256'lanır, hex'e göre sıralanır,
    ilk yarı A / ikinci yarı B (deterministik, yeniden üretilebilir, etiketten bağımsız);
  - T_s yarı A'da fit edilir (NLL küçültme — Guo et al. 2017'nin standart TS'i), yarı B'de
    ölçülür; sonra yönler değiştirilir; birleşik rapor = her örnek tam bir kez, karşı yarıda
    fit edilmiş T ile ölçülmüş hâlde.
  - Fit edilen T_s değerleri yön yön raporlanır (kural gereği).

NEYİN KARŞILAŞTIRILDIĞI (@swa, tohum başına):
  ham T=1 öğrencisi  ·  TS'li T=1 öğrencisi  ·  bizim T*=0.5063 kolu (öğretmen tarafı)
İki eksende: hard-label ECE ve insan-JSD (10 oylayıcı dağılımına karşı). JSD kritik: iddiamız
"öğrenci-TS güven vektörünü ölçekler ama TEMSİLE dokunamaz" — TS'li öğrencinin JSD'si T*
kolununkine ulaşıyor mu, rapor hangi yöne düşerse düşsün yazılır.

Görüntü kümesi `ferplus_student_jsd.py` ile AYNI (oy toplamı > 0 filtresi dahil), böylece
buradaki ham-kol sayıları o artefaktla bire bir karşılaştırılabilir. Logitler koşu dizinine
önbelleklenir; ikinci çalıştırma dosya okumadan ibaret.

CPU'da koşar (P6 kuyruğu GPU'da). Eğitim yok.
Usage:  python diagnostics/student_ts_baseline.py [--force]
Çıktı -> diagnostics/paper_tables/student_ts_baseline.{md,json}
"""
import argparse
import hashlib
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from ferplus_human_vote_jsd import entropy, jsd  # noqa: E402
from ferplus_selection_audit import VARIANTS, load_student  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402

STUDENTS = ROOT / "results" / "unified_students"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
CK = "swa"
SEEDS = (42, 1, 43)
ARM_RAW = "FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed{s}"
ARM_TSTAR = "FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed{s}"


def build_val_with_names():
    """ferplus_student_jsd.build_val'ın isimleri de döndüren kopyası.

    Oradaki fonksiyon (images, labels, p_human) döndürüyor; çapraz-fit'in bölme kuralı dosya
    ADINA ihtiyaç duyduğu için burada keep-filtreden geçen isimler de dışarı veriliyor. Filtre
    ve sıralama bire bir aynı — sayılar o artefaktla karşılaştırılabilir kalsın diye.
    """
    import pandas as pd
    from types import SimpleNamespace
    from dataset_utils.builder import build_dataloader
    from train_affectnetplus_kd import build_data_args
    from utils.configs import load_yaml
    from ferplus_human_vote_jsd import EMOTIONS

    rd = latest(ARM_RAW.format(s=42))
    run_args = json.loads((rd / "run_args.json").read_text())
    a = SimpleNamespace(**run_args)
    a.device = torch.device("cpu")
    a.workers = 0
    a.cache_img = False
    cfg_path = Path(a.teacher_config)
    data_args = build_data_args(cfg_path if cfg_path.is_absolute() else ROOT / cfg_path, a)
    data_args.train_root = None
    data_args.train_shuffle = False
    _tr, val_loader = build_dataloader(data_args)
    ds = val_loader.dataset

    imgs, labs, idxs = [], [], []
    for batch in val_loader:
        index, img, label, _label_em, _path = batch
        imgs.append(img)
        labs.append(label)
        idxs.append(index)
    images = torch.cat(imgs)
    labels = torch.cat(labs)
    indices = torch.cat(idxs).numpy()
    names = [Path(ds.data_infos[i]["path"]).name for i in indices]

    cfg = argparse.Namespace()
    load_yaml(cfg, str(ROOT / a.teacher_config))
    df = pd.read_csv(ROOT / cfg.metadata)
    df = df[df["fold"].isin(cfg.val_folds)].reset_index(drop=True)
    by_name = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows = [by_name[n] for n in names]
    votes = torch.tensor(df.loc[rows, EMOTIONS].to_numpy(dtype=np.float64), dtype=torch.float64)
    vsum = votes.sum(dim=1)
    keep = (vsum > 0)
    p_human = (votes[keep] / vsum[keep].unsqueeze(1)).float()
    kept_names = [n for n, k in zip(names, keep.tolist()) if k]
    return images[keep], labels[keep], p_human, kept_names


def val_from_published():
    """(labels, p_human, names) — koşu dizinine DOKUNMADAN; build_val_with_names'in eşleniği.

    NEDEN VAR (8 Ağu 2026). `build_val_with_names()` bir koşu dizininin `run_args.json`'unu
    okuyor (yükleyiciyi kurmak için) ve görüntüleri yüklüyor. İkisi de yalnız FORWARD için
    gerekli. Logitler yayımlanmış önbellekten geldiğinde forward yoktur, dolayısıyla ne
    görüntü ne koşu dizini gerekir. `r3w1_joint_optimum.py` bunu kullanır ve böylece Level-1
    ihlali olmaktan çıkar.

    KOPYALAMA YOK. İsim+etiket `tstar_stability.ferplus_kept()`, oy dağılımı
    `jsd_sensitivity.load_ferplus()`'tan İTHAL. İkisi de aynı iki dosyayı
    (`ferplus_jsd/ferplus_val_logits.pt` -- `paths` alanı val yükleyicinin sırasını taşır --
    ve `configs/FERPlus_majority_metadata.csv`) aynı oy>0 filtresiyle okur. Etiket
    vektörleri burada AYRICA karşılaştırılır: ayrışırlarsa iki modülün filtresi ayrışmış
    demektir ve betik durur.
    """
    from jsd_sensitivity import load_ferplus
    from tstar_stability import ferplus_kept
    _tlogits, labels, names = ferplus_kept()
    _tlogits2, labels2, p_human, _sums = load_ferplus()
    if not torch.equal(labels, labels2):
        raise RuntimeError(
            "val_from_published: tstar_stability.ferplus_kept() ile "
            "jsd_sensitivity.load_ferplus() farklı etiket vektörü verdi — iki modülün oy>0 "
            "filtresi ya da satır sırası ayrışmış. Sayı üretilmez.")
    if len(names) != labels.shape[0] or p_human.shape[0] != labels.shape[0]:
        raise RuntimeError(f"val_from_published: n uyuşmuyor — isim {len(names)}, "
                           f"etiket {labels.shape[0]}, p_human {p_human.shape[0]}")
    return labels, p_human, names


def published_logits(run_name):
    """@swa öğrenci logitleri, YAYIMLANMIŞ bayt kopyasından (koşu dizini okumaz).

    `cached_logits()`in koşu-dizini-siz eşleniği. İkisinin aynı sayıyı verdiği ölçüldü:
    `student_logits_swa.pt` ile `logits_swa.npz` 12 FERPlus koşusunda bit düzeyinde aynı
    (max |fark| = 0.0), yani bu geçiş hiçbir yayımlanmış sayıyı oynatmaz.
    """
    from publish_student_logits import published_npz
    z = np.load(published_npz(run_name, CK), allow_pickle=False)
    return torch.from_numpy(z["logits"]).float()


def latest(run_name):
    d = STUDENTS / run_name
    subs = sorted([x for x in d.iterdir() if x.is_dir()])
    if not subs:
        raise RuntimeError(f"koşu yok: {run_name}")
    return subs[-1]


def cached_logits(rd, images, force):
    """@swa logitleri koşu dizinine önbellekle — forward CPU'da bir kez."""
    p = rd / f"student_logits_{CK}.pt"
    if p.exists() and not force:
        return torch.load(p, map_location="cpu", weights_only=True)
    ra = json.loads((rd / "run_args.json").read_text())
    student, _ep = load_student(rd, VARIANTS[CK][0], ra, torch.device("cpu"))
    chunks = []
    with torch.no_grad():
        for i in range(0, images.shape[0], 64):
            from kd_common import extract_logits
            chunks.append(extract_logits(student(images[i:i + 64])).float())
    logits = torch.cat(chunks)
    torch.save(logits, p)
    del student
    return logits


def sha_split(names):
    """Deterministik SHA-sıralı ikiye bölme. Etikete, sıraya, içeriğe bakmaz — yalnız ada."""
    order = sorted(range(len(names)),
                   key=lambda i: hashlib.sha256(names[i].encode("utf-8")).hexdigest())
    half = len(order) // 2
    a = torch.zeros(len(names), dtype=torch.bool)
    a[torch.tensor(order[:half])] = True
    return a, ~a


def fit_ts(logits, labels):
    """Standart TS: tek skaler T, NLL küçültme (Guo et al. 2017). log-uzayda arama."""
    def nll(log_t):
        return float(F.cross_entropy(logits / float(np.exp(log_t)), labels.long()))
    r = minimize_scalar(nll, bounds=(np.log(0.05), np.log(10.0)), method="bounded")
    return float(np.exp(r.x))


def measure(logits, labels, p_human, T=1.0):
    probs = F.softmax(logits / T, dim=1)
    return {"ece": confidence_ece(logits, labels, T),
            "jsd": float(jsd(p_human, probs).mean()),
            "entropy": float(entropy(probs).mean())}


def main():
    # cp1252 konsolda Türkçe karakter `UnicodeEncodeError` atıyordu ve betik SAYIYI ÜRETTİKTEN
    # DEĞİL, ilk satırı basarken düşüyordu. Kapıda "başka hata" olarak görünüyordu; deponun
    # geri kalanında zaten standart olan blok buraya da eklendi. (`order_stat_trend.py` ve
    # `tstar_stability.py` hâlâ bu durumda -- ayrı kalem, işaretli.)
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="logitleri koşu dizinlerinden YENİDEN üret (Level 3: veri kümesi + "
                         "checkpoint gerekir). Varsayılan yol yayımlanmış önbelleği okur.")
    # `parse_known_args` -- ŞART, gerekçesi `abs_path_gate.py`'dekiyle aynı: Level-1 kapısı
    # üreticileri `runpy` ile çağırıp betiğin yolunu argv'de bırakıyor; `parse_args` bunu
    # tanımadığı argüman sayıp SystemExit atıyor ve kapı "başka hata" yazıyor -- yani LEVEL-1
    # SORUSU HİÇ SORULMUYOR. Bu betikte tam bu oldu: 8 Ağu'da "başka hata" görünüyordu ve
    # arkasında GERÇEK bir ihlal duruyordu (aşağıdaki blok). Harness arızası ihlali sakladı.
    args, _unknown = ap.parse_known_args()

    # LEVEL-1 (9 Ağu). Varsayılan yol koşu dizinine DOKUNMAZ: logitler yayımlanmış bayt
    # kopyalarından, raporlama kümesi (etiket / oy dağılımı / dosya adı) yayımlanmış iki
    # artefakttan gelir. `--force` eski yolu korur -- önbelleği sıfırdan kurmak tanım gereği
    # Level 3'tür (görüntüler + checkpoint gerekir) ve açık bir opt-in'dir.
    if args.force:
        images, labels, p_human, names = build_val_with_names()
    else:
        images = None
        labels, p_human, names = val_from_published()
    n = labels.shape[0]
    mask_a, mask_b = sha_split(names)
    print(f"FERPlus raporlama kümesi n={n} (oy>0 filtresi ferplus_student_jsd ile aynı)")
    print(f"SHA-sıralı bölme: A={int(mask_a.sum())} / B={int(mask_b.sum())}")
    print(f"kaynak: {'koşu dizinleri (--force)' if args.force else 'yayımlanmış önbellek'}\n")

    per_seed, rows_md = {}, []
    for s in SEEDS:
        if args.force:
            lg_raw = cached_logits(latest(ARM_RAW.format(s=s)), images, True)
            lg_star = cached_logits(latest(ARM_TSTAR.format(s=s)), images, True)
        else:
            lg_raw = published_logits(ARM_RAW.format(s=s))
            lg_star = published_logits(ARM_TSTAR.format(s=s))

        raw = measure(lg_raw, labels, p_human)
        star = measure(lg_star, labels, p_human)

        # çapraz-fit: A'da fit → B'de ölç; B'de fit → A'da ölç; birleşik = iki ölçüm yarısının
        # örnek-ağırlıklı birleşimi (her örnek tam bir kez ölçülür)
        t_ab = fit_ts(lg_raw[mask_a], labels[mask_a])
        t_ba = fit_ts(lg_raw[mask_b], labels[mask_b])
        m_b = measure(lg_raw[mask_b], labels[mask_b], p_human[mask_b], T=t_ab)
        m_a = measure(lg_raw[mask_a], labels[mask_a], p_human[mask_a], T=t_ba)
        na, nb = int(mask_a.sum()), int(mask_b.sum())
        ts = {k: (m_a[k] * na + m_b[k] * nb) / n for k in ("ece", "jsd", "entropy")}

        per_seed[s] = {"raw": raw, "student_ts": ts, "tstar_arm": star,
                       "T_s_fitA_evalB": t_ab, "T_s_fitB_evalA": t_ba}
        rows_md.append(f"| {s} | {raw['ece']:.4f} | {ts['ece']:.4f} | {star['ece']:.4f} | "
                       f"{raw['jsd']:.4f} | {ts['jsd']:.4f} | {star['jsd']:.4f} | "
                       f"{t_ab:.3f} / {t_ba:.3f} |")
        print(f"seed{s}: raw ece {raw['ece']:.4f} jsd {raw['jsd']:.4f} | "
              f"TS ece {ts['ece']:.4f} jsd {ts['jsd']:.4f} (T_s {t_ab:.3f}/{t_ba:.3f}) | "
              f"T* arm ece {star['ece']:.4f} jsd {star['jsd']:.4f}")

    def agg(key, met):
        vals = [per_seed[s][key][met] for s in SEEDS]
        return st.mean(vals), sample_sd(vals)

    L = ["# R0-1 — FERPlus student-side TS comparison arm (no training)", "",
         f"Producer: `diagnostics/student_ts_baseline.py` · @{CK} · {SD_CONVENTION} · "
         f"reporting set n={n} (same filter as `ferplus_student_jsd`)", "",
         "**Leak-free protocol.** The TS temperature was not fitted on the reporting set: image "
         "names were sha256'd and sorted by hex, first half A / second half B "
         f"(A={int(mask_a.sum())}, B={int(mask_b.sum())}); T_s was fitted on one half by NLL "
         "minimisation (Guo et al. 2017) and measured on the other, in both directions; the "
         "combined row scores every sample exactly once, with the opposite half's T. The fitted "
         "T_s values are in the table.",
         "",
         "| seed | ECE raw | ECE student-TS | ECE T\\*-arm | JSD raw | JSD student-TS | "
         "JSD T\\*-arm | T_s (A→B / B→A) |",
         "|---|---|---|---|---|---|---|---|"]
    L += rows_md
    me_r, se_r = agg("raw", "ece")
    me_t, se_t = agg("student_ts", "ece")
    me_s, se_s = agg("tstar_arm", "ece")
    mj_r, sj_r = agg("raw", "jsd")
    mj_t, sj_t = agg("student_ts", "jsd")
    mj_s, sj_s = agg("tstar_arm", "jsd")
    L += [f"| **mean ± sd** | **{me_r:.4f} ± {se_r:.4f}** | **{me_t:.4f} ± {se_t:.4f}** | "
          f"**{me_s:.4f} ± {se_s:.4f}** | **{mj_r:.4f} ± {sj_r:.4f}** | "
          f"**{mj_t:.4f} ± {sj_t:.4f}** | **{mj_s:.4f} ± {sj_s:.4f}** | — |", ""]

    ts_all = [per_seed[s][k] for s in SEEDS for k in ("T_s_fitA_evalB", "T_s_fitB_evalA")]
    # Okuma cümleleri YÖN-FARKINDALIKLI kurulur: hangi kolun düşük (iyi) olduğu ölçümden gelir,
    # şablondan değil. İlk taslak "TS, JSD'de T*-koluna ulaşamıyor" kalıbını tek yönlü yazmıştı;
    # ölçüm ters yönü verdi (TS'in JSD'si T*-kolundan İYİ çıktı) ve kalıp düzeltildi.
    ece_gap = me_t - me_s          # >0: TS, T*-kolundan kötü (ECE'de)
    ece_bar = 2 * max(se_t, se_s)
    jsd_gap = mj_t - mj_s          # <0: TS'in JSD'si T*-kolundan İYİ (düşük)
    jsd_bar = 2 * max(sj_t, sj_s)
    if abs(ece_gap) <= ece_bar:
        ece_sent = (f"On ECE, TS and the T\\*-arm do not separate beyond seed noise "
                    f"(difference {ece_gap:+.4f}, bar {ece_bar:.4f}).")
    else:
        who = "the T\\*-arm is better" if ece_gap > 0 else "student-TS is better"
        ece_sent = (f"On ECE, {who}: difference {ece_gap:+.4f}, bar {ece_bar:.4f} — TS closes "
                    f"most of the gap but does not match it." if ece_gap > 0 else
                    f"On ECE, {who}: difference {ece_gap:+.4f}, bar {ece_bar:.4f}.")
    if abs(jsd_gap) <= jsd_bar:
        jsd_sent = (f"On JSD the two arms do not separate beyond seed noise "
                    f"(difference {jsd_gap:+.4f}, bar {jsd_bar:.4f}).")
    elif jsd_gap < 0:
        jsd_sent = (f"**student-TS's JSD is BETTER than the T\\*-arm's** ({mj_t:.4f} vs "
                    f"{mj_s:.4f}): TS fixes ECE while preserving the better human alignment of "
                    f"the T=1 arm, whereas the T\\*-teacher arm paid for its ECE gain out of JSD "
                    f"(the student-side trace of the teacher-side trade-off). On this axis the "
                    f"sentence \"student-side TS cannot touch the representation\" works IN "
                    f"FAVOUR of TS, not against it — the Block-3 reframing should use that "
                    f"direction.")
    else:
        jsd_sent = (f"TS's JSD is worse than the T\\*-arm's ({mj_t:.4f} vs {mj_s:.4f}): rescaling "
                    f"confidence with a single scalar does not carry the representation's human "
                    f"alignment to that of the T\\*-arm.")
    L += ["## Reading", "",
          f"- **On the ECE axis, student-side TS works**: raw {me_r:.4f} → TS {me_t:.4f} "
          f"(T\\*-arm {me_s:.4f}). {ece_sent} The fitted T_s ∈ [{min(ts_all):.3f}, "
          f"{max(ts_all):.3f}] — all < 1: an under-confident student is being sharpened, i.e. the "
          f"teacher's pathology has passed to the student and TS corrects in the same direction.",
          f"- **JSD axis**: raw {mj_r:.4f} → TS {mj_t:.4f}; T\\*-arm {mj_s:.4f}. {jsd_sent}",
          "",
          "> The numbers are reported whichever way they fell; the sentences were written "
          "direction-aware and selected by the measurement.", ""]

    payload = {"sd_convention": SD_CONVENTION, "checkpoint": CK, "n_val": n,
               "split": {"rule": "sha256(filename) hex sort, first half A",
                         "n_A": int(mask_a.sum()), "n_B": int(mask_b.sum())},
               "fit": "single-scalar TS, NLL minimisation (Guo et al. 2017), bounded log-search",
               "per_seed": {str(k): v for k, v in per_seed.items()},
               "aggregate": {"ece": {"raw": [me_r, se_r], "student_ts": [me_t, se_t],
                                     "tstar_arm": [me_s, se_s]},
                             "jsd": {"raw": [mj_r, sj_r], "student_ts": [mj_t, sj_t],
                                     "tstar_arm": [mj_s, sj_s]}}}
    (OUT_DIR / "student_ts_baseline.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "student_ts_baseline.json").write_text(json.dumps(payload, indent=2),
                                                     encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'student_ts_baseline.md'}")


if __name__ == "__main__":
    main()
