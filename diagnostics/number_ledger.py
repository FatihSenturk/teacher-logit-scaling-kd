"""N13 — SAYI PROVENANS DEFTERI: makaledeki her tablo hucresi hangi alandan geliyor?

NEDEN. 17 Agu 2026'da uc ayri taraf sayisal hata yapti ve ucu de TESADUFEN yakalandi: biri PDF'e
baktigi icin, biri defterle karsilastirdigi icin, biri kendi hukmunu gozden gecirdigi icin.
Tesaduf bir savunma degil. Onceki tur bir prototipi olctu: "bu sayi havuzda var mi?" sorusu
makaledeki sayilarin %98.9'unu esliyor ama bayat degerlerin dordunden ucunu KACIRIYOR -- cunku
bayat bir deger de bir yerde vardir, eskiden dogruydu. Ve r=0.724 vakasinda sayi gercekti, dogru
artefaktaydi, yalniz YANLIS KOLA baglanmisti. Varlik kontrolu bunu asla yakalayamaz.

BU YUZDEN DEFTER DEGERI DEGIL, DEGER<->ALAN BAGINI kaydeder. Her basili sayi icin: hangi
artefakt, o artefaktin hangi alani, hangi yuvarlama, makalede nerede. Bag kurulmaya zorlandigi
anda yanlis bag GORUNUR hale gelir.

BU BETIK NE URETIR
  paper_tables/number_ledger.{md,json}      -- alan baglama (tablo hucreleri + manset)
  paper_tables/derived_registry.{md,json}   -- oran/fark gibi TURETILMIS nicelikler, pay/payda
Denetci ayri betiktir: `diagnostics/check_numbers.py` (ayni tarayiciyi ITHAL eder).

KAPSAM (beyan, bu tur)
  girer : paper/tables/*.tex butun hucreleri · ozetteki manset sayilar · supplementary S8-S11
  girmez: sections/*.tex duzyazisi (revizyon penceresi) · supplementary S1-S3 (bugunku headroom
          turunun sonucu oraya henuz islenmedi; degisecek bir hucreyi baglamak curuk)
  olcum degil (baglanmaz, sinifiyla beyan edilir): hiperparametreler (tau, alpha, lr, epoch,
          tohum kimlikleri), veri kumesi/populasyon sayimlari, sayfa/yil/DOI, mimari boyutlari,
          sutun basliklarindaki sayilar.

KAGIT AGACI. `--paper-root` ile verilir; kodda MUTLAK YOL YOK. Yol verilmezse (Level-1 kapisi
ureticileri argumansiz cagirir) betik MEVCUT defteri KORUR ve 0 doner -- artefakti bozmaz.

Kullanim: python diagnostics/number_ledger.py --paper-root "<...>/paper"
"""
import argparse
import json
import math
import os
import subprocess
import sys
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from paper_number_scan import scan_paper  # noqa: E402

D = ROOT / "diagnostics"
OUT_DIR = D / "paper_tables"

# --- artefakt kisaltmalari (yol depo kokune gore, `diagnostics/` altinda)
A_TDO = "p1_dose_response/two_dataset_overlay.json"
A_DRS = "paper_tables/dose_response_per_seed.json"
A_RT = "paper_tables/RESULTS_TABLES.json"
A_P4 = "p4_teacher_selection/p4_teacher_selection.json"
A_CSM = "paper_tables/control_sd_mde.json"
A_INF = "paper_tables/inferential_tests.json"
A_EFF = "paper_tables/efficiency_retention.json"
A_LAT = "p5_efficiency/latency_benchmark.json"
A_SG = "selection_audit/selection_gain.json"
A_OST = "paper_tables/order_stat_trend.json"
A_FSJ = "ferplus_jsd/ferplus_student_jsd.json"
A_FJ = "ferplus_jsd/ferplus_jsd.json"
A_R3W = "paper_tables/r3w1_joint_optimum.json"
A_JCA = "paper_tables/jsd_collapse_audit.json"
A_ASY = "paper_tables/asymmetry_estimand.json"
A_HR = "paper_tables/headroom_review.json"
A_CRIT = "paper_tables/criterion_applied.json"
# --- N14 (17 Agu 2026): kayitsiz 28 kalemin kapatilmasi icin acilan artefaktlar
A_TEG = "teacher_ece_grid/teacher_ece_grid.json"
A_NU = "paper_tables/noise_units.json"
A_TSS = "paper_tables/tstar_sensitivity.json"
A_TSP = "paper_tables/tstar_provenance.json"
A_SAI = "paper_tables/selection_audit_inference.json"
# --- N16 (18 Agu 2026): supplementary S1-S3 kapsam genislemesi
A_ROB = "paper_tables/robustness_metrics.json"
A_BOOT = "paper_tables/bootstrap_cis.json"
A_HGA = "paper_tables/headroom_grid_audit.json"
A_JSD = "paper_tables/jsd_sensitivity.json"
A_ABS = "paper_tables/ferplus_abstention_entropy.json"
A_SPL = "paper_tables/split_identity.json"
A_STS = "paper_tables/student_ts_baseline.json"
# --- N19b (20 Agu 2026): son 23 kayitsiz sayinin kapatilmasi icin acilan/kullanilan artefaktlar
A_RMC = "paper_tables/run_manifest_census.json"
A_REL = "reliability/reliability_diagram.json"
A_PCC = "reliability/perclass_calibration.json"
A_PL = "paper_tables/prereg_lead_audit.json"
A_A13 = "a13_scratch_dose/a13_verdict.json"
# Round-6 (27-28 Agu 2026): ogrenci tarafi olcekleme, iki veri kumesi. Ikisi de YAYIMLANMIS
# artefaktlardan TURETME -- yeni degerlendirme yok, kosu dizini yok.
A_FSE = "paper_tables/ferplus_scaled_ece_axis.json"
A_RTD = "paper_tables/rafdb_student_ts_dose.json"

BINDINGS = []      # alan baglari
DERIVED = []       # turetilmis nicelikler
EXEMPT = []        # olcum-degil beyanlari
PROSE = []         # duzyazida beyan edilen tek tek baglar
CROSS_CHECKS = []  # ayni niceligi hesaplayan IKINCI kaynak: teyit kaydi + ayrisma kontrolu
SIGNS = []         # isaret desenleri (`[++-]`) -- rakamsiz VERI iddialari

# BANT MUAFIYETI (23 Agu 2026 eki). `binding_source_unpublished` kurulur kurulmaz bir sorun
# doguruyor: ihraci MUMKUN OLMAYAN tek bir kaynak kalirsa (lisans, ham veri turevi, boyut)
# kapi KALICI KIRMIZIYA doner ve bir hafta icinde herkesin gormezden geldigi bir uyariya
# donusur -- kapilarin en kotu olum bicimi. Cozum susturma degil, AYRISTIRMA: gerekcesi
# YAZILMIS muafiyet ihlal saymaz, gerekcesizi sayar. Boylece "yayimlanamaz cunku lisans" ile
# "unutulmus" birbirinden ayrilir ve muafiyetin kendisi de denetlenir:
#   · bantta OLMAYAN + burada YAZILI  -> muaf (STATUS.md'ye adiyla ve gerekcesiyle basilir)
#   · bantta OLMAYAN + burada YOK     -> IHLAL (binding_source_unpublished)
#   · bantta OLAN     + burada YAZILI -> IHLAL (band_exempt_rotten): curumus beyan, silinmeli
# 23 Agu 2026 itibariyle BOS: defterin isaret ettigi 49 kaynagin 49'u bantta.
BAND_EXEMPT = {
    # "artefakt/yolu.json": "neden ihrac edilemez -- ve bunun yerine ne yayimlandi",
}


def b(unit, sec, row, idx, artifact, path, rounding, ident=None):
    BINDINGS.append({"id": ident or f"{unit}.s{sec}.{row}.{idx}", "unit": unit, "section": sec,
                     "row": row, "idx": idx, "artifact": artifact, "path": path,
                     "rounding": rounding})


# Bazi manset sayilar duzyazida HARFLE yaziliyor ("roughly forty times the noise"). Capa
# kontrolu rakami arar; harfle yazilan degerler icin karsiligi BEYAN edilir.
SPELLED = {"40": "forty", "76": "seventy-six", "37": "thirty-seven", "27": "twenty-seven"}


def dv(ident, printed, kind, operands, rounding, where_unit, sec, row, idx, note="",
       where=None):
    DERIVED.append({"id": ident, "printed": printed, "formula": kind, "operands": operands,
                    "rounding": rounding, "unit": where_unit, "section": sec, "row": row,
                    "idx": idx, "note": note, "where_literal": where})


def pv(ident, artifact, path, rounding, where, note=""):
    """DUZYAZIDA duran bir sayinin alan bagi. Kapsam disi olan duzyazi TARANMAZ, ama tek tek
    beyan edilen cumleler baglanabilir: denetci o SATIRI okur ve alanin yuvarlanmis degerinin
    orada gectigini dogrular. r=0.724 vakasi tam bu yolla yakalanir -- sayi dogru, artefakt
    dogru, bag yanlissa yuvarlanmis deger o satirda GECMEZ."""
    PROSE.append({"id": ident, "artifact": artifact, "path": path, "rounding": rounding,
                  "where": where, "note": note})


def sg(unit, sec, row, idx, artifact, paths, why, ident=None):
    """ISARET DESENI BAGI (22 Agu 2026, defter final3).

    `tab_mechanisms` her ECE hucresinin yaninda tohum basina farkin isaret dizisini basiyor
    (`[++-]`) ve §5 duzyazisi bunlara adiyla atif veriyor. Bunlar SAYI JETONU DEGIL -- rakam
    tasimadiklari icin sayi ayiklayici onlari HIC gormez -- ama artefaktin `d_ece_signs` /
    `d_acc_signs` alanlarinin birebir kopyasi, yani veri iddiasi. Bu tura kadar hicbir kapi
    onlara bakmiyordu: bir deseni bozan degisiklik (`[+++]` -> `[++-]`) tum kapilardan sessizce
    gecerdi. Olculdu (ligatur duzeltmesi tam bu desenlere dokundu) ve acik kapatildi.

    `paths` bir liste olabilir: duzyazi "sign pattern `-++` on both" derken TEK jeton IKI
    hucre hakkinda konusur; ikisi de esit olmak zorunda, yoksa cumle yanlistir.
    """
    SIGNS.append({"unit": unit, "section": sec, "row": row, "idx": idx, "artifact": artifact,
                  "paths": [paths] if isinstance(paths, str) else list(paths),
                  "why": why, "id": ident or f"sign.{unit}.{row[:22]}.{idx}"})


def ex(unit, sec, row, idx, klass, why, opt=False):
    """`opt=True`: bu muafiyet bazi bloklarda hic jetona denk gelmeyebilir (orn. adinda
    basamak olmayan FERPlus basligi). Kalan muafiyetler eslesmezse SORUN olarak raporlanir --
    yoksa curumus bir muafiyet sessizce durur."""
    EXEMPT.append({"unit": unit, "section": sec, "row": row, "idx": idx,
                   "class": klass, "why": why, "optional": opt})


# =============================================================================
# 1 · tab_dose_response — uc blok, `two_dataset_overlay` tek kaynak
# =============================================================================
DOSE = [(0, "rafdb_stage1", ["0.85", "1.00", "1.34", "1.70", "2.20"]),
        (1, "rafdb_vae9182", ["0.85", "1.00", "1.34", "1.70", "2.20"]),
        (2, "ferplus", ["0.26", "0.51", "0.74", "1.00"])]
DOSE_COLS = [("teacher_ece", "teacher_ece", "4dp"), ("signed_gap", "signed_gap", "4dp"),
             ("ece_swa_mean", "by_ckpt.swa.ece_mean", "4dp"),
             ("ece_swa_sd", "by_ckpt.swa.ece_sd", "4dp"),
             ("ece_last_mean", "by_ckpt.last.ece_mean", "4dp"),
             ("ece_last_sd", "by_ckpt.last.ece_sd", "4dp"),
             ("acc_swa_mean", "by_ckpt.swa.acc_mean", "2dp"),
             ("acc_swa_sd", "by_ckpt.swa.acc_sd", "2dp")]
for sec, arm, rows in DOSE:
    for i, row in enumerate(rows):
        for k, (name, tail, rnd) in enumerate(DOSE_COLS):
            b("tab_dose_response", sec, row, k, A_TDO,
              f"arms.{arm}.points[{i}].{tail}", rnd,
              ident=f"tab_dose_response.{arm}.T{row}.{name}")
# blok basliklari: ogretmenin T=1'deki ECE'si + basilan T
for sec, arm, i_T1 in ((0, "rafdb_stage1", 1), (1, "rafdb_vae9182", 1)):
    b("tab_dose_response", sec, "§header", 1, A_TDO,
      f"arms.{arm}.points[{i_T1}].teacher_ece", "4dp",
      ident=f"tab_dose_response.{arm}.header.teacher_ece_T1")
    ex("tab_dose_response", sec, "§header", 0, "teacher_name_digits",
       "blok basliginda gecen ogretmen adinin icindeki basamak (Stage1 / VAE9182)", opt=True)
# Baslikta 'T*' diye basilan sayi 17 Agu'a kadar IKI FARKLI niceligi tasiyordu: Stage1'de
# DAGITILAN sicaklik (1.3406), VAE9182'de FIT (0.98294). Defter ikisini ayri alanlara baglayinca
# cakisma gorunur oldu ve makale tarafinda duzeltildi -- artik UC baslik da FIT degeri basiyor
# (T^*_NLL) ve dagitilan kol alt yazida ayrica adlandiriliyor. Bag da o yuzden tek alan ailesine
# tasindi: ucu de `tstar_sensitivity.results.<ogretmen>.published_full_nll`, yani alt yazidaki
# 1.3494 ile basliktaki 1.35 KANITLANABILIR bicimde ayni sayi.
# DIKKAT — BEYAN OLAN ALANA BAGLANMAZ. `tstar_sensitivity.results.*.published_full_nll` ve
# `.deployed_T` ELLE YAZILMIS sabit sozluklerdir (`tstar_stability.PUBLISHED`,
# `tstar_sensitivity.DEPLOYED`): "kampanyada su deger yayimlandi/dagitildi" BEYANI, olcum degil.
# Basili sayiyi oraya baglamak dairesel olurdu -- alan, basili sayinin elle yazilmis kopyasi.
# Bag bu yuzden OLCULEN fite kuruluyor: `T_star_nll`, uretici tarafindan hesaplanan tam-fold NLL
# optimumu (n=3068/3153).
for sec, t in ((0, "stage1"), (1, "vae9182"), (2, "ferplus")):
    b("tab_dose_response", sec, "§header", 2 if sec < 2 else 1, A_TSS,
      f"results.{t}.T_star_nll", "2dp",
      ident=f"tab_dose_response.{t}.header.T_star_fit")
b("tab_dose_response", 2, "§header", 0, A_TDO, "arms.ferplus.points[3].teacher_ece", "4dp",
  ident="tab_dose_response.ferplus.header.teacher_ece_T1")
# Alt yazi (17 Agu'da eklendi): dagitilan kol ile tam-fold fit yan yana adlandiriliyor. Ikisi de
# AYNI artefaktta duruyor -- cumlenin karsilastirdigi iki sayi tek kaynaktan geliyor.
DOSE_CAP = "under-confident so their corrections act in"
# 1.3406 = YARI-FOLD fit (dagitilan kolun kokeni), OLCULEN deger: `tstar_provenance` bu ayrimin
# artefakti ve iki fiti de kendisi hesapliyor. 1.3494 = tam-fold fit.
b("tab_dose_response", -1, DOSE_CAP, 1, A_TSP, "half_fold_fits.stage1", "4dp",
  ident="tab_dose_response.caption.stage1_half_fold_fit")
b("tab_dose_response", -1, DOSE_CAP, 2, A_TSS, "results.stage1.T_star_nll", "4dp",
  ident="tab_dose_response.caption.stage1_full_fold_fit")
b("tab_dose_response", -1, DOSE_CAP, 3, A_TSS, "results.vae9182.T_star_nll", "2dp",
  ident="tab_dose_response.caption.vae9182_fit")
ex("tab_dose_response", -1, DOSE_CAP, 0, "teacher_name_digits",
   "alt yazidaki 'Stage1' adinin icindeki basamak")
ex("tab_dose_response", -1, DOSE_CAP, 4, "hyperparameter",
   "kontrolun fit'ine en yakin EGITILMIS kol: T=1 -- tasarim degeri, olcum degil")

# =============================================================================
# 2 · app_seeds (S10) — tohum basina ogrenci ECE'si
# =============================================================================
SEEDS_ORDER = ["1", "42", "43"]
S10 = [(0, "rafdb_stage1", ["0.85", "1.00", "1.3406", "1.70", "2.20"]),
       (1, "rafdb_vae9182", ["0.85", "1.00", "1.3406", "1.70", "2.20"]),
       (2, "ferplus", ["0.26", "0.5063", "0.74", "1.00"])]
for sec, arm, rows in S10:
    for i, row in enumerate(rows):
        b("app_seeds", sec, row, 0, A_DRS, f"series.{arm}.points[{i}].teacher_ece", "4dp",
          ident=f"app_seeds.{arm}.T{row}.teacher_ece")
        b("app_seeds", sec, row, 1, A_DRS, f"series.{arm}.points[{i}].signed_gap", "4dp",
          ident=f"app_seeds.{arm}.T{row}.signed_gap")
        for k, s in enumerate(SEEDS_ORDER):
            b("app_seeds", sec, row, 2 + k, A_DRS,
              f'series.{arm}.points[{i}].per_seed["{s}"].ece', "4dp",
              ident=f"app_seeds.{arm}.T{row}.seed{s}")
        b("app_seeds", sec, row, 5, A_DRS, f"series.{arm}.points[{i}].ece_mean", "4dp",
          ident=f"app_seeds.{arm}.T{row}.mean")
        b("app_seeds", sec, row, 6, A_DRS, f"series.{arm}.points[{i}].ece_sd", "4dp",
          ident=f"app_seeds.{arm}.T{row}.sd")
    ex("app_seeds", sec, "§header", None, "teacher_name_digits",
       "blok basliginda gecen ogretmen adinin icindeki basamak", opt=True)
ex("app_seeds", -1, "T", None, "column_header",
   "sutun basligindaki tohum kimlikleri (1/42/43)", opt=True)

# =============================================================================
# 3 · app_sd (S8) + app_mde (S9) — control_sd_mde tek kaynak
# =============================================================================
CW = {"eff.": "effective_number", "none": "none"}
for ck_tex, ck in (("SWA", "swa"), ("best", "best"), ("last", "last")):
    for t_tex, t in (("Stage1", "stage1"), ("Primary", "primary"), ("VAE9182", "vae9182")):
        for cw_tex, cw in CW.items():
            row = f"{ck_tex} {t_tex} {cw_tex}"
            sel = f"rows[checkpoint={ck}][teacher={t}][class_weight_mode={cw}]"
            for k, (axis, field, rnd) in enumerate(
                    [("ece", "control_level", "4dp"), ("ece", "control_sd", "4dp"),
                     ("acc", "control_level", "3dp"), ("acc", "control_sd", "3dp")]):
                b("app_sd", -1, row, k, A_CSM, f"{sel}[axis={axis}].{field}", rnd,
                  ident=f"app_sd.{ck}.{t}.{cw}.{axis}_{field}")
            for k, (axis, field, rnd, sc) in enumerate(
                    [("ece", "mde_2sd", "4dp", 1), ("ece", "mde_pct_of_level", "1dp", 1),
                     ("acc", "mde_2sd", "3dp", 1), ("acc", "mde_pct_of_level", "1dp", 1)]):
                b("app_mde", -1, row, k, A_CSM, f"{sel}[axis={axis}].{field}", rnd,
                  ident=f"app_mde.{ck}.{t}.{cw}.{axis}_{field}")
ex("app_sd", -1, "checkpoint teacher cw", None, "column_header", "sutun basligi",
   opt=True)
ex("app_mde", -1, "checkpoint teacher cw", None, "column_header",
   "sutun basligi ($2\\sigma$ icindeki 2)")
ex("app_sd", -1, "All rows are three seeds ( 1 42 43 ) sample standard", None,
   "hyperparameter", "tohum kimlikleri ve tohum sayisi")
ex("app_mde", -1, "2 of the control arm absolutely and as a fraction of", None,
   "criterion_constant", "olcutun kendisi: 2 sigma (esik tanimi, olcum degil)")

# =============================================================================
# 4 · tab_mechanisms (T5) + tab_logitstd (T5a) — RESULTS_TABLES.T5
# =============================================================================
# Hangi hucre DOLU: `---` yazan hucre jeton uretmez, dolayisiyla jeton indisleri kayar.
# "G2G + adaptive T" satirinda yalniz VAE9182 dolu. N13'te "T5'te bu bilesik hucre YOK" diye
# kayitsiz birakilmisti; DUZELTME (17 Agu): T5 gercekten 21 hucre tasiyor ama bilesimi baska --
# stage1/primary yedi mekanizma, vae9182 ise `gate:target_logvar` yerine `g2g_kl+adaptive_t`.
# Yani hucre artefaktta VARDI, eksik olan beyandi. Tek tohumlu kol (n=1, sd=0), tabloda da
# dagger ile isaretli.
MECH_ROWS = [("Adaptive temperature", "adaptive_t", ["stage1", "primary", "vae9182"]),
             ("CTKD", "ctkd", ["stage1", "primary", "vae9182"]),
             ("G2G (class-space KL)", "g2g_kl", ["stage1", "primary", "vae9182"]),
             ("Gate mean logvar", "gate:mean_logvar", ["stage1", "primary", "vae9182"]),
             ("Gate target logvar", "gate:target_logvar", ["stage1", "primary"]),
             ("Gate oracle error", "gate:oracle_error", ["stage1", "primary", "vae9182"]),
             ("Logit standardisation", "logit_std", ["stage1", "primary", "vae9182"])]
for row, mech, teachers in MECH_ROWS:
    k = 0
    for t in teachers:
        cell = f'T5_mechanisms["{t}/{mech}"].swa'
        b("tab_mechanisms", -1, row, k, A_RT, f"{cell}.d_acc_mean", "2dp",
          ident=f"tab_mechanisms.{t}.{mech}.d_acc")
        b("tab_mechanisms", -1, row, k + 1, A_RT, f"{cell}.d_ece_mean", "4dp",
          ident=f"tab_mechanisms.{t}.{mech}.d_ece")
        k += 2
b("tab_mechanisms", -1, "G2G + adaptive T ^", 0, A_RT,
  'T5_mechanisms["vae9182/g2g_kl+adaptive_t"].swa.d_acc_mean', "2dp",
  ident="tab_mechanisms.vae9182.g2g_kl+adaptive_t.d_acc")
b("tab_mechanisms", -1, "G2G + adaptive T ^", 1, A_RT,
  'T5_mechanisms["vae9182/g2g_kl+adaptive_t"].swa.d_ece_mean', "4dp",
  ident="tab_mechanisms.vae9182.g2g_kl+adaptive_t.d_ece")
# T5a (`tab_logitstd`) alt yazisinin dort gurultu-birimi orani. Tanim `noise_units.py`de:
# (|dECE|/sigma_ECE) ÷ (|dacc|/sigma_acc), her kol KENDI kontrol sd'siyle. Dordu de o
# artefaktin ALANI -- yeniden bolme yok, basili yuvarlak degerden turetme hic yok.
b("tab_mechanisms", 0, "23 in the narrowest SWA comparison", 0, A_NU,
  'nine_cell_grid["swa|primary"].ratio', "int", ident="tab_logitstd.caption.narrowest_swa")
b("tab_mechanisms", 0, "of 27 (mean 52", 0, A_NU, "summary.median", "int",
  ident="tab_logitstd.caption.median")
b("tab_mechanisms", 0, "of 27 (mean 52", 1, A_NU, "summary.mean", "int",
  ident="tab_logitstd.caption.mean")
b("tab_mechanisms", 0, "the all-checkpoint floor is 2.6", 0, A_NU, "summary.min", "1dp",
  ident="tab_logitstd.caption.floor")
for t_tex, t in (("Primary", "primary"), ("Stage1", "stage1"), ("VAE9182", "vae9182")):
    for k, ck in enumerate(("swa", "best", "last")):
        b("tab_mechanisms", 0, t_tex, k, A_RT,
          f'T5_mechanisms["{t}/logit_std"].{ck}.d_acc_mean', "2dp",
          ident=f"tab_logitstd.{t}.{ck}.d_acc")
        b("tab_mechanisms", 0, t_tex, 3 + k, A_RT,
          f'T5_mechanisms["{t}/logit_std"].{ck}.d_ece_mean', "4dp",
          ident=f"tab_logitstd.{t}.{ck}.d_ece")
# T5 dipnotu (bolum 0'in baslik satiri): alti kontrol tohum sd'si, ikisi aralik ucu olarak
# TEKRAR basiliyor. Onu da ayni alana bagliyoruz -- ayni sayinin iki kez yazilmasi da bir bag.
FOOT_SD = [(0, "stage1", "effective_number"), (1, "vae9182", "effective_number"),
           (3, "stage1", "effective_number"), (4, "primary", "effective_number"),
           (6, "vae9182", "effective_number"), (7, "stage1", "none"),
           (8, "primary", "none"), (10, "stage1", "none"), (11, "primary", "none"),
           (13, "vae9182", "none")]
for idx, t, cw in FOOT_SD:
    b("tab_mechanisms", 0, "§header", idx, A_CSM,
      f"rows[checkpoint=swa][teacher={t}][class_weight_mode={cw}][axis=ece].control_sd", "4dp",
      ident=f"tab_mechanisms.foot.{t}.{cw}.{idx}")
for idx in (2, 5, 9, 12):
    ex("tab_mechanisms", 0, "§header", idx, "teacher_name_digits",
       "dipnotta gecen ogretmen adinin icindeki basamak (Stage1 / VAE9182)")
ex("tab_mechanisms", 0, "§header", 14, "table_reference", "Supplementary Table S8 atfi")
ex("tab_mechanisms", 0, "§header", 15, "table_reference", "Supplementary Table S9 atfi")

# =============================================================================
# 5 · tab_selection — p4 recipe_step3_ranking
# =============================================================================
for i, (row, t) in enumerate((("Stage1", "stage1"), ("Primary", "primary"),
                              ("VAE9182", "vae9182"))):
    sel = f"recipe_step3_ranking.rows[teacher={t}]"
    b("tab_selection", -1, row, 0, A_P4, f"{sel}.teacher_acc", "2dp",
      ident=f"tab_selection.{t}.teacher_acc")
    b("tab_selection", -1, row, 1, A_P4, f"{sel}.teacher_ece", "4dp",
      ident=f"tab_selection.{t}.teacher_ece")
    # T* sutunu KANONIK kaynaga cekildi (17 Agu, N14 karari): `tstar_sensitivity` T*'in adanmis
    # ureticisi, p4 onu secim tarifinin yan urunu olarak tasiyor. p4'un degeri silinmiyor --
    # CROSS_CHECKS altinda TEYIT KAYDI olarak duruyor ve ayrisirsa denetci bagirir.
    b("tab_selection", -1, row, 2, A_TSS, f"results.{t}.T_star_nll", "3dp",
      ident=f"tab_selection.{t}.T_star")
    b("tab_selection", -1, row, 3, A_P4, f"{sel}.student_by_ckpt.best.acc_mean", "2dp",
      ident=f"tab_selection.{t}.student_acc_mean")
    b("tab_selection", -1, row, 4, A_P4, f"{sel}.student_by_ckpt.best.acc_sd", "2dp",
      ident=f"tab_selection.{t}.student_acc_sd")
    b("tab_selection", -1, row, 5, A_P4, f"{sel}.student_by_ckpt.best.ece_mean", "4dp",
      ident=f"tab_selection.{t}.student_ece")
b("tab_selection", -1, "( 89.60 pp each) and the cost of the accuracy rule i", 0, A_P4,
  "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.swa.acc_mean", "2dp",
  ident="tab_selection.swa_tie")
# Dipnot TEK mantiksal satir: [0] rho_s(acc,acc) [1] rho_s(-ECE,acc) [2] 0.52 pp maliyet
# [3] kazanan tam deger [4] dogruluk-kuralinin tam degeri.
SEL_FOOT = "_s(teacher acc. student acc.)"
# Dipnotun iki sira korelasyonu: uc ogretmen uzerinden. N13'te "artefakti yok" diye kayitsiz
# birakilmisti; yanlis -- `p4_teacher_selection` ikisini de HESAPLIYOR, yalniz beyan edilmemisti.
b("tab_selection", -1, SEL_FOOT, 0, A_P4,
  "recipe_step3_ranking.spearman_teacherACC_vs_studentACC", "2dp",
  ident="tab_selection.rho_teacherACC_studentACC")
b("tab_selection", -1, SEL_FOOT, 1, A_P4,
  "recipe_step3_ranking.spearman_negTeacherECE_vs_studentACC", "2dp",
  ident="tab_selection.rho_negTeacherECE_studentACC")
b("tab_selection", -1, SEL_FOOT, 3, A_P4,
  "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.acc_mean", "4dp",
  ident="tab_selection.best_winner_exact")
b("tab_selection", -1, SEL_FOOT, 4, A_P4,
  "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.acc_mean", "4dp",
  ident="tab_selection.best_acc_rule_exact")

# =============================================================================
# 6 · tab_holm — inferential_tests.results (sirali)
# =============================================================================
# Makale satirlari p_Holm'e gore siralanmis; artefaktin liste sirasi baska. Esleme ADLA
# kuruldu (asagidaki indisler `inferential_tests.results` icindeki gercek satirlar):
#   1 vae9182/logit_std (kontrol) · 2 stage1/logit_std · 3 stage1 T* · 4 FERPlus T* ·
#   5 primary/logit_std · 6 vae9182 oracle gate
HOLM = [("1", 3), ("2", 1), ("3", 0), ("4", 5), ("5", 2), ("6", 4)]
for row, i in HOLM:
    sel = f"results[{i}]"
    b("tab_holm", -1, row, 0, A_INF, f"{sel}.mean", "4dp", ident=f"tab_holm.rank{row}.mean")
    b("tab_holm", -1, row, 1, A_INF, f"{sel}.sd", "4dp", ident=f"tab_holm.rank{row}.sd")
    b("tab_holm", -1, row, 2, A_INF, f"{sel}.t", "1dp", ident=f"tab_holm.rank{row}.t")
    b("tab_holm", -1, row, 3, A_INF, f"{sel}.p_holm", "4dp", ident=f"tab_holm.rank{row}.p_holm")

# =============================================================================
# 7 · tab_human — ferplus_student_jsd @swa
# =============================================================================
HUMAN = [("0.26", "0.26"), ("0.51", "0.5063"), ("0.74", "0.74"), ("1.00", "1.0")]
for row, key in HUMAN:
    cell = f'by_checkpoint.swa["{key}"]'
    b("tab_human", -1, row, 0, A_FSJ, f"{cell}.teacher_ece", "4dp",
      ident=f"tab_human.T{key}.teacher_ece")
    b("tab_human", -1, row, 1, A_FSJ, f"{cell}.ece[0]", "4dp",
      ident=f"tab_human.T{key}.student_ece_mean")
    b("tab_human", -1, row, 2, A_FSJ, f"{cell}.ece[1]", "4dp",
      ident=f"tab_human.T{key}.student_ece_sd")
    b("tab_human", -1, row, 3, A_FSJ, f"{cell}.jsd[0]", "4dp",
      ident=f"tab_human.T{key}.jsd_mean")
    b("tab_human", -1, row, 4, A_FSJ, f"{cell}.jsd[1]", "4dp",
      ident=f"tab_human.T{key}.jsd_sd")
    b("tab_human", -1, row, 5, A_FSJ, f"{cell}.entropy", "3dp",
      ident=f"tab_human.T{key}.entropy")
HUM_FOOT = "Human annotator entropy"
b("tab_human", -1, HUM_FOOT, 0, A_FSJ, "human_mean_entropy", "3dp",
  ident="tab_human.human_entropy")

# =============================================================================
# 8 · tab_pooled — two_dataset_overlay.pooled_stats
# =============================================================================
for row, ck in (("SWA", "swa"), ("best", "best"), ("last", "last")):
    b("tab_pooled", -1, row, 0, A_TDO, f"pooled_stats.{ck}.spearman_abs_signed_gap", "3dp",
      ident=f"tab_pooled.{ck}.spearman_unsigned")
    # `r` (unsigned) sutunu 17 Agu'a kadar KAYITSIZDI: makalede duruyordu, hicbir artefakt
    # havuzlanmis 14 nokta uzerinde Pearson hesaplamiyordu. Karar (Fatih): sutunu silmek yerine
    # kaynagini uretmek -- `two_dataset_overlay.pearson`, Spearman'in yanina, ayni dongude.
    b("tab_pooled", -1, row, 1, A_TDO, f"pooled_stats.{ck}.pearson_abs_signed_gap", "3dp",
      ident=f"tab_pooled.{ck}.pearson_unsigned")
    b("tab_pooled", -1, row, 2, A_TDO, f"pooled_stats.{ck}.spearman_signed_gap", "3dp",
      ident=f"tab_pooled.{ck}.spearman_signed")
b("tab_pooled", -1, "Checkpoint _s (unsigned) r (unsigned) _s (signed)", None, None, None,
  None, ident="tab_pooled.header")
BINDINGS.pop()      # baslik satirinda sayi yok; yer tutucu geri alindi

ex("tab_pooled", -1, "calibration error over all 14 grid points", None, "population_count",
   "iki veri kumesinin izgara noktasi sayisi (14) -- olcum degil, sayim")

# =============================================================================
# 9 · tab_capacity — RESULTS_TABLES T10
# =============================================================================
CAP = [("width 0.50 scratch", "scratch w050"), ("width 0.75 scratch", "scratch w075"),
       ("width 1.00 scratch", "scratch w100ns"), ("width 1.00 pre-trained", "pretrained w100")]
CAP_PARAMS = {"scratch w050": 0.712, "scratch w075": 1.380,
              "scratch w100ns": 2.248, "pretrained w100": 2.248}
for row, cell in CAP:
    b("tab_capacity", -1, row, 1, A_RT, f'T10_capacity_cells.swa["{cell}"].acc_mean', "2dp",
      ident=f"tab_capacity.{cell}.acc_mean")
    b("tab_capacity", -1, row, 2, A_RT, f'T10_capacity_cells.swa["{cell}"].acc_sd', "2dp",
      ident=f"tab_capacity.{cell}.acc_sd")
    b("tab_capacity", -1, row, 3, A_RT, f'T10_capacity_cells.swa["{cell}"].ece_mean', "4dp",
      ident=f"tab_capacity.{cell}.ece_mean")
    b("tab_capacity", -1, row, 4, A_RT, f'T10_capacity_cells.swa["{cell}"].ece_sd', "4dp",
      ident=f"tab_capacity.{cell}.ece_sd")
    ex("tab_capacity", -1, row, 0, "architecture_dim",
       "ogrenci parametre sayisi (M) -- mimari boyutu, olcum degil")
CAP_FOOT = "Student-ECE range across the capacity axis"
b("tab_capacity", -1, CAP_FOOT, 1, A_RT, "T10_axis_spans.swa.capacity_span", "5dp",
  ident="tab_capacity.capacity_span")
b("tab_capacity", -1, CAP_FOOT, 2, A_RT, "T10_axis_spans.swa.teacher_span", "4dp",
  ident="tab_capacity.teacher_span")
ex("tab_capacity", -1, CAP_FOOT, 0, "architecture_dim",
   "3.16x parametre orani -- mimari boyut orani, olcum degil")

# =============================================================================
# 10 · tab_collapse — RESULTS_TABLES T11/T12
# =============================================================================
for row, key in (("T = 5.10", "T·τ = 5.10"), ("T = 10.20", "T·τ = 10.20")):
    b("tab_collapse", 0, row, 0, A_RT, f'T11_collapse.pairs["{key}"].mean', "4dp",
      ident=f"tab_collapse.{key}.mean")
    b("tab_collapse", 0, row, 1, A_RT, f'T11_collapse.pairs["{key}"].sd', "4dp",
      ident=f"tab_collapse.{key}.sd")
    ex("tab_collapse", 0, row, 2, "sign_count", "isaret sayaci 3/3 -- olcum degil, sayim")
    ex("tab_collapse", 0, row, 3, "sign_count", "isaret sayaci 3/3")
for row in ("0.1", "0.3", "0.5", "0.7", "0.9"):
    for k, s in enumerate(("42", "1", "43")):
        b("tab_collapse", 1, row, k, A_RT, f'T12_alpha.gaps["{row}"].by_seed["{s}"]', "4dp",
          ident=f"tab_collapse.alpha{row}.seed{s}")
    b("tab_collapse", 1, row, 3, A_RT, f'T12_alpha.gaps["{row}"].mean', "4dp",
      ident=f"tab_collapse.alpha{row}.mean")
b("tab_collapse", -1, "seed deviation 0.0024 ). Bottom: the benefit of pre-", 0, A_CSM,
  "rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_2sd",
  "4dp", ident="tab_collapse.threshold_2bar")
ex("tab_collapse", 1, "T = 10.20", None, "column_header",
   "alpha bloguna ait sutun basligi (tohum kimlikleri 42/1/43); etiket ustteki satirdan tasindi")

# =============================================================================
# 11 · tab_efficiency — efficiency_retention + latency_benchmark
# =============================================================================
b("tab_efficiency", -1, "POSTER++ teacher", 0, A_EFF, "teacher.params_m", "3dp",
  ident="tab_efficiency.teacher.params_m")
b("tab_efficiency", -1, "POSTER++ teacher", 1, A_EFF, "teacher.flops_g", "3dp",
  ident="tab_efficiency.teacher.gmacs")
b("tab_efficiency", -1, "POSTER++ teacher", 2, A_EFF, "teacher.size_mb", "1dp",
  ident="tab_efficiency.teacher.size_mb")
b("tab_efficiency", -1, "POSTER++ teacher", 3, A_EFF, "teacher.acc", "2dp",
  ident="tab_efficiency.teacher.acc")
b("tab_efficiency", -1, "MobileNetV2Plus student", 0, A_EFF, "student.params_m", "3dp",
  ident="tab_efficiency.student.params_m")
b("tab_efficiency", -1, "MobileNetV2Plus student", 1, A_EFF, "student.flops_g", "3dp",
  ident="tab_efficiency.student.gmacs")
b("tab_efficiency", -1, "MobileNetV2Plus student", 2, A_EFF, "student.size_mb", "1dp",
  ident="tab_efficiency.student.size_mb")
b("tab_efficiency", -1, "MobileNetV2Plus student", 3, A_EFF, "by_checkpoint.swa.acc_mean",
  "2dp", ident="tab_efficiency.student.acc_mean")
b("tab_efficiency", -1, "MobileNetV2Plus student", 4, A_EFF, "by_checkpoint.swa.acc_sd",
  "2dp", ident="tab_efficiency.student.acc_sd")
b("tab_efficiency", -1, "ratio", 0, A_EFF, "compression.params_ratio", "1dp",
  ident="tab_efficiency.ratio.params")
b("tab_efficiency", -1, "ratio", 1, A_EFF, "compression.flops_ratio", "1dp",
  ident="tab_efficiency.ratio.flops")
b("tab_efficiency", -1, "ratio", 2, A_EFF, "compression.size_ratio", "1dp",
  ident="tab_efficiency.ratio.size")
b("tab_efficiency", -1, "ratio", 3, A_EFF, "headline.retention_pct_swa", "1dp",
  ident="tab_efficiency.ratio.retention")
# Gecikme dipnotu `\\emph{Latency ...}` ile basliyor, yani tarayici icin bir BOLUM basligi.
# Jetonlar: [0] fp32'nin 32'si, sonra her cihaz icin (yigin, hizlanma) ikilileri.
for k, (dev, batch) in enumerate((("cuda", 1), ("cuda", 32), ("cpu", 1), ("cpu", 32))):
    b("tab_efficiency", 0, "§header", 2 + 2 * k, A_LAT,
      f"speedups[device={dev}][batch={batch}][dtype=fp32].speedup", "2dp",
      ident=f"tab_efficiency.latency.{dev}_b{batch}")
    ex("tab_efficiency", 0, "§header", 1 + 2 * k, "hyperparameter",
       f"yigin boyutu b={batch} -- olcum degil")
ex("tab_efficiency", 0, "§header", 0, "dtype_name", "fp32 -- veri tipi adi, olcum degil")
EFF_CAP1 = "25.8 cheaper in multiply--accumulates but between 1.9"
b("tab_efficiency", -1, EFF_CAP1, 0, A_EFF, "compression.flops_ratio", "1dp",
  ident="tab_efficiency.caption.flops_ratio")
b("tab_efficiency", -1, EFF_CAP1, 1, A_LAT,
  "speedups[device=cuda][batch=1][dtype=fp32].speedup", "1dp",
  ident="tab_efficiency.caption.speedup_min")
b("tab_efficiency", -1, "and 4.4 faster in wall-clock time", 0, A_LAT,
  "speedups[device=cpu][batch=32][dtype=fp32].speedup", "1dp",
  ident="tab_efficiency.caption.speedup_max")
ex("tab_efficiency", -1, "and 4.4 faster in wall-clock time", 1, "benchmark_protocol",
   "olcum protokolu: yigin 32")
ex("tab_efficiency", -1, "and 4.4 faster in wall-clock time", 2, "benchmark_protocol",
   "olcum protokolu: 200 zamanlanmis yineleme")
ex("tab_efficiency", -1, "iterations after 50 warm-up on GPU", None, "benchmark_protocol",
   "olcum protokolu: isinma/yineleme sayilari")
ex("tab_efficiency", -1, "Measured on an idle machine", None, "hardware_name",
   "donanim adi (RTX 5070, Ryzen 9)")
ex("tab_efficiency", -1, "7950X 16 cores).", None, "hardware_name",
   "donanim adi ve cekirdek sayisi")

# =============================================================================
# 12 · tab_selection_audit — selection_gain + order_stat_trend
# =============================================================================
AUDIT_ROWS = [("RAF-DB best - last", "b_best_minus_last", "rafdb_best_last"),
              ("RAF-DB best - SWA", "c_best_minus_swa", "rafdb_best_swa")]
for row, key, slug in AUDIT_ROWS:
    for k, (field, sub, rnd) in enumerate([("d_acc", "mean", "2dp"), ("d_acc", "sd", "2dp"),
                                           ("d_ece", "mean", "4dp"), ("d_ece", "sd", "4dp")]):
        b("tab_selection_audit", -1, row, k, A_SG,
          f"audit_deltas.{key}.{field}.{sub}", rnd,
          ident=f"tab_selection_audit.{slug}.{field}_{sub}")
    b("tab_selection_audit", -1, row, 4, A_SG, f"audit_deltas.{key}.n", "int",
      ident=f"tab_selection_audit.{slug}.n")
# FERPlus satirlari (N14, 17 Agu): `selection_gain.audit_deltas` yalniz RAF-DB kirilimi tasiyor,
# ama ayni ESTIMAND FERPlus icin de uretilmis -- `selection_audit_inference` dort kontrastin
# hepsini ayni CSV'lerden ve ayni tanimla hesapliyor. YENI URETICI YAZILMADI: ikinci bir tanim
# getirmek yerine var olan alan baglandi. Iki artefaktin ORTUSEN sekiz RAF-DB degeri birebir
# ayni (bit duzeyinde dogrulandi, 17 Agu), yani bolunme bir tanim ayrismasi degil.
for row, con, slug in (("FERPlus best - last", "best-last", "ferplus_best_last"),
                       ("FERPlus best - SWA", "best-swa", "ferplus_best_swa")):
    sel = f'datasets["FERPlus"].contrasts["{con}"]'
    for k, (path, rnd) in enumerate(((f"{sel}.acc_pp.mean", "2dp"), (f"{sel}.acc_pp.sd", "2dp"),
                                     (f"{sel}.ece.mean", "4dp"), (f"{sel}.ece.sd", "4dp"),
                                     (f"{sel}.acc_pp.n", "int"))):
        b("tab_selection_audit", -1, row, k, A_SAI, path, rnd,
          ident=f"tab_selection_audit.{slug}." + ["d_acc_mean", "d_acc_sd", "d_ece_mean",
                                                  "d_ece_sd", "n"][k])
# Sira-istatistigi satirlari: 17 Agu'da makale tarafinda ACIKCA RAF-DB etiketi verildi (once
# birinci sutun bostu ve satir ustteki FERPlus etiketini miras aliyordu). Bag da o gun guncellendi
# -- eski etiketle duran beyan `binding_matched_nothing` veriyordu, yani denetci degisikligi gordu.
for k, K in enumerate(("50", "100")):
    b("tab_selection_audit", 0, f"RAF-DB K = {K}", 0, A_OST,
      f'results["{K}"].a2_raw.mean', "3dp", ident=f"tab_selection_audit.order_stat.K{K}.mean")
    b("tab_selection_audit", 0, f"RAF-DB K = {K}", 1, A_OST,
      f'results["{K}"].a2_raw.sd', "3dp", ident=f"tab_selection_audit.order_stat.K{K}.sd")
    b("tab_selection_audit", 0, f"RAF-DB K = {K}", 2, A_OST,
      f'results["{K}"].n_runs', "int", ident=f"tab_selection_audit.order_stat.K{K}.n")


MDE_CAP1 = "0.0024 (Stage1 eff.) to 0.0067 (Primary none)"
b("app_mde", -1, MDE_CAP1, 0, A_CSM, "mde_ece_swa_min", "4dp", ident="app_mde.cap.swa_min")
b("app_mde", -1, MDE_CAP1, 2, A_CSM, "mde_ece_swa_max", "4dp", ident="app_mde.cap.swa_max")
ex("app_mde", -1, MDE_CAP1, 1, "teacher_name_digits", "Stage1 adinin icindeki basamak")
MDE_CAP2 = "in absolute ECE and 3.2 % to 19.4 % (VAE9182 none) as a"
b("app_mde", -1, MDE_CAP2, 0, A_CSM, "mde_ece_swa_pct_min", "1dp",
  ident="app_mde.cap.swa_pct_min")
b("app_mde", -1, MDE_CAP2, 1, A_CSM, "mde_ece_swa_pct_max", "1dp",
  ident="app_mde.cap.swa_pct_max")
ex("app_mde", -1, MDE_CAP2, 2, "teacher_name_digits", "VAE9182 adinin icindeki basamak")
ex("app_mde", -1, "from the rounded columns can differ by 0.1 point.", None, "rounding_caveat",
   "yuvarlama uyarisinin kendisi (0.1 puan) -- olcum degil")

# --- app_predecl (S11): on-kayit provenans metadatasi. OLCUM DEGIL ve yapilandirilmis
# artefakti YOK (preregistration_blocks.csv yalniz kosu->blok eslemesi tasiyor, lead suresi
# tasimiyor). Bu turda beyanla kapsam disi; acik kalem olarak raporda yazildi.
# 21 Agu 2026: "Miscalibration pilot kill-switch" ve "Oracle-gate extension" satirlari bu
# donguden CIKARILDI -- lead jetonlari (8 h, 12 h) artik muaf degil, `prereg_lead_audit`
# alanlarina bagli (asagida). Satirlarin n/bolum jetonlari ayri muafiyetle duruyor.
# 27 Agu 2026 (EK-1): "T factorial" da donguden CIKTI -- S11'e Lead basildi (108 s),
# jetonu artik muaf degil, A9'un alanina bagli (asagida, A2/A8 kalibiyla).
for _r in ("Control teacher flat response",
           "Second-dataset replication", "Human-alignment arm",
           "Logit standardisation three seeds",
           "Initialisation-matched capacity arm", "Learned-signal gate three seeds",
           "Student-scaling joint frontier", "Capacity sweep",
           "Oracle-gate diagnostic (original)", "Student-head isolation",
           "Control completion (two teachers)", "Over-confident dose--response"):
    for _s in (0, 1, 2, 3):
        ex("app_predecl", _s, _r, None, "preregistration_provenance",
           "on-beyan lead suresi / ongoru sayisi / bolum atfi -- olcum degil, saglama "
           "PREREGISTRATIONS.md + git zaman damgasi", opt=True)

# S11'in saat-birimli iki lead'i BAGLI (21 Agu 2026, jeton final). Kip `int_floor`: Lead
# "en gec su kadar once donduruldu" iddiasidir, asagi yuvarlanir -- 0.998 tabaniyla ayni
# mantik. Olculdu: A2 = 8sa43dk (8.7239 sa) -> 8 (yari-yukari 9 verirdi, basili 8 bastan
# beri taban kipiyle tutarliydi); A8 = 12sa57dk (12.9539 sa) -> 12 (yari-yukari 13 verirdi
# ve 20 Agu'ya kadar basili deger tam da oydu -- F4 bulgusu). Kural artik tablo genelinde
# TEK: floor. Saniye-birimli dort lead (20/19/18/28 s) tamsayi-kesin, floor==deger.
# sec=0 ZORUNLU (olculdu): app_predecl'in `\multicolumn` grup basliklari bolum sayacini
# ilerletiyor, A2/A8 satirlari s0'da; -1 eslesmiyor (matcher bolumu BIREBIR karsilastirir).
b("app_predecl", 0, "Miscalibration pilot kill-switch", 0, A_PL,
  "items.A2.lead_hours", "int_floor", ident="app_predecl.A2.lead_h")
b("app_predecl", 0, "Oracle-gate extension", 0, A_PL,
  "items.A8.lead_hours", "int_floor", ident="app_predecl.A8.lead_h")
ex("app_predecl", 0, "Miscalibration pilot kill-switch", 1, "preregistration_provenance",
   "A2'nin tasidigi ongoru sayisi (n=1); olcum degil, beyan")
ex("app_predecl", 0, "Miscalibration pilot kill-switch", 2, "table_reference",
   "S5.2 bolum atfi")
ex("app_predecl", 0, "Oracle-gate extension", 1, "preregistration_provenance",
   "A8'in tasidigi ongoru sayisi (n=3); olcum degil, beyan")
ex("app_predecl", 0, "Oracle-gate extension", 2, "table_reference",
   "S5.5 bolum atfi")
# 27 Agu 2026 (EK-1): tau x T faktoriyelinin lead'i basildi -> A9 alanina bagli.
# 108 s tamsayi-kesin, floor==deger (tablo geneli tek kural: floor).
b("app_predecl", 0, "T factorial", 0, A_PL,
  "items.A9.lead_seconds", "int_floor", ident="app_predecl.A9.lead_s")
ex("app_predecl", 0, "T factorial", 1, "preregistration_provenance",
   "A9'un tasidigi ongoru sayisi (n=3); olcum degil, beyan")
ex("app_predecl", 0, "T factorial", 2, "table_reference",
   "S5.3 bolum atfi")

# --- tab_collapse caption muafiyetleri ve olcut sabiti
ex("tab_collapse", -1, "Pre-declared factorial on the Stage1 teacher", None,
   "teacher_name_digits", "Stage1 adinin icindeki basamak")
ex("tab_collapse", -1, "order of magnitude above the pre-declared threshold", None,
   "criterion_constant", "olcut: 2x kontrol sd'si (esik tanimi)")
ex("tab_collapse", -1, "ECE(T = 1) - ECE(T = 1.34) within seed", None, "hyperparameter",
   "gap(alpha) tanimindaki sicakliklar T=1 ve T=1.34")
ex("tab_collapse", -1, "= 0.5 and reverses sign by = 0.9", None, "hyperparameter",
   "sert etiket agirligi alpha degerleri")

# =============================================================================
# 13 · abstract — manset sayilar
# =============================================================================
b("abstract", -1, "= 0.79 ) --- while accuracy", 0, A_TDO,
  "pooled_stats.swa.spearman_abs_signed_gap", "2dp", ident="abstract.pooled_rho")
b("abstract", -1, "checkpoints: across", 0, A_SG,
  "audit_deltas.b_best_minus_last.n", "int", ident="abstract.audit_n_runs")
b("abstract", -1, "reported partition inflates accuracy", 0, A_SG,
  "audit_deltas.b_best_minus_last.d_acc.mean", "2dp", ident="abstract.selection_inflation")
# Asimetri araligi: iki UC, ikisi de alan. Ozetin "1.8--2.0x"i, ARA DEGERLENDIRME yapilmamis
# (extrapole edilmemis) iki karsilastirmanin min/max'i -- artefaktin kendi ozet blogu.
b("abstract", -1, "over-confidence is 1.8", 0, A_ASY,
  "summary.interpolated_only.absolute.min", "1dp", ident="abstract.asymmetry_min")
b("abstract", -1, "over-confidence is 1.8", 1, A_ASY,
  "summary.interpolated_only.absolute.max", "1dp", ident="abstract.asymmetry_max")
b("abstract", -1, "harm is a median", 0, A_NU, "summary.median",
  "int", ident="abstract.logitstd_noise_median")


# --- olcum olmayan kalan jetonlar (beyan)
ex("tab_holm", -1, "at n = 3 ( df = 2 )", None, "sample_size",
   "n=3 ve df=2 -- tasarim sayisi, olcum degil")
ex("tab_holm", -1, "The family was fixed on 1 August 2026", None, "date",
   "aile sabitleme tarihi (1 Agustos 2026)")
ex("tab_human", -1, "n = 3 ). Students are scored", None, "sample_size", "n=3")
ex("tab_mechanisms", 0, "those ratios are in Supplementary Table", None, "table_reference",
   "Supplementary Table S8 atfi")

# =============================================================================
# TURETILMIS NICELIKLER (derived_registry)
# =============================================================================
def op(artifact, path):
    return {"artifact": artifact, "path": path}


pv("methodology.entropy_pearson_T1", "ferplus_jsd/ferplus_jsd.json",
   "entropy_correlation.T1.pearson", "3dp", "sections/03_methodology.tex#per-sample entropy correlation is",
   note="'per-sample entropy correlation is r=0.724 at T=1' -- bag T=1 KOLUNA kurulu; dis "
        "inceleme bu sayinin yanlis kola atfedildigini bildirmisti")
dv("jsd_collapse", "37", "ratio",
   [op(A_R3W, 'arms["0.26"].jsd_arm[0] - arms["0.74"].jsd_arm[0]'),
    op(A_R3W, 'arms["0.74"].jsd_ts[0] - arms["0.26"].jsd_ts[0]')],
   "int", None, None, None, None,
   where="sections/05_results_discussion.tex#collapse onto a common value",
   note="'collapse onto a common value' cumlesi; N12'de olculdu")
dv("jsd_noise_ratio", "40", "ratio",
   [op(A_JCA, "numerator.value"), op(A_JCA, "R_noise.seed_sd_by_convention[\"mean sd\"]")],
   "int", None, None, None, None,
   where="sections/05_results_discussion.tex#times the noise",
   note="ayni alt bolumun govdesi: 'roughly forty times the noise'")
dv("capacity_vs_teacher_lever", "76", "ratio",
   [op(A_RT, "T10_axis_spans.swa.teacher_span"),
    op(A_RT, "T10_axis_spans.swa.capacity_span")],
   "int", "tab_capacity", -1, CAP_FOOT, 3,
   note="tab_capacity dipnotu: 'a factor of 76'")
dv("selection_cost_best", "0.52", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.acc_mean"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.acc_mean")],
   "2dp", "tab_selection", -1, SEL_FOOT, 2)
dv("selection_cost_swa", "0.35", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.swa.acc_mean"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.swa.acc_mean")],
   "2dp", "tab_selection", -1,
   "( 89.60 pp each) and the cost of the accuracy rule i", 1)
dv("selection_cost_last", "0.83", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.last.acc_mean"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.last.acc_mean")],
   "2dp", "tab_selection", -1,
   "there 0.52 pp here and 0.83 pp at the last checkpoint.", 1)
dv("human_trade_ece", "+0.0159", "diff",
   [op(A_FSJ, 'by_checkpoint.swa["0.74"].ece[0]'),
    op(A_FSJ, 'by_checkpoint.swa["0.5063"].ece[0]')],
   "4dp", "tab_human", -1, HUM_FOOT, 1)
dv("human_trade_jsd", "-0.0051", "diff",
   [op(A_FSJ, 'by_checkpoint.swa["0.74"].jsd[0]'),
    op(A_FSJ, 'by_checkpoint.swa["0.5063"].jsd[0]')],
   "4dp", "tab_human", -1, HUM_FOOT, 2)
dv("collapse_ratio_5_10", "16.3", "ratio",
   [op(A_RT, 'T11_collapse.pairs["T·τ = 5.10"].mean'), op(A_RT, "T11_collapse.two_bar")],
   "1dp", "tab_collapse", 0, "T = 5.10", 4, note="|ort|/esik; isaret disi")
dv("collapse_ratio_10_20", "13.5", "ratio",
   [op(A_RT, 'T11_collapse.pairs["T·τ = 10.20"].mean'), op(A_RT, "T11_collapse.two_bar")],
   "1dp", "tab_collapse", 0, "T = 10.20", 4, note="|ort|/esik; isaret disi")

# --- N14 (17 Agu 2026): kayitsiz kalan turetilmis nicelikler
dv("selection_cost_best_caption", "0.52", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.acc_mean"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.acc_mean")],
   "2dp", "tab_selection", -1, "there 0.52 pp here and 0.83 pp at the last c", 0,
   note="AYNI nicelik, ikinci gecis: alt yazi. Dipnottaki `selection_cost_best` ile ayni "
        "pay/payda; iki yerde basildigi icin iki kez kaydediliyor")
# Ozetin ECE azalmasi araligi: iki UC, ikisi de 'duzeltilmemis kol T=1' -> 'duzeltilmis kol T*'
# yuzde dususu. AYRI AYRI kaydedildi, cunku bir aralik tek bir olcum degil iki olcumdur.
dv("ece_reduction_min", "41", "pct_drop",
   [op(A_TDO, "arms.rafdb_stage1.points[1].by_ckpt.swa.ece_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.ece_mean")],
   "int", "abstract", -1, "calibration error 41 -- 76", 0,
   note="Stage1: T=1 -> T=1.3406 (dagitilan kol), @SWA ogrenci ECE'si")
dv("ece_reduction_max", "76", "pct_drop",
   [op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.ece_mean"),
    op(A_TDO, "arms.ferplus.points[1].by_ckpt.swa.ece_mean")],
   "int", "abstract", -1, "calibration error 41 -- 76", 1,
   note="FERPlus: T=1 -> T=0.5063 (dagitilan kol), @SWA ogrenci ECE'si")
# Ozetin "accuracy stays within 0.51 pp"i: KOL ICI dogruluk acikligi, uc kolun EN GENISI.
# §3.6 ayni niceligi iki RAF-DB kolu icin veriyor (0.30 ve 0.51), yani estimand adlandirilmis.
dv("accuracy_band_widest_arm", "0.51", "diff",
   [op(A_TDO, "arms.rafdb_vae9182.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_vae9182.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "abstract", -1, "= 0.79 ) --- while accuracy", 1,
   note="VAE9182 kolunun en yuksek (T=1.3406) ve en dusuk (T=1.70) @SWA dogrulugu; olculen kol "
        "aciklikleri 0.304 / 0.511 / 0.486, ozet en genisi basiyor")
# §3.2, DUZYAZI -- kapsam disi metinden TEK TEK beyanla iceri alinan iki uc. Fatih'in 17 Agu
# kurali: turetilmis nicelik asla basili yuvarlak degerden hesaplanmaz. Bu iki sayi 14 Agu'da
# tam o hatayla (0.0015/0.0220) yeniden uretilmisti; artik pay ve payda alan yolu.
# --- N16: S2 duzyazisinin turetilmis nicelikleri
dv("robust_agreeing_steps", "224", "diff",
   [op(A_ROB, "total_steps"), op(A_ROB, "total_breaks")],
   "int", "robust", -1, "bottoms out. Across", 1,
   note="uyusan adim sayisi = toplam adim - kirilma; makale 224'u basiyor, artefakt ikisini")
dv("robust_agreement_pct", "97.0", "pct_of",
   [op(A_ROB, "total_steps - total_breaks"), op(A_ROB, "total_steps")],
   "1dp", "robust", -1, "temperature pair (", 0,
   note="paydasi CUMLEDE adlandirilmis: 231 adim")
dv("jsd_smallest_stratum_pct", "0.9", "pct_of",
   [op(A_JSD, 'results["(c) stratum 6-7"].n'), op(A_JSD, 'results["(a) all rows"].n')],
   "1dp", "robust", -1, "0.9 % of the fold", 0,
   note="en kucuk katmanin foldun yuzde kaci: 28 / 3153")
# 13-14x AYNI nicelik, ucuncu ve dorduncu gecis (§3.2 duzyazisi + S2 duzyazisi). Ayni pay/payda.
dv("tstar_criterion_cost_min_supp", "13", "ratio",
   [op(A_TSS, "results.ferplus.ece_removed_by_ts"), op(A_TSS, "results.ferplus.d_ece")],
   "int", "robust", -1, "the ECE minimum costs at most", 1,
   note="§3.2'deki `tstar_criterion_cost_min` ile ayni pay/payda, S2'deki ikinci gecis")
dv("tstar_criterion_cost_max_supp", "14", "ratio",
   [op(A_TSS, "results.stage1.ece_removed_by_ts"), op(A_TSS, "results.stage1.d_ece")],
   "int", "robust", -1, "the ECE minimum costs at most", 2,
   note="§3.2'deki `tstar_criterion_cost_max` ile ayni pay/payda, S2'deki ikinci gecis")
dv("tstar_criterion_cost_min", "13", "ratio",
   [op(A_TSS, "results.ferplus.ece_removed_by_ts"), op(A_TSS, "results.ferplus.d_ece")],
   "int", None, None, None, None,
   where="sections/03_methodology.tex#times smaller than the ECE the scaling removes",
   note="FERPlus 13.31x -- uc ogretmenin en dusugu (primary 13.60, stage1 14.32)")
dv("tstar_criterion_cost_max", "14", "ratio",
   [op(A_TSS, "results.stage1.ece_removed_by_ts"), op(A_TSS, "results.stage1.d_ece")],
   "int", None, None, None, None,
   where="sections/03_methodology.tex#times smaller than the ECE the scaling removes",
   note="Stage1 14.32x -- uc ogretmenin en yuksegi; vae9182 disarida cunku TS orada ECE EKLIYOR")

# =============================================================================
# 14 · supplementary S1-S3 (18 Agu 2026, N16) — kapsam genisletmesi
# =============================================================================
# NEDEN SIMDI. Kapsam beyani "S1-S3 girmez (bugunku headroom hukmu oraya henuz islenmedi)"
# diyordu ve BAYATLAMISTI: hukum S2'ye islendi. 15 Agustos'taki celiskiyi ureten sayilarin
# (headroom noktasi ve GA'si) tamami orada duruyor -- belgede bagsiz duran en yuksek riskli
# hucreler onlardi.
# S3 tarandi ve SIFIR jeton verdi: govdesi yalniz `\input` ve `\ref`, tablolarin kendisi zaten
# TABLE_FILES uzerinden kapsamda. Bos cikan bir kapsam da bir olcumdur, beyani duruyor.

# --- S2 tablosu app_tstar: dordu de `tstar_sensitivity`in kendi satirlari
for row, t in (("stage1", "stage1"), ("primary", "primary"), ("control", "vae9182"),
               ("FERPlus", "ferplus")):
    for k, (fld, rnd) in enumerate((("T_star_nll", "3dp"), ("T_star_ece", "3dp"),
                                    ("d_ece", "4dp"), ("ece_removed_by_ts", "4dp"))):
        b("app_tstar", -1, row, k, A_TSS, f"results.{t}.{fld}", rnd,
          ident=f"app_tstar.{t}.{fld}")
b("app_tstar", -1, "text says so (FERPlus and Stage1 at a half-fold", 1, A_TSP,
  "half_fold_fits.stage1", "4dp", ident="app_tstar.caption.half_fold")
b("app_tstar", -1, "against the full-fold 1.3494", 0, A_TSS, "results.stage1.T_star_nll",
  "4dp", ident="app_tstar.caption.full_fold")
b("app_tstar", -1, "local minimum; the dense-grid check", 0, A_TSS, "dense_grid.step", "3dp",
  ident="app_tstar.caption.dense_step")
b("app_tstar", -1, "local minimum; the dense-grid check", 1, A_TSS,
  "results.stage1.dense_grid_ece", "4dp", ident="app_tstar.caption.dense_ece")
b("app_tstar", -1, "at T = 1.335", 0, A_TSS, "results.stage1.dense_grid_T", "3dp",
  ident="app_tstar.caption.dense_T")
ex("app_tstar", -1, "text says so (FERPlus and Stage1 at a half-fold", 0, "teacher_name_digits",
   "alt yazidaki 'Stage1' adinin icindeki basamak")
ex("app_tstar", -1, "Section ). The stage1 ECE", 0, "teacher_name_digits",
   "alt yazidaki 'stage1' adinin icindeki basamak")

# --- S2 tablosu app_jsd: `jsd_sensitivity` kesitleri
JSD_ROWS = [("all rows", "(a) all rows"), ("vote sum =10", "(b) vote sum = 10"),
            ("stratum 6--7", "(c) stratum 6-7"), ("stratum 8--9", "(c) stratum 8-9"),
            ("stratum 10", "(c) stratum 10")]
for row, key in JSD_ROWS:
    cell = f'results["{key}"]'
    b("app_jsd", -1, row, 0, A_JSD, f"{cell}.n", "int", ident=f"app_jsd.{key}.n")
    for k, fld in enumerate(("T_ece", "T_nll", "T_jsd"), start=1):
        b("app_jsd", -1, row, k, A_JSD, f"{cell}.{fld}", "2dp", ident=f"app_jsd.{key}.{fld}")

# --- S2 tablosu app_argmin: uzlasi T'leri + "7/7" sayaclari (18 Agu 2026'da baglandi)
# 17 Agu'da bu satirda "BULUNAMADI" yaziyordu: sayaclar YALNIZ md'ye basiliyordu. Uretici
# `_consensus_metrics_agreeing` / `_n_metrics` alanlarini yazacak sekilde degistirildi ve
# md artik AYNI alanlari okuyor -- md ile JSON ayri ayri sayamaz, dolayisiyla ayrisamaz.
for row, key in (("RAF-DB stage1", "RAF-DB stage1"), ("RAF-DB control", "RAF-DB vae9182"),
                 ("FERPlus", "FERPlus")):
    b("app_argmin", -1, row, 0, A_ROB, f'series["{key}"]._consensus_T', "2dp",
      ident=f"app_argmin.{key}.consensus_T")
    b("app_argmin", -1, row, 1, A_ROB, f'series["{key}"]._consensus_metrics_agreeing', "int",
      ident=f"app_argmin.{key}.metrics_agreeing")
    b("app_argmin", -1, row, 2, A_ROB, f'series["{key}"]._n_metrics', "int",
      ident=f"app_argmin.{key}.n_metrics")
# Istisna sutunu: FERPlus'ta NLL'in argmin'i. IKI 0.74 VAR ve AYNI ALANA BAGLANMIYOR --
# gerekce olculdu: tabloda basilan sayi CO GUNLUGUN yeri (`argmin_T_modal`), S2 duzyazisinda
# basilan sayi ise HER TOHUMUN ayni yeri gosterdigi deger (`argmin_T_all_seeds`, oybirligi
# yoksa None). Ayni artefaktta 21 (seri x metrik) hucrenin 5'inde bu ikisi FARKLI (or.
# RAF-DB vae9182/NLL: modal 1.0, oybirligi yok -> None). Yani ayrim varsayim degil, olcum:
# tek alana baglamak "ayni ad, iki nicelik" ailesinin dorduncu uyesini kurardi.
b("app_argmin", -1, "FERPlus", 3, A_ROB, 'series["FERPlus"].metrics.nll.argmin_T_modal', "2dp",
  ident="app_argmin.FERPlus.nll_exception_modal")
ex("app_argmin", -1, "seed-level dissents", 0, "teacher_name_digits",
   "alt yazidaki 'stage1' adinin icindeki basamak")

# --- S2 duzyazisi: ROBUSTLUK paragrafi
b("robust", -1, "seeds of the NLL metric place the minimum at", 0, A_ROB,
  'series["FERPlus"].metrics.nll.argmin_T_all_seeds', "2dp",
  ident="robust.ferplus_nll_argmin_all_seeds")
b("robust", -1, "Every run of the three dose--response series", 0, A_ROB, "total_runs", "int",
  ident="robust.total_runs")
b("robust", -1, "bottoms out. Across", 0, A_ROB, "total_runs", "int",
  ident="robust.total_runs_2")
b("robust", -1, "bottoms out. Across", 2, A_ROB, "total_steps", "int",
  ident="robust.total_steps")
ex("robust", -1, "NLL Brier equal-width ECE at", None, "benchmark_protocol",
   "kestirici envanteri: 10/15/25 kutu -- olcum protokolu")
ex("robust", -1, "ECE at 15 bins and classwise ECE", None, "benchmark_protocol",
   "kutu sayisi 15 -- olcum protokolu")
ex("robust", -1, "15 -bin column was required to match", None, "benchmark_protocol",
   "kutu sayisi 15 -- olcum protokolu")
ex("robust", -1, "value to 10^", None, "criterion_constant",
   "kapinin toleransi 10^-9 (esik tanimi; artefakta `verification.tolerance` olarak da var)")
ex("robust", -1, "leaves ECE slightly worse than T = 1", 0, "hyperparameter",
   "olceklenmemis kol T=1")
ex("robust", -1, "T = 1 minus the minimum over the grid", 0, "hyperparameter",
   "Eq.8 tanimindaki T=1")
ex("robust", -1, "[+0.0151", 2, "teacher_name_digits", "'stage1' adinin icindeki basamak")
ex("robust", -1, "0.74 in every slice holding at least", 1, "criterion_constant",
   "kesit buyuklugu esigi 1{,}000 satir -- olcut, olcum degil")
# (binlik ayraci duzeltilince `1{,}000` tek jeton oldu; ikinci muafiyet dustu)
b("robust", -1, "the ECE minimum costs at most", 0, A_TSS, "max_d_ece", "4dp",
  ident="robust.max_criterion_cost")
b("robust", -1, "two criteria disagree in direction", 0, A_TSS, "results.vae9182.T_star_nll",
  "2dp", ident="robust.control_T_nll")
b("robust", -1, "the other side of unity", 0, A_TSS, "results.vae9182.T_star_ece", "2dp",
  ident="robust.control_T_ece")
b("robust", -1, "( 2000 resamples", 0, A_BOOT, "B", "int", ident="robust.bootstrap_B")
HEAD_ROWS = [("( 2000 resamples", 1, "stage1", "point.headroom_eq8", "4dp"),
             ("[+0.0151", 0, "stage1", "ci95.headroom_eq8[0]", "4dp"),
             ("[+0.0151", 1, "stage1", "ci95.headroom_eq8[1]", "4dp"),
             ("[+0.0151", 3, "primary", "point.headroom_eq8", "4dp"),
             ("[+0.0151", 4, "primary", "ci95.headroom_eq8[0]", "4dp"),
             ("[+0.0151", 5, "primary", "ci95.headroom_eq8[1]", "4dp"),
             ("primary +0.0023", 0, "vae9182", "point.headroom_eq8", "4dp"),
             ("primary +0.0023", 1, "vae9182", "ci95.headroom_eq8[0]", "4dp"),
             ("primary +0.0023", 2, "vae9182", "ci95.headroom_eq8[1]", "4dp")]
for row, idx, t, path, rnd in HEAD_ROWS:
    b("robust", -1, row, idx, A_BOOT, f"results.{t}.{path}", rnd,
      ident=f"robust.headroom.{t}.{path}")
# FERPlus'in headroom'u BASKA bir artefakttan gelir ve bu AYRIM onemli: ayni 0.1126'ya yuvarlanan
# UC alan var (`bootstrap_cis`, `headroom_grid_audit`, `headroom_review`) ve makale burada KOSU
# IZGARASI uzerindeki degeri aliyor -- 15 Agu'daki celiskinin cikis noktasi tam buydu.
b("robust", -1, "primary +0.0023", 3, A_HGA, "grids.run.headroom", "4dp",
  ident="robust.headroom.ferplus.point")
b("robust", -1, "[+0.1018", 0, A_HGA, "grids.run.ci95[0]", "4dp",
  ident="robust.headroom.ferplus.ci_lo")
b("robust", -1, "[+0.1018", 1, A_HGA, "grids.run.ci95[1]", "4dp",
  ident="robust.headroom.ferplus.ci_hi")
for k, fld in enumerate(("lo", "hi", "step")):
    b("robust", -1, "dense auxiliary grid", k, A_HGA, f"grids.boot.grid.{fld}", "2dp",
      ident=f"robust.dense_grid.{fld}")
b("robust", -1, "the ECE minimum at T = 0.46", 0, A_HGA, "grids.fine.T_argmin", "2dp",
  ident="robust.ferplus_fine_argmin")
b("robust", -1, "paper actually ran whose minimum is the deployed arm", 0, A_HGA,
  "grids.run.T_argmin", "4dp", ident="robust.ferplus_deployed_arm")
b("robust", -1, "0.74 in every slice holding at least", 0, A_JSD,
  "T_jsd_values_across_slices[0]", "2dp", ident="robust.jsd_optimum")
b("robust", -1, "T^ * _ NLL ) flips in the smallest stratum", 0, A_JSD, 'results["(c) stratum 6-7"].n',
  "int", ident="robust.smallest_stratum_n")

# --- S1: mekanizma tanimlari. KIRK BES JETONUN TAMAMI hiperparametre, formul sabiti ya da
# kaynakca sayisi -- yani hicbiri olcum degil. Tanim gereği: bir sayi ancak bir kosunun
# CIKTISIYSA olcumdur; S1 kosularin GIRDISINI yaziyor.
SPECS_EX = [
    ("shares = 6 = 0.3 and an unscaled teacher", None, "hyperparameter", "tau=6, alpha=0.3"),
    ("( T = 1 ); the single exception", None, "hyperparameter", "olceklenmemis kol T=1"),
    ("T_0 = 0.7311 by design", None, "hyperparameter", "miskalibrasyon pilotunun T_0'i"),
    ("( = 10^", None, "hyperparameter", "sayisal kararlilik sabiti epsilon=1e-6"),
    ("(1- _i) L _ KD i . Settings:", None, "hyperparameter", "kayip formulundeki 1"),
    ("_ lo = 0.1 _ hi = 0.7", None, "hyperparameter", "gate alpha_lo/alpha_hi"),
    ("k = 2 _g = 0", None, "hyperparameter", "gate k ve tau_g"),
    ("Direction of the oracle arm", None, "hyperparameter", "top-1 tanimindaki 1"),
    ("is wrong u_i = 1", None, "hyperparameter", "oracle sinyali u_i=1 (tanim)"),
    ("_ hi and the teacher's weight", None, "hyperparameter", "agirlik formulundeki 1"),
    ("_ T = 0.5 clamped to", None, "hyperparameter", "adaptive-T gamma=0.5"),
    ("T_i [1.0 2 ]", None, "hyperparameter", "T kelepcesi [1.0, 2tau] ve H_i'nin T=1'i"),
    ("Class-space Gaussian matching", None, "hyperparameter", "G2G basligindaki 2"),
    ("w KL ( N (", None, "hyperparameter", "formuldeki sigma^2 usleri"),
    ("| N (", None, "hyperparameter", "formuldeki sigma^2 usleri"),
    ("with w = 0.1 and no warm-up", None, "hyperparameter", "G2G agirligi w=0.1"),
    ("not an intermediate feature layer", None, "hyperparameter", "formuldeki sigma^2 usu"),
    ("is clamped to 10", None, "hyperparameter", "logvar kelepcesi +-10"),
    ("( ) ) with t_ = 1 t_ = 8", None, "hyperparameter", "CTKD t_min=1, t_max=8"),
    ("initialised at 0 and cosine-ramped", None, "hyperparameter", "theta baslangici ve rampa"),
    ("_ = 1 ; the gradient-reversal", None, "hyperparameter", "lambda_max=1"),
    ("( 3 10^", None, "hyperparameter", "ogrenme orani 3e-4"),
    ("Proc. AAAI", None, "citation", "cilt/sayi/sayfa/yil"),
    ("doi:10.1609", None, "citation", "DOI"),
    ("= 10^ -6 taken per sample", None, "hyperparameter", "logit standardizasyonu epsilon"),
    ("= 6 = 0.3 vanilla setup", None, "hyperparameter", "tau=6, alpha=0.3"),
]
for _row, _idx, _cls, _why in SPECS_EX:
    ex("specs", -1, _row, _idx, _cls, _why)


# =============================================================================
# 14 · ANA GOVDE DUZYAZISI (N19, 20 Agu 2026) — kapsam acildi
# =============================================================================
# NEDEN SIMDI. Kapsam ERTELENMISTI ve gerekcesi yaziliydi: "hareket eden hedefi baglamak curuk
# bag uretir". Bastan sona okuma 20 Agu'da bitti, duzyazi sabitlendi, erteleme sartinin kendisi
# ortadan kalkti. Tarayici artik `sections/*.tex`i de goruyor (paper_number_scan.SECTION_FILES).
#
# CIFT YUVARLAMA VAKASI -- KAPANDI (20 Agu 2026 aksami). Bu blok kuruldugunda iki bag BILEREK
# kirmizi birakilmisti: makale §1:151 ve §2:229'da "+0.65" basiyordu; alan
# `selection_gain.per_k["50"].a2_pure_order_statistic.mean` = 0.6445305842767274, yani 2 basamakta
# 0.64. 0.65 ancak CIFT YUVARLAMAYLA cikiyor: 0.6445 -> 0.645 (3 basamak, ki makale §4:150,
# §5:781 ve tab_selection_audit:25'te DOGRU basiyor) -> 0.65. Kampanyanin kendi kurali bunu
# yasakliyor ("turetilmis nicelik basili yuvarlanmis degerden hesaplanmaz"). Bag KURULMUS ve
# kapi kirmizi BIRAKILMISTI -- rapora saklanan bir kusur, kapinin gormedigi bir kusurdur.
# Makale tarafi ayni gun "+0.645"--"0.764" olarak duzeltti; beyanin yuvarlamasi da 2dp'den
# 3dp'ye cekildi ve iki bag yesile dondu. Kaydin kendisi duruyor: kapinin bir kusuru YAKALADIGI
# ve kusurun kapandigi, ikisi birlikte okunmadan anlasilmaz.

# --- §1 giris
b("01_introduction", -1, "branch in all nine seed curves", 0, A_TDO,
  "pooled_stats.swa.n_points", "int", ident="intro.pooled_n_points")
b("01_introduction", -1, "the three series yields a rank", 0, A_TDO,
  "pooled_stats.swa.spearman_abs_signed_gap", "2dp", ident="intro.pooled_rho")
b("01_introduction", -1, "over-confident teacher leaves the student", 0, A_ASY,
  "comparisons[2].ratio_absolute", "2dp", ident="intro.asym_rafdb")
b("01_introduction", -1, "2.04 on FERPlus", 0, A_ASY,
  "comparisons[5].ratio_absolute", "2dp", ident="intro.asym_ferplus")
b("01_introduction", -1, "calibration error by", 0, A_NU,
  'nine_cell_grid["swa|primary"].d_ece_mean', "3dp", ident="intro.logitstd_dece_min")
b("01_introduction", -1, "calibration error by", 1, A_NU,
  'nine_cell_grid["swa|vae9182"].d_ece_mean', "3dp", ident="intro.logitstd_dece_max")
b("01_introduction", -1, "its effect on accuracy by a median", 0, A_NU, "summary.median",
  "int", ident="intro.logitstd_noise_median")
b("01_introduction", -1, "( T^ * _ ECE", 0, A_TSS, "results.ferplus.T_star_ece", "2dp",
  ident="intro.tstar_ece_ferplus")
b("01_introduction", -1, "Jensen--Shannon divergence", 0, A_FJ, "T_star_jsd.T", "2dp",
  ident="intro.tstar_jsd_ferplus")
b("01_introduction", -1, "( 0.412 vs.", 0, A_FJ,
  "entropy_correlation.T_jsd.teacher_mean_entropy", "3dp", ident="intro.teacher_entropy_tjsd")
b("01_introduction", -1, "( 0.412 vs.", 1, A_FJ, "human_mean_entropy", "3dp",
  ident="intro.human_entropy")
b("01_introduction", -1, "reporting. Auditing a frozen corpus", 0, A_SG,
  "audit_deltas.b_best_minus_last.n", "int", ident="intro.audit_n_runs")
b("01_introduction", -1, "+0.77 pp on average", 0, A_SG,
  "audit_deltas.b_best_minus_last.d_acc.mean", "2dp", ident="intro.selection_inflation")
# CIFT YUVARLAMA VAKASI, birinci gecis -- kapandi (blok basligina bakiniz).
b("01_introduction", -1, "component +0.645 to +0.764", 0, A_SG,
  'per_k["50"].a2_pure_order_statistic.mean', "3dp", ident="intro.orderstat_k50")
b("01_introduction", -1, "component +0.645 to +0.764", 1, A_SG,
  'per_k["100"].a2_pure_order_statistic.mean', "3dp", ident="intro.orderstat_k100")
b("01_introduction", -1, "calibration error under over-confidence", 0, A_ASY,
  "summary.interpolated_only.absolute.min", "1dp", ident="intro.asymmetry_min")
b("01_introduction", -1, "calibration error under over-confidence", 1, A_ASY,
  "summary.interpolated_only.absolute.max", "1dp", ident="intro.asymmetry_max")
b("01_introduction", -1, "(The compression setting itself", 0, A_EFF,
  "compression.params_ratio", "1dp", ident="intro.compression_ratio")
b("01_introduction", -1, "retaining 97.96", 0, A_EFF, "headline.retention_pct_swa", "2dp",
  ident="intro.retention_swa")
b("01_introduction", -1, "asymmetry are post-hoc. (5)", 1, A_SG,
  "audit_deltas.b_best_minus_last.n", "int", ident="intro.audit_n_runs_2")

# Kol ICI dogruluk acikligi: iki nokta arasi FARK, tek alan degil -- turetilmis.
dv("intro.acc_band_stage1", "0.30", "diff",
   [op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "01_introduction", -1, "contrast stays within narrow bands", 0,
   note="stage1 kolunun @swa dogruluk acikligi: T*=1.3406 eksi T=1.70")
dv("intro.acc_band_vae9182", "0.51", "diff",
   [op(A_TDO, "arms.rafdb_vae9182.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_vae9182.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "01_introduction", -1, "supported 0.51 pp on its control", 0,
   note="kontrol kolunun @swa dogruluk acikligi")
dv("intro.acc_decline_ferplus", "0.49", "diff",
   [op(A_TDO, "arms.ferplus.points[0].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "01_introduction", -1, "supported 0.51 pp on its control", 1,
   note="FERPlus kolunda T=0.26 ile T=1.0 arasi @swa dogruluk farki")

INTRO_EX = [
    ("both pathologies:", 0, "criterion_constant", "T^*>1 esik tanimi, olcum degil"),
    ("( T^ * < 1 )", 0, "criterion_constant", "T^*<1 esik tanimi"),
    ("to correct every pre-declared", 0, "hyperparameter", "on-beyanli kalkis noktasi T=1"),
    ("student's calibration and a finer", 0, "hyperparameter", "ince izgaranin merkezi T=1"),
    ("2.04 on FERPlus", 1, "null_value", "bootstrap araliginin disladigi NULL deger 1"),
]
for _row, _idx, _cls, _why in INTRO_EX:
    ex("01_introduction", -1, _row, _idx, _cls, _why)

# --- §2 ilgili calismalar
b("02_related_work", -1, "1.8 -- 2.0 that under", 0, A_ASY,
  "summary.interpolated_only.absolute.min", "1dp", ident="related_work.asymmetry_min")
b("02_related_work", -1, "1.8 -- 2.0 that under", 1, A_ASY,
  "summary.interpolated_only.absolute.max", "1dp", ident="related_work.asymmetry_max")
b("02_related_work", -1, "T^ * _ ECE", 0, A_TSS, "results.ferplus.T_star_ece", "2dp",
  ident="related_work.ferplus_tstar_ece")
b("02_related_work", -1, "divergence from the votes", 0, A_JSD,
  'results["(a) all rows"].T_jsd', "2dp", ident="related_work.ferplus_tstar_jsd")
b("02_related_work", -1, "amount (", 0, A_SG,
  "audit_deltas.b_best_minus_last.d_acc.mean", "2dp", ident="related_work.selection_inflation")
# CIFT YUVARLAMA VAKASI, ikinci gecis -- 20 Agu aksami kapandi (blok basligina bakiniz).
b("02_related_work", -1, "amount (", 1, A_SG,
  'per_k["50"].a2_pure_order_statistic.mean', "3dp", ident="related_work.orderstat_k50")
b("02_related_work", -1, "amount (", 2, A_OST, 'results["100"].a2_raw.mean', "3dp",
  ident="related_work.orderstat_k100")

RELATED_EX = [
    ("temperature over", i, "citation",
     "alintilanan calismanin kendi sicaklik izgarasi (2/4/8/16/20/32/64) -- bizim olcumumuz degil")
    for i in range(7)
]
for _row, _idx, _cls, _why in RELATED_EX:
    ex("02_related_work", -1, _row, _idx, _cls, _why)

# --- §6 sonuc
CONCL_EX = [
    # 28 Agu: ayni alpha cumlesi §6'da IKI yerde geciyor -- govde ("peaking near ...
    # reversing by") ve kapanis ("the benefit peaks near ... reverses by"). Dort muafiyet.
    ("near = 0.5 and reversing", 0, "hyperparameter", "alpha=0.5, karisim agirligi"),
    ("near = 0.5 and reversing", 1, "hyperparameter", "alpha=0.9, karisim agirligi"),
    ("the benefit peaks near = 0.5", 0, "hyperparameter", "alpha=0.5, karisim agirligi"),
    ("the benefit peaks near = 0.5", 1, "hyperparameter", "alpha=0.9, karisim agirligi"),
    ("peak benefit. The = 0.3 used", 0, "hyperparameter", "kampanya boyunca kullanilan alpha=0.3"),
    ("(archived at https://doi.org/10.5281", 0, "doi",
     "Zenodo DOI onekinin sayisal parcasi (10.5281) -- tanimlayici, olcum degil"),
]
for _row, _idx, _cls, _why in CONCL_EX:
    ex("06_conclusion", -1, _row, _idx, _cls, _why)


# --- Okumanin isaretledigi dort sayi (N19, 20 Agu 2026) -----------------------------------
# ORTAK DERS: dordunun de sorusu "hangi PAYDA" idi. Bir oranin paydasi cumlede adlandirilmali
# (17 Agu kurali); burada alan yolu olarak da duruyor.

# (1) §3.5 — oy toplami 10'dan kucuk olan satirlarin orani. IKI FARKLI PAYDA:
#     %29,3 -> TUREV dosyasinin TAMAMI (uc fold, 31412 satir)
#     %37,3 -> YALNIZ dogrulama fold'u (3153 satir)
# Ikisi ayni cumlede yan yana duruyor ve ayni sayi degiller; ayni alana baglanamazlar.
# %29,3'un ureticisi 20 Agu'da yazildi (ferplus_abstention_entropy, `--` filtresiz sayim);
# N16'dan beri "ureticisi yok" diye kayitliydi.
b("03_methodology", -1, "( 29.3 % of all rows", 0, A_ABS, "share_below_ten_all_folds", "1dp",
  ident="methodology.votes_below_ten_all_folds")
dv("methodology.votes_below_ten_val", "37.3", "pct_of",
   [op(A_ABS, "rows_with_abstention"), op(A_ABS, "n_val")],
   "1dp", "03_methodology", -1, "( 29.3 % of all rows", 1,
   note="dogrulama fold'unda 10'a tamamlanmayan satir orani; payda n_val=3153")
dv("methodology.abstention_mass_val", "37.3", "pct_of",
   [op(A_ABS, "rows_with_abstention"), op(A_ABS, "n_val")],
   "1dp", "03_methodology", -1, "canonical file every row sums to exactly ten", 0,
   note="ayni cumlenin ikinci yarisi: kanonik dosyada unknown/NF'ye kutle koyan satirlar. "
        "Kanonik dosyada her satir tam 10'a topladigi icin bu kume 10'dan kucuk toplayan "
        "satirlarla BIREBIR ayni -- ayni alan, ama iddia farkli, o yuzden ayri beyan.")

# (2) §5 — ogrenci-tarafi TS ile ogretmen-tarafi T* kolunun JSD'si ve FARKI.
# BASILI 0.0041, YUVARLANMIS operandlardan 0.0042 cikar. Yani makale DOGRU yapmis: fark
# yuvarlanmamis alanlardan aliniyor. Defter de oyle hesaplar (operandlar tam duyarlikta).
b("05_results_discussion", -1, "lying entirely outside the same margin", 0, A_STS,
  "aggregate.jsd.student_ts[0]", "4dp", ident="results.jsd_student_ts")
b("05_results_discussion", -1, "lying entirely outside the same margin", 1, A_STS,
  "aggregate.jsd.tstar_arm[0]", "4dp", ident="results.jsd_tstar_arm")
dv("results.jsd_gap_student_ts", "0.0041", "diff",
   [op(A_STS, "aggregate.jsd.tstar_arm[0]"), op(A_STS, "aggregate.jsd.student_ts[0]")],
   "4dp", "05_results_discussion", -1, "student-scaled arm's JSD is lower by", 0,
   note="TAM DUYARLIKTA fark 0.004145559676890273 -> 0.0041. Basili operandlardan "
        "(0.0587-0.0545) 0.0042 cikar; makale yuvarlanmamis alanlardan hesaplamis.")

# (3) §5 — FERPlus best-swa ECE farki ve ONUN ECE SEVIYESINE ORANI, iki paydayla.
b("05_results_discussion", -1, "+0.0069 (SD", 0, A_SAI,
  'datasets["FERPlus"].contrasts["best-swa"].ece.mean', "4dp",
  ident="results.ferplus_best_swa_ece")
dv("results.ferplus_ece_share_low", "13", "pct_of",
   [op(A_SAI, 'datasets["FERPlus"].contrasts["best-swa"].ece.mean'),
    op(A_SAI, 'datasets["FERPlus"].contrasts["best-swa"].ece_scale_denominators["mean ECE @best"]')],
   "int", "05_results_discussion", -1, "0.020 ; 13 -- 15 % of the ECE level", 1,
   note="araligin ALT ucu; payda 'mean ECE @best' = 0.05435748884887785 -> %12,66 -> 13")
dv("results.ferplus_ece_share_high", "15", "pct_of",
   [op(A_SAI, 'datasets["FERPlus"].contrasts["best-swa"].ece.mean'),
    op(A_SAI, 'datasets["FERPlus"].contrasts["best-swa"].ece_scale_denominators["median ECE @swa"]')],
   "int", "05_results_discussion", -1, "0.020 ; 13 -- 15 % of the ECE level", 2,
   note="araligin UST ucu; payda 'median ECE @swa' = 0.045957979335884726 -> %14,97 -> 15. "
        "UCUNCU payda ('mean ECE @swa', %14,50) aralik ICINDE kaldigi icin ayrica basilmiyor. "
        "DIKKAT: §3'teki '13--14 times' BASKA BIR NICELIKTIR -- boyutsuz KAT (ece_removed_by_ts "
        "/ d_ece), yuzde degil; defterde `tstar_criterion_cost_min/max` olarak ayri kayitli. "
        "Resiprok da degiller (1/13.31 = %7,5), yani ayni ifadenin iki yazilisi diye okunamaz.")

# (4) §5 — iki optimumun goreli farki. YENI turetilmis nicelik (okuma turunda eklendi).
dv("results.tstar_gap_pct", "63", "pct_excess",
   [op(A_FJ, "T_star_jsd.T"), op(A_TSS, "results.ferplus.T_star_ece")],
   "int", "05_results_discussion", -1, "63 % in T", 0,
   note="PAYDA T*_ECE: (T*_JSD - T*_ECE) / T*_ECE = (0.74-0.45305)/0.45305 = %63,3. "
        "Ilk denemede `pct_drop` kullanildi (payda T*_JSD) ve 39 verdi; defter bunu "
        "derived_mismatch olarak dusurdu, formul duzeltildi. Iki payda arasindaki fark "
        "24 puan -- yani 'bir oranin paydasi cumlede adlanmali' kurali burada 24 puanlik "
        "bir hatayi engelledi.")


# --- §3 / §4 / §5 govde duzyazisi (N19, 20 Agu 2026) --------------------------------------
# 824 duzyazi jetonunun 765'i bu uc dosyada. Beyanlar birim birim uretildi ve HER BIRI defterde
# sayisal olarak dogrulaniyor: tutmayan bag rounding_mismatch / binding_matched_nothing /
# derived_mismatch verir. Muafiyetler mevcut siniflara dusuyor; iki yeni sinif onerildi
# (`scientific_notation`, `doi`) ve gerekceleri asagida her satirda yazili.

# --- 03_methodology
b("03_methodology", -1, "T = 0.5063 is the minimiser", 0, A_HGA,
  "grids.run.T_argmin", "4dp", ident="meth.ferplus_deployed_arm_is_argmin")
b("03_methodology", -1, "reduction of 0.1126", 0, A_HGA,
  "grids.run.headroom", "4dp", ident="meth.ferplus_run_grid_reduction")
b("03_methodology", -1, "reduction of 0.1126", 1, A_HGA,
  "grids.fine.grid.n", "int", ident="meth.ferplus_fine_grid_n")
b("03_methodology", -1, "reduction of 0.1126", 2, A_HGA,
  "grids.fine.grid.step", "2dp", ident="meth.ferplus_fine_grid_step")
b("03_methodology", -1, "T = 0.46 and reach", 0, A_HGA,
  "grids.fine.T_argmin", "2dp", ident="meth.ferplus_fine_argmin_T")
b("03_methodology", -1, "T = 0.46 and reach", 1, A_HGA,
  "grids.fine.headroom", "4dp", ident="meth.ferplus_fine_headroom")
b("03_methodology", -1, "the four teachers the two criteria differ", 0, A_TSS,
  "max_abs_dT", "3dp", ident="meth.max_criterion_dT")
b("03_methodology", -1, "and the ECE cost of fitting by NLL", 0, A_TSS,
  "max_d_ece", "4dp", ident="meth.max_criterion_cost")
b("03_methodology", -1, "it rather than smooth it over", 1, A_TSP,
  "half_fold_fits.stage1", "4dp", ident="meth.stage1_half_fold_fit")
b("03_methodology", -1, "fold which returns 1.3494", 0, A_TSS,
  "results.stage1.T_star_nll", "4dp", ident="meth.stage1_full_fold_fit")
b("03_methodology", -1, "SHA-sorted split) moves it", 0, "paper_tables/tstar_stability.json",
  "results.primary.absdiff_nll_A_B", "3dp", ident="meth.halfsplit_shift_rafdb_max")
b("03_methodology", -1, "teachers and 0.026 on FERPlus", 0, "paper_tables/tstar_stability.json",
  "results.ferplus.absdiff_nll_A_B", "3dp", ident="meth.halfsplit_shift_ferplus")
b("03_methodology", -1, "(MobileNetV2Plus 2.248", 1, A_EFF,
  "student.params_m", "3dp", ident="meth.student_params_m")
b("03_methodology", -1, "(MobileNetV2Plus 2.248", 2, A_EFF,
  "student.flops_g", "3dp", ident="meth.student_gmacs")
b("03_methodology", -1, "already well calibrated (VAE9182", 1, A_HR,
  "rafdb_teachers.vae9182.ece_T1", "4dp", ident="meth.control_teacher_ece_T1")
b("03_methodology", -1, "T^ * = 0.983 headroom", 0, A_TSS,
  "results.vae9182.T_star_nll", "3dp", ident="meth.control_tstar_nll")
b("03_methodology", -1, "T^ * = 0.983 headroom", 1, A_BOOT,
  "results.vae9182.point.headroom_eq8", "4dp", ident="meth.control_headroom_point")
b("03_methodology", -1, "of [+0.0000", 0, A_BOOT,
  "results.vae9182.ci95.headroom_eq8[0]", "4dp", ident="meth.control_headroom_ci_lo")
b("03_methodology", -1, "of [+0.0000", 1, A_BOOT,
  "results.vae9182.ci95.headroom_eq8[1]", "4dp", ident="meth.control_headroom_ci_hi")
b("03_methodology", -1, "of magnitude below the other two teachers", 0, A_BOOT,
  "results.stage1.point.headroom_eq8", "4dp", ident="meth.stage1_headroom_point_boot")
b("03_methodology", -1, "[+0.0151", 0, A_BOOT,
  "results.stage1.ci95.headroom_eq8[0]", "4dp", ident="meth.stage1_headroom_ci_lo")
b("03_methodology", -1, "[+0.0151", 1, A_BOOT,
  "results.stage1.ci95.headroom_eq8[1]", "4dp", ident="meth.stage1_headroom_ci_hi")
b("03_methodology", -1, "[+0.0151", 2, A_BOOT,
  "results.primary.point.headroom_eq8", "4dp", ident="meth.primary_headroom_point_boot")
b("03_methodology", -1, "[+0.0151", 3, A_BOOT,
  "results.primary.ci95.headroom_eq8[0]", "4dp", ident="meth.primary_headroom_ci_lo")
b("03_methodology", -1, "[+0.0151", 4, A_BOOT,
  "results.primary.ci95.headroom_eq8[1]", "4dp", ident="meth.primary_headroom_ci_hi")
b("03_methodology", -1, "over-confident --- sMG>0", 1, A_TSS,
  "results.stage1.T_star_nll", "3dp", ident="meth.stage1_tstar_nll_3dp")
b("03_methodology", -1, "dose grid as T = 1.34", 1, A_HR,
  "rafdb_teachers.stage1.headroom_eq8", "3dp", ident="meth.stage1_headroom_eq8_review")
b("03_methodology", -1, "teacher is under-confident", 0, A_TDO,
  "arms.ferplus.points[3].signed_gap", "3dp", ident="meth.ferplus_signed_gap_T1")
b("03_methodology", -1, "teacher is under-confident", 1, A_TSS,
  "results.ferplus.T_star_nll", "2dp", ident="meth.ferplus_tstar_nll_2dp")
b("03_methodology", -1, "headroom 0.113 on the grid", 0, A_HGA,
  "grids.run.headroom", "3dp", ident="meth.ferplus_run_headroom_3dp")
b("03_methodology", -1, "headroom 0.113 on the grid", 1, A_HGA,
  "grids.fine.grid.step", "2dp", ident="meth.ferplus_fine_step_2")
b("03_methodology", -1, "refinement would reach 0.120", 0, A_HGA,
  "grids.fine.headroom", "3dp", ident="meth.ferplus_fine_headroom_3dp")
b("03_methodology", -1, "coincide: T^ * _ ECE", 0, A_TSS,
  "results.ferplus.T_star_ece", "3dp", ident="meth.ferplus_tstar_ece_3dp")
b("03_methodology", -1, "coincide: T^ * _ ECE", 1, A_HGA,
  "ferplus_T_star_ece.fine_grid_argmin", "2dp", ident="meth.ferplus_tstar_ece_grid")
b("03_methodology", -1, "log-likelihood is T^ * _ NLL", 0, A_TSS,
  "results.ferplus.T_star_nll", "3dp", ident="meth.ferplus_tstar_nll_3dp")
b("03_methodology", -1, "T^ * _ JSD = 0.74", 0, A_FJ,
  "T_star_jsd.T", "2dp", ident="meth.ferplus_tstar_jsd")
b("03_methodology", -1, "T^ * _ JSD = 0.74", 1, A_FJ,
  "T_star_jsd.T", "2dp", ident="meth.ferplus_tstar_jsd_2")
b("03_methodology", -1, "predictive entropy ( 0.412", 0, A_FJ,
  "entropy_correlation.T_jsd.teacher_mean_entropy", "3dp", ident="meth.teacher_entropy_at_tjsd")
b("03_methodology", -1, "human-vote entropy ( 0.440", 0, A_FJ,
  "human_mean_entropy", "3dp", ident="meth.human_mean_entropy")
b("03_methodology", -1, "per-sample entropy correlation", 0, A_FJ,
  "entropy_correlation.T1.pearson", "3dp", ident="meth.entropy_pearson_T1")
b("03_methodology", -1, "0.711 at T = 0.74", 0, A_FJ,
  "entropy_correlation.T_jsd.pearson", "3dp", ident="meth.entropy_pearson_Tjsd")
b("03_methodology", -1, "0.711 at T = 0.74", 1, A_FJ,
  "T_star_jsd.T", "2dp", ident="meth.ferplus_tstar_jsd_3")
dv("meth.argmin_cells_agreeing", "20", "sum",
   [op(A_ROB, "series[\"RAF-DB stage1\"]._consensus_metrics_agreeing"),
    op(A_ROB, "series[\"RAF-DB vae9182\"]._consensus_metrics_agreeing"),
    op(A_ROB, "series[\"FERPlus\"]._consensus_metrics_agreeing")],
   "int", "03_methodology", -1, "agreeing in 20 of 21 cells", 0)
dv("meth.argmin_cells_total", "21", "sum",
   [op(A_ROB, "series[\"RAF-DB stage1\"]._n_metrics"),
    op(A_ROB, "series[\"RAF-DB vae9182\"]._n_metrics"),
    op(A_ROB, "series[\"FERPlus\"]._n_metrics")],
   "int", "03_methodology", -1, "agreeing in 20 of 21 cells", 1)
dv("meth.tstar_criterion_cost_min", "13", "ratio",
   [op(A_TSS, "results.ferplus.ece_removed_by_ts"),
    op(A_TSS, "results.ferplus.d_ece")],
   "int", "03_methodology", -1, "and the ECE cost of fitting by NLL", 1)
dv("meth.tstar_criterion_cost_max", "14", "ratio",
   [op(A_TSS, "results.stage1.ece_removed_by_ts"),
    op(A_TSS, "results.stage1.d_ece")],
   "int", "03_methodology", -1, "and the ECE cost of fitting by NLL", 2)
# (cift beyan: `meth.ferplus_abstention_pct_val` ayni jetonu elle yazilan beyanla paylasiyordu; dusuruldu)
# (cift beyan: `meth.ferplus_abstention_pct_val_2` ayni jetonu elle yazilan beyanla paylasiyordu; dusuruldu)
dv("meth.acc_band_stage1", "0.30", "diff",
   [op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "03_methodology", -1, "narrow band ( 0.30", 0)
dv("meth.acc_band_vae9182", "0.51", "diff",
   [op(A_TDO, "arms.rafdb_vae9182.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_vae9182.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "03_methodology", -1, "narrow band ( 0.30", 1)
dv("meth.acc_trend_ferplus", "0.49", "diff",
   [op(A_TDO, "arms.ferplus.points[0].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "03_methodology", -1, "teachers and a monotone 0.49", 0)
EX_03 = [
    ("distillation. In the dose--response arms", 0, "hyperparameter",
     "KD sicakligi tau=6.0, her kolda sabit tutulan tasarim ayari -- olcum degil"),
    ("_ j=1 ^ C (z_j^ M", 0, "equation_constant",
     "Eq.1 softmax paydasindaki toplam alt siniri j=1 -- matematiksel gosterim. YENI SINIF ONERISI: `equation_constant` (toplam/carpim sinirlari, usler, 1/2"),
    (";+ ; (1- ) ^ 2", 0, "equation_constant",
     "(1-alpha) ifadesindeki 1 -- formul gosterimi. DIKKAT: bu tek beyan IKI fiziksel satiri (47 ve 119, Eq.2 ve Eq.4) kapsar; tarayici ikisine de ayni anah"),
    (";+ ; (1- ) ^ 2", 1, "equation_constant",
     "tau^2 carpanindaki us -- formul gosterimi. Ayni sekilde satir 47 ve 119'u birlikte kapsar"),
    (";+ ; (1- ) ^ 2", 0, "equation_constant",
     "IKINCI GECIS (satir 119, Eq.4): satir 47 ile AYNI tarayici anahtarini paylasir, tek ex() beyani ikisini de kapatir. Bu satir yalnizca 147 jetonun sayi"),
    (";+ ; (1- ) ^ 2", 1, "equation_constant",
     "IKINCI GECIS (satir 119, Eq.4): yukaridakiyle ayni -- deftere ikinci kez yazilmasi gerekmez, yalnizca jeton sayimi icin"),
    ("where = 0.3 in every run", 0, "hyperparameter",
     "gorev terimi agirligi alpha=0.3"),
    ("objective is 0.3", 0, "hyperparameter",
     "amac fonksiyonunda acikca yazilan alpha=0.3"),
    ("objective is 0.3", 1, "hyperparameter",
     "KD terimi agirligi 1-alpha=0.7"),
    ("reduction=\"batchmean\")", 0, "equation_constant",
     "tau^2 carpanindaki us"),
    ("deliberately kept at", 0, "equation_constant",
     "tau^2 carpanindaki us"),
    ("T_i^ 2 only in the", 0, "equation_constant",
     "T_i^2 carpanindaki us"),
    ("_ VICH = 10^", 0, "hyperparameter",
     "beta_VICH = 10^-4 yardimci KL agirligi (mantis 10)"),
    ("_ VICH = 10^", 1, "hyperparameter",
     "beta_VICH = 10^-4 (us -4)"),
    ("_ j=1 ^ C (z_j^ T", 0, "equation_constant",
     "Eq.3 paydasindaki toplam alt siniri j=1"),
    ("= 6 all soft targets", 0, "hyperparameter",
     "tau=6 -- sabit KD sicakligi"),
    ("temperature manipulation: applying a pre-scaling", 0, "equation_constant",
     "T_0 sembolunun alt indisi -- gosterim, olcum degil"),
    ("conducted at a fixed T_0", 0, "equation_constant",
     "T_0 sembolunun alt indisi"),
    ("equal-width top-1 confidence ECE", 0, "metric_name_digits",
     "'top-1' olcut adindaki basamak (tirenin isaret gibi okunmasi yuzunden -1 basiliyor). YENI SINIF ONERISI: `metric_name_digits` -- top-1/top-2 gibi olcu"),
    ("equal-width top-1 confidence ECE", 1, "benchmark_protocol",
     "ECE kestiricisinin kutu sayisi B=15 -- olcum protokolu (S2'de ayni sayi ayni sinifla muaf)"),
    ("ECE ;= ; _ b=1", 0, "equation_constant",
     "Eq.5'teki toplam alt siniri b=1"),
    ("where B_b is the set of samples", 0, "metric_name_digits",
     "'top-1 confidence' olcut adindaki basamak"),
    ("agreeing in 20 of 21 cells", 2, "table_reference",
     "'Supplementary Section S2' capraz atfindaki basamak"),
    ("where conf is the mean top-1", 0, "metric_name_digits",
     "'top-1 confidence' olcut adindaki basamak"),
    ("- 1 N _ i=1 ^ N", 0, "equation_constant",
     "Eq.7'deki 1/N katsayisinin payi"),
    ("- 1 N _ i=1 ^ N", 1, "equation_constant",
     "Eq.7'deki toplam alt siniri i=1"),
    ("method tolerance 10^", 0, "hyperparameter",
     "Brent minimizasyonunun toleransi 10^-5 (mantis) -- optimizasyon ayari"),
    ("method tolerance 10^", 1, "hyperparameter",
     "tolerans 10^-5 (us)"),
    ("training. Bounds are [0.5", 0, "hyperparameter",
     "RAF-DB TS fit araliginin alt siniri"),
    ("training. Bounds are [0.5", 1, "hyperparameter",
     "RAF-DB TS fit araliginin ust siniri"),
    ("training. Bounds are [0.5", 2, "hyperparameter",
     "FERPlus TS fit araliginin alt siniri (log-uzayda)"),
    ("training. Bounds are [0.5", 3, "hyperparameter",
     "FERPlus TS fit araliginin ust siniri"),
    ("scaling removes ECE at all", 0, "table_reference",
     "'Supplementary Table S2' capraz atfindaki basamak"),
    ("Supplementary Section S2. The vote-alignment", 0, "table_reference",
     "'Supplementary Section S2' capraz atfindaki basamak"),
    ("it rather than smooth it over", 0, "teacher_name_digits",
     "'Stage1' ogretmen adinin icindeki basamak"),
    ("3 10^ -3 . The choice of fitting sample", 0, "stated_bound",
     "'less than 3x10^-3' -- BEYAN EDILEN TAVAN, alan degeri degil. Altta yatan olcum tstar_stability.results.*.cross_ece_penalty maksimumudur (FERPlus 0.00"),
    ("3 10^ -3 . The choice of fitting sample", 1, "stated_bound",
     "Ayni tavanin bilimsel gosterimindeki taban (10)"),
    ("3 10^ -3 . The choice of fitting sample", 2, "stated_bound",
     "Ayni tavanin bilimsel gosterimindeki us (-3)"),
    ("ECE(T = 1) ;- ;", 0, "hyperparameter",
     "Eq.8'deki referans nokta T=1 (olceklenmemis ogretmen). S2'de ayni jeton ayni sinifla muaf: 'Eq.8 tanimindaki T=1'"),
    ("finer-resolution check appears", 0, "table_reference",
     "'Supplementary Section S2' capraz atfindaki basamak"),
    ("top-1 predictions and accuracy causally", 0, "metric_name_digits",
     "'top-1 predictions' olcut adindaki basamak"),
    ("(MobileNetV2Plus 2.248", 0, "name_digits",
     "'MobileNetV2Plus' mimari adinin icindeki basamak. YENI SINIF ONERISI: `name_digits` -- teacher_name_digits'in ogretmen-disi karsiligi (ogrenci mimaris"),
    ("224 224 ) training recipe", 0, "architecture_dim",
     "girdi cozunurlugu 224x224 (yukseklik)"),
    ("224 224 ) training recipe", 1, "architecture_dim",
     "girdi cozunurlugu 224x224 (genislik)"),
    ("Each seed s 42 1 43", 0, "hyperparameter",
     "tohum kimligi 42"),
    ("Each seed s 42 1 43", 1, "hyperparameter",
     "tohum kimligi 1"),
    ("Each seed s 42 1 43", 2, "hyperparameter",
     "tohum kimligi 43"),
    ("(i) the natural teacher", 0, "hyperparameter",
     "izgaranin dogal kolu T=1 (on-olcekleme yok)"),
    ("already well calibrated (VAE9182", 0, "teacher_name_digits",
     "'VAE9182' ogretmen adinin icindeki basamaklar"),
    ("T^ * = 0.983 headroom", 2, "benchmark_protocol",
     "bootstrap guven araliginin duzeyi %95 -- cikarim protokolu, olcum degil"),
    ("should sit near T = 1", 0, "hyperparameter",
     "on-beyanli tahminin referans noktasi T=1"),
    ("should sit near T = 1", 1, "hyperparameter",
     "dose izgarasinin T=1.34 kolu -- kol ayari"),
    ("falsified by a resolvable interior optimum", 0, "hyperparameter",
     "yanlislama olcutundeki referans nokta T=1"),
    ("central to the experimental design", 0, "teacher_name_digits",
     "'Stage1' ogretmen adinin icindeki basamak"),
    ("over-confident --- sMG>0", 0, "null_value",
     "sMG>0 esiginin NULL degeri (asiri-guven yonunun tanimi) -- olcum degil. Sinif defterde zaten kullanimda (intro'da 'bootstrap araliginin disladigi NULL"),
    ("dose grid as T = 1.34", 0, "hyperparameter",
     "dose izgarasinda fiilen kosulan kolun etiketi T=1.34"),
    ("(deployed exactly as T = 0.5063", 0, "hyperparameter",
     "FERPlus kolunda DAGITILAN on-olcekleme ayari (fitin 4 basamaga kirpilmisi). tstar_sensitivity.results.ferplus.deployed_T ELLE YAZILMIS bir BEYAN oldug"),
    ("teacher (G2G) and by the temperature", 0, "name_digits",
     "'G2G' mekanizma adinin icindeki basamak"),
    ("Supplementary Section S1.", 0, "table_reference",
     "'Supplementary Section S1' capraz atfindaki basamak"),
    (";+ ; (1- _i)", 0, "equation_constant",
     "Eq.9'daki (1-alpha_i) ifadesinin 1'i"),
    ("with constants in Supplementary Section S1;", 0, "table_reference",
     "'Supplementary Section S1' capraz atfindaki basamak"),
    ("^ 2 -scaled KL for sample", 0, "equation_constant",
     "tau^2 carpanindaki us"),
    ("mean logit variance target-class", 0, "metric_name_digits",
     "'top-2 logit variance' belirsizlik sinyalinin adindaki basamak"),
    ("Class-space Gaussian matching", 0, "name_digits",
     "alt bolum basligindaki 'G2G' adinin basamagi (S1'de ayni jeton 'G2G basligindaki 2' gerekcesiyle muaf)"),
    ("--- the head's C -dimensional", 0, "equation_constant",
     "(mu, log sigma^2) gosterimindeki us"),
    ("w = 0.1 ). The design is ours", 0, "hyperparameter",
     "G2G ek KL teriminin agirligi w=0.1"),
    ("L _ G2G ;= ; L", 0, "name_digits",
     "Eq.10'daki 'G2G' alt simgesinin basamagi"),
    ("softmax(z^ T _ i ) at T = 1", 0, "hyperparameter",
     "entropinin okundugu olceklenmemis kol T=1 (dairesellikten kacinmak icin)"),
    ("T_i ;= ; [ 1 +", 0, "equation_constant",
     "Eq.11'deki 1 + gamma_T(...) ifadesinin 1'i"),
    ("T_i [1.0 ;2 ]", 0, "hyperparameter",
     "per-sample sicakligin kelepce alt siniri 1.0"),
    ("T_i [1.0 ;2 ]", 1, "hyperparameter",
     "kelepce ust siniri 2tau'nun katsayisi"),
    ("mean over the current mini-batch", 0, "hyperparameter",
     "adaptif sicaklik modulasyon gucu gamma_T=0.5"),
    ("Three of the five mechanisms", 0, "name_digits",
     "'G2G' mekanizma adinin icindeki basamak"),
    ("= 0.05 ) initial learning rate", 0, "hyperparameter",
     "SAM yaricapi rho=0.05"),
    ("= 0.05 ) initial learning rate", 1, "hyperparameter",
     "baslangic ogrenme orani 9x10^-6 (mantis)"),
    ("= 0.05 ) initial learning rate", 2, "hyperparameter",
     "baslangic ogrenme orani 9x10^-6 (taban)"),
    ("= 0.05 ) initial learning rate", 3, "hyperparameter",
     "baslangic ogrenme orani 9x10^-6 (us)"),
    ("schedule ( = 0.98 )", 0, "hyperparameter",
     "ustel ogrenme orani cizelgesinin gamma=0.98'i"),
    ("not a differentiating factor", 0, "teacher_name_digits",
     "'Stage1' ogretmen adinin icindeki basamak"),
    ("( 10^ -4 vs. 10^ -3 )", 0, "hyperparameter",
     "beta_CE-KLD = 10^-4 (taban)"),
    ("( 10^ -4 vs. 10^ -3 )", 1, "hyperparameter",
     "beta_CE-KLD = 10^-4 (us)"),
    ("( 10^ -4 vs. 10^ -3 )", 2, "hyperparameter",
     "beta_CE-KLD = 10^-3 (taban)"),
    ("( 10^ -4 vs. 10^ -3 )", 3, "hyperparameter",
     "beta_CE-KLD = 10^-3 (us)"),
    ("( 10^ -4 vs. 10^ -3 )", 4, "hyperparameter",
     "egitim uzunlugu 200 epok"),
    ("( 10^ -4 vs. 10^ -3 )", 5, "hyperparameter",
     "egitim uzunlugu 300 epok"),
    ("VAE9182 additionally uses a VAE head", 0, "teacher_name_digits",
     "'VAE9182' ogretmen adinin icindeki basamaklar"),
    ("distribution p^ human", 0, "equation_constant",
     "olasilik simpleksi Delta^{C-1}'in boyut gosterimi"),
    ("probability simplex over C = 8", 0, "architecture_dim",
     "FERPlus sinif sayisi C=8 (cikti boyutu)"),
    (";= ; 1 2 KL(p^ T", 0, "equation_constant",
     "Eq.12'deki 1/2 katsayisinin payi"),
    (";= ; 1 2 KL(p^ T", 1, "equation_constant",
     "Eq.12'deki 1/2 katsayisinin paydasi"),
    (";+ ; 1 2 KL(p^ human", 0, "equation_constant",
     "Eq.12'nin ikinci teriminde 1/2 katsayisinin payi"),
    (";+ ; 1 2 KL(p^ human", 1, "equation_constant",
     "Eq.12'nin ikinci teriminde 1/2 katsayisinin paydasi"),
    ("m = 1 2 (p^ T", 0, "equation_constant",
     "karisim dagilimi m = 1/2(...) katsayisinin payi"),
    ("m = 1 2 (p^ T", 1, "equation_constant",
     "karisim dagilimi m = 1/2(...) katsayisinin paydasi"),
    ("per-sample entropy correlation", 1, "hyperparameter",
     "korelasyonun olculdugu olceklenmemis kol T=1 -- kol etiketi"),
]
for _row, _idx, _cls, _why in EX_03:
    ex("03_methodology", -1, _row, _idx, _cls, _why)

# --- 04_experiments
b("04_experiments", -1, "All teachers are POSTER", 0, A_EFF,
  "teacher.params_m", "1dp", ident="s4.arch.teacher_params_m")
b("04_experiments", -1, "parameters 8.48 GMACs", 0, A_EFF,
  "teacher.flops_g", "2dp", ident="s4.arch.teacher_gmacs")
b("04_experiments", -1, "(Section ). The student totals", 0, A_EFF,
  "student.params_m", "3dp", ident="s4.arch.student_params_m")
b("04_experiments", -1, "parameters and 0.329 GMACs", 0, A_EFF,
  "student.flops_g", "3dp", ident="s4.arch.student_gmacs")
b("04_experiments", -1, "( 8.8 MB on disk)", 0, A_EFF,
  "student.size_mb", "1dp", ident="s4.arch.student_size_mb")
b("04_experiments", -1, "diagnostics over the audit's frozen", 0, "paper_tables/audit_population.json",
  "n_total", "int", ident="s4.audit.inclusion_n")
# 22 Agu 2026 (defter final2): SS4.4'un secim-siskinligi pasaji makaleden CIKTI (C koprusu);
# sayilarin kalan kopyalari SS5.9 + tab_selection_audit + ozet. Dusen 16 bag: ost.k50/k100
# mean/sd, audit best-last acc/ece, best-swa, ferplus best-last, growth 116/125/131/span.
# 116/125/131/0.02 SS5.9'da YENIDEN baglandi (asagida, N20 blogu); digerleri zaten SS5 /
# tablo kopyalarinda bagliydi. Kayit: bu turun raporu + commit gecmisi.
b("04_experiments", -1, "3 % -- 19 %", 0, A_CSM,
  "mde_ece_swa_pct_min", "int", ident="s4.crit.mde_pct_min")
b("04_experiments", -1, "3 % -- 19 %", 1, A_CSM,
  "mde_ece_swa_pct_max", "int", ident="s4.crit.mde_pct_max")
b("04_experiments", -1, "The student (MobileNetV2Plus) has", 1, A_EFF,
  "student.params_m", "3dp", ident="s4.eff.student_params_m")
b("04_experiments", -1, "0.329 GMACs at 224", 0, A_EFF,
  "student.flops_g", "3dp", ident="s4.eff.student_gmacs")
b("04_experiments", -1, "representing 25.9", 0, A_EFF,
  "compression.params_ratio", "1dp", ident="s4.eff.ratio_params")
b("04_experiments", -1, "representing 25.9", 1, A_EFF,
  "compression.flops_ratio", "1dp", ident="s4.eff.ratio_flops")
b("04_experiments", -1, "FLOPs and 62.9", 0, A_EFF,
  "compression.size_ratio", "1dp", ident="s4.eff.ratio_size")
b("04_experiments", -1, "retaining 97.96", 0, A_EFF,
  "headline.retention_pct_swa", "2dp", ident="s4.eff.retention_swa")
b("04_experiments", -1, "we report as primary ( 98.32", 0, A_EFF,
  "headline.retention_pct_best", "2dp", ident="s4.eff.retention_best")
# 22 Agu (defter final2): fp32 hizlanma sonuclari SS4'ten cikti; tek kopya artik SS5.9'da
# ve orada bagli (res.speedup_*). Dort SS4 bagi dustu.
EX_04 = [
    ("FERPlus relabels FER2013", 0, "dataset_name_digits",
     "FER2013 veri kumesi adindaki yil basamaklari; olcum degil (YENI SINIF onerisi)"),
    # 21 Agu 2026 (jeton final): "The canonical release lists 28,709/3,589/..." cumlesi
    # makaleden CIKTI -- yeni cumle kanonik yayini degil BIZIM kopyamizin olcumunu soyluyor
    # ("Our copy of the label release measures 28,559/3,579/3,573") ve o sayilar artik
    # citation degil OLCUM: N19d blogunda A_SPL.unfiltered_by_fold alanlarina BAGLI. Dusen
    # jetonlar (28,709 / 3,589) N19c raporunda ve commit gecmisinde kayitli.
    ("parameters 8.48 GMACs", 1, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("parameters 8.48 GMACs", 2, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("parameters 8.48 GMACs", 3, "architecture_dim",
     "68 yuz noktasi -- POSTER++ mimarisinin landmark sayisi"),
    ("(MobileFaceNet IR50)", 0, "architecture_dim",
     "IR50 omurga adindaki basamak (50 katman); olcum degil"),
    ("The student is a MobileNetV2", 0, "architecture_dim",
     "MobileNetV2 adindaki surum basamagi"),
    ("The student is a MobileNetV2", 1, "architecture_dim",
     "genislik carpani (width multiplier) 1.0"),
    ("linear layers producing", 0, "notation_digits",
     "log sigma^2 gosterimindeki ustel basamak; matematiksel notasyon, olcum degil (YENI SINIF onerisi)"),
    ("over the classes (embedding size", 0, "architecture_dim",
     "gomme boyutu 768"),
    ("over the classes (embedding size", 1, "notation_digits",
     "log sigma^2 gosterimindeki ustel basamak"),
    ("at -5 clamped", 0, "hyperparameter",
     "log sigma^2 bias baslatma degeri -5"),
    ("at -5 clamped", 1, "hyperparameter",
     "kirpma araligi alt ucu -10"),
    ("at -5 clamped", 2, "hyperparameter",
     "kirpma araligi ust ucu 10"),
    ("parameters and 0.329 GMACs", 1, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("parameters and 0.329 GMACs", 2, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("pre-trained MobileNetV2 weights", 0, "architecture_dim",
     "MobileNetV2 adindaki surum basamagi"),
    ("3 10^ -4 weight decay", 0, "hyperparameter",
     "ogrenme orani 3e-4 (mantis)"),
    ("3 10^ -4 weight decay", 1, "hyperparameter",
     "ogrenme orani 3e-4 (taban 10)"),
    ("3 10^ -4 weight decay", 2, "hyperparameter",
     "ogrenme orani 3e-4 (ustel -4)"),
    ("3 10^ -4 weight decay", 3, "hyperparameter",
     "agirlik sonumlemesi 1e-4 (taban 10)"),
    ("3 10^ -4 weight decay", 4, "hyperparameter",
     "agirlik sonumlemesi 1e-4 (ustel -4)"),
    ("annealing with warm restarts", 0, "hyperparameter",
     "T_0 alt indisi (cizelge parametresinin adi)"),
    ("annealing with warm restarts", 1, "hyperparameter",
     "T_0=10 ilk devir uzunlugu"),
    ("annealing with warm restarts", 2, "hyperparameter",
     "T_mult=2 devir carpani"),
    ("_ = 10^ -6 ) batch size", 0, "hyperparameter",
     "eta_min=1e-6 (taban 10)"),
    ("_ = 10^ -6 ) batch size", 1, "hyperparameter",
     "eta_min=1e-6 (ustel -6)"),
    ("_ = 10^ -6 ) batch size", 2, "hyperparameter",
     "yigin boyutu 64"),
    ("no gradient clipping input resolution", 0, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("no gradient clipping input resolution", 1, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("no gradient clipping input resolution", 2, "hyperparameter",
     "damitma sicakligi tau=6"),
    ("= 0.3 _ VICH", 0, "hyperparameter",
     "alpha=0.3 sert etiket agirligi"),
    ("= 0.3 _ VICH", 1, "hyperparameter",
     "beta_VICH=1e-4 (taban 10)"),
    ("= 0.3 _ VICH", 2, "hyperparameter",
     "beta_VICH=1e-4 (ustel -4)"),
    ("_ mix = 0.1", 0, "hyperparameter",
     "mixup alpha_mix=0.1"),
    ("images. They differ as follows", 0, "hyperparameter",
     "RAF-DB egitim suresi 400 epoch"),
    ("from epoch 200 ) with label smoothing", 0, "hyperparameter",
     "SWA baslangic epoch'u 200"),
    ("0.1 and effective-number", 0, "hyperparameter",
     "etiket yumusatma 0.1"),
    ("class weighting ( = 0.9999", 0, "hyperparameter",
     "etkin-sayi sinif agirliklandirma beta=0.9999"),
    ("FERPlus trains for 200 epochs", 0, "hyperparameter",
     "FERPlus egitim suresi 200 epoch"),
    ("(SWA from epoch 100 )", 0, "hyperparameter",
     "FERPlus SWA baslangic epoch'u 100"),
    ("to 10^ -4 over ten epochs", 0, "hyperparameter",
     "SWALR hedef ogrenme orani 1e-4 (taban 10)"),
    ("to 10^ -4 over ten epochs", 1, "hyperparameter",
     "SWALR hedef ogrenme orani 1e-4 (ustel -4)"),
    ("RAF-DB: resize to 224", 0, "architecture_dim",
     "yeniden boyutlandirma 224x224"),
    ("RAF-DB: resize to 224", 1, "architecture_dim",
     "yeniden boyutlandirma 224x224"),
    ("RAF-DB: resize to 224", 2, "hyperparameter",
     "RandAugment islem sayisi 2"),
    ("RAF-DB: resize to 224", 3, "hyperparameter",
     "RandAugment buyuklugu 7"),
    ("erasing ( 0.1 )", 0, "hyperparameter",
     "rastgele silme olasiligi p=0.1"),
    ("( 0.3/0.3/0.2 hue", 0, "hyperparameter",
     "renk sarsintisi parlaklik 0.3"),
    ("( 0.3/0.3/0.2 hue", 1, "hyperparameter",
     "renk sarsintisi karsitlik 0.3"),
    ("( 0.3/0.3/0.2 hue", 2, "hyperparameter",
     "renk sarsintisi doygunluk 0.2"),
    ("( 0.3/0.3/0.2 hue", 3, "hyperparameter",
     "renk sarsintisi ton 0.05"),
    ("( 0.3/0.3/0.2 hue", 4, "hyperparameter",
     "uygulama olasiligi 0.5"),
    ("(RAF-DB: epochs 200--400", 0, "hyperparameter",
     "SWA penceresi RAF-DB 200--400 (alt uc)"),
    ("(RAF-DB: epochs 200--400", 1, "hyperparameter",
     "SWA penceresi RAF-DB 200--400 (ust uc)"),
    ("(RAF-DB: epochs 200--400", 2, "hyperparameter",
     "SWA penceresi FERPlus 100--200 (alt uc)"),
    ("(RAF-DB: epochs 200--400", 3, "hyperparameter",
     "SWA penceresi FERPlus 100--200 (ust uc)"),
    # 22 Agu: K50/K100 pencere sabitleri SS4'ten cikti (SS5.9 kopyalari zaten muaf).
    ("applied to the six selected contrasts", 0, "table_reference",
     "Supplementary Table S4 capraz referansi"),
    ("natural ( T = 1 )", 0, "hyperparameter",
     "dogal kosul sicakligi T=1"),
    ("With only n = 3 seeds", 0, "sample_size",
     "tohum sayisi n=3"),
    ("Supplementary Table S4 and at n = 3", 0, "table_reference",
     "Supplementary Table S4 capraz referansi"),
    ("Supplementary Table S4 and at n = 3", 1, "sample_size",
     "tohum sayisi n=3"),
    ("fires at 2 _ control", 0, "criterion_constant",
     "olcutun esigi 2 sigma_control; esik tanimi"),
    ("Supplementary Tables S8 and S9", 0, "table_reference",
     "Supplementary Table S8 capraz referansi"),
    ("Supplementary Tables S8 and S9", 1, "table_reference",
     "Supplementary Table S9 capraz referansi"),
    ("elements fixed only post hoc", 0, "date",
     "Holm ailesinin sabitlendigi tarih (1 Agustos)"),
    ("table-wide screening criterion (5 August)", 0, "date",
     "tablo-genisi tarama olcutunun sabitlendigi tarih (5 Agustos)"),
    ("thirteen predictions frozen between", 0, "date",
     "dondurma penceresi baslangic gunu (14 Temmuz)"),
    ("thirteen predictions frozen between", 1, "date",
     "dondurma penceresi bitis gunu (31 Temmuz)"),
    ("thirteen predictions frozen between", 2, "date",
     "yil 2026"),
    # 21 Agu 2026 (jeton final): '18 s to 13 h.' muafiyet cifti KALDIRILDI. Iki sebep:
    # (1) capa dusen sayiyi (13) iceriyordu -- CAPA KURALI'nin muafiyet tarafindaki ikinci
    # vakasi; (2) gerekcesi "yapilandirilmis artefakti yok" idi ve artik VAR:
    # `prereg_lead_audit.py` donmus kayittan lead'leri alan olarak yaziyor. 18 ve 12 artik
    # MUAF degil BAGLI (N19d blogu). Basili 13, A8'in 12.954 saatinin yari-yukari
    # yuvarlanmis haliydi; Lead bir alt-sinir-oncesi iddiasi oldugu icin dogrusu taban: 12.
    ("completion. Supplementary Table S11", 0, "table_reference",
     "Supplementary Table S11 capraz referansi"),
    ("declaration (Supplementary Section S2)", 0, "table_reference",
     "Supplementary Section S2 capraz referansi (bolum referansi; istenirse yeni sinif 'section_reference')"),
    ("dataset SHA-256 checksums", 0, "algorithm_name_digits",
     "SHA-256 ozet algoritmasinin adindaki basamak; olcum degil (YENI SINIF onerisi)"),
    # Capa 21 Agu 2026'da SAYIDAN ARINDIRILDI ("Of the 90 runs in that window" -> "Of the"):
    # eski hali bagli sayiyi (90) iceriyordu, yani CAPA KURALI'nin ihlaliydi. "Of the" bu
    # bolumde tek satira uyuyor (olculdu), dolayisiyla kisaltmak belirsizlik yaratmiyor.
    ("Of the", 1, "date",
     "pencere baslangic gunu (17 Haziran)"),
    ("Of the", 2, "date",
     "pencere bitis gunu (24 Temmuz)"),
    ("Of the", 3, "date",
     "yil 2026"),
    ("The student (MobileNetV2Plus) has", 0, "architecture_dim",
     "MobileNetV2Plus adindaki surum basamagi"),
    ("0.329 GMACs at 224", 1, "architecture_dim",
     "giris cozunurlugu 224x224"),
    ("0.329 GMACs at 224", 2, "architecture_dim",
     "giris cozunurlugu 224x224"),
    # 22 Agu (defter final2): gecikme protokolu + fp32 sonuc cumleleri SS4'ten cikti;
    # protokol artik supplementary'de (unit "tables", asagida ex() cagrilari) ve
    # tab_efficiency altyazisinda. SS4'te kalan iki kalinti asagida.
    ("in the Supplementary alongside Table S", 0, "table_reference",
     "Supplementary Table S7 capraz referansi"),
    ("reported as speedup factors and the observed", 0, "dtype_name",
     "fp32 veri tipi adinin icindeki basamak"),
]
for _row, _idx, _cls, _why in EX_04:
    ex("04_experiments", -1, _row, _idx, _cls, _why)

# --- 05_results_discussion
b("05_results_discussion", -1, "T^ * _ ECE =", 0, A_TSS,
  "results.ferplus.T_star_ece", "2dp", ident="res.ferplus_tstar_ece")
b("05_results_discussion", -1, "deployed arm", 0, A_TSS,
  "results.ferplus.T_star_nll", "2dp", ident="res.ferplus_tstar_nll")
b("05_results_discussion", -1, "it is best at", 0, A_FJ,
  "T_star_jsd.T", "2dp", ident="res.ferplus_tstar_jsd")
b("05_results_discussion", -1, "it is best at", 1, A_FJ,
  "entropy_correlation.T_jsd.teacher_mean_entropy", "3dp", ident="res.teacher_entropy_tjsd")
b("05_results_discussion", -1, "nearly matches", 0, A_FJ,
  "human_mean_entropy", "3dp", ident="res.human_entropy")
b("05_results_discussion", -1, "teacher optima", 1, A_JSD,
  "results[\"(b) vote sum = 10\"].n", "int", ident="res.jsd_completerow_n")
b("05_results_discussion", -1, "in every slice", 0, A_JSD,
  "T_jsd_values_across_slices[0]", "2dp", ident="res.tstar_jsd_slices")
b("05_results_discussion", -1, "( 0.0185 0.0016", 0, A_FSJ,
  "by_checkpoint.swa[\"0.5063\"].ece[0]", "4dp", ident="res.student_ece_min")
b("05_results_discussion", -1, "( 0.0185 0.0016", 1, A_FSJ,
  "by_checkpoint.swa[\"0.5063\"].ece[1]", "4dp", ident="res.student_ece_min_sd")
b("05_results_discussion", -1, "attains the best", 0, A_FSJ,
  "by_checkpoint.swa[\"0.74\"].jsd[0]", "4dp", ident="res.student_jsd_min")
b("05_results_discussion", -1, "0.0004 ). The", 0, A_FSJ,
  "by_checkpoint.swa[\"0.74\"].jsd[1]", "4dp", ident="res.student_jsd_min_sd")
b("05_results_discussion", -1, "( 0.667 -- 0.704", 0, A_FSJ,
  "by_checkpoint.swa[\"0.26\"].rho", "3dp", ident="res.rho_min")
b("05_results_discussion", -1, "( 0.667 -- 0.704", 1, A_FSJ,
  "by_checkpoint.swa[\"1.0\"].rho", "3dp", ident="res.rho_max")
b("05_results_discussion", -1, "Student JSD varies", 0, A_JCA,
  "numerator.value", "4dp", ident="res.jsd_span_raw")
b("05_results_discussion", -1, "0.00050 --- the", 0, A_JCA,
  "R_noise.seed_sd_by_convention[\"mean sd\"]", "5dp", ident="res.jsd_seed_sd_mean")
b("05_results_discussion", -1, "scored). It works:", 0, A_R3W,
  "arms[\"1.0\"].ece_arm[0]", "4dp", ident="res.native_ece_raw")
b("05_results_discussion", -1, "scored). It works:", 1, A_R3W,
  "arms[\"1.0\"].ece_arm[1]", "4dp", ident="res.native_ece_raw_sd")
b("05_results_discussion", -1, "0.0203 0.0017", 0, A_R3W,
  "arms[\"1.0\"].ece_ts[0]", "4dp", ident="res.native_ece_ts")
b("05_results_discussion", -1, "0.0203 0.0017", 1, A_R3W,
  "arms[\"1.0\"].ece_ts[1]", "4dp", ident="res.native_ece_ts_sd")
b("05_results_discussion", -1, "0.0185 0.0016", 0, A_R3W,
  "arms[\"0.5063\"].ece_arm[0]", "4dp", ident="res.teacherside_ece")
b("05_results_discussion", -1, "0.0185 0.0016", 1, A_R3W,
  "arms[\"0.5063\"].ece_arm[1]", "4dp", ident="res.teacherside_ece_sd")
b("05_results_discussion", -1, "inconclusive", 1, "paper_tables/equivalence_tests.json",
  "tests[unit=ECE].p_tost", "2dp", ident="res.tost_p")
# (cift bag: ayni jeton yukarida elle beyan edildi -- uretilen kopya dusuruldu)
# (cift bag: ayni jeton yukarida elle beyan edildi -- uretilen kopya dusuruldu)
b("05_results_discussion", -1, "worth +0.35 pp", 0, A_P4,
  "recipe_step3_ranking.per_checkpoint.by_ckpt.swa.cost_of_wrong_pick_pp", "2dp", ident="res.teacher_selection_gain_swa")
b("05_results_discussion", -1, "T = 1 control", 1, A_TDO,
  "arms.ferplus.points[3].by_ckpt.swa.acc_sd", "2dp", ident="res.ferplus_control_acc_sd")
b("05_results_discussion", -1, "six cross-fitted", 0, A_R3W,
  "per_seed[\"1.0\"][\"43\"].T_s[0]", "3dp", ident="res.student_T_lo")
b("05_results_discussion", -1, "six cross-fitted", 1, A_R3W,
  "per_seed[\"1.0\"][\"42\"].T_s[1]", "3dp", ident="res.student_T_hi")
b("05_results_discussion", -1, "( ECE_ = 0.0185", 0, A_R3W,
  "corner.ECE_min", "4dp", ident="res.corner_ece_min")
b("05_results_discussion", -1, "( ECE_ = 0.0185", 1, A_R3W,
  "corner.JSD_min", "4dp", ident="res.corner_jsd_min")
b("05_results_discussion", -1, "does: the native", 0, A_R3W,
  "occupancy[\"1.0\"].ece", "4dp", ident="res.occ_native_ece")
b("05_results_discussion", -1, "0.0017 0.0545", 0, A_R3W,
  "occupancy[\"1.0\"].ece_sd", "4dp", ident="res.occ_native_ece_sd")
b("05_results_discussion", -1, "0.0017 0.0545", 1, A_R3W,
  "occupancy[\"1.0\"].jsd", "4dp", ident="res.occ_native_jsd")
b("05_results_discussion", -1, "0.0017 0.0545", 2, A_R3W,
  "occupancy[\"1.0\"].jsd_sd", "4dp", ident="res.occ_native_jsd_sd")
b("05_results_discussion", -1, "arms span 0.0201", 0, A_JCA,
  "numerator.value", "4dp", ident="res.jsd_span_raw_2")
b("05_results_discussion", -1, "they span 0.00054", 0, A_JCA,
  "R_collapse.denominator", "5dp", ident="res.jsd_span_ts")
b("05_results_discussion", -1, "they span 0.00054", 1, A_JCA,
  "R_collapse.value", "int", ident="res.jsd_collapse_ratio")
b("05_results_discussion", -1, "+0.028 on the most frequent", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Happiness].gap_native", "3dp", ident="res.gap_happiness_native")
b("05_results_discussion", -1, "+0.028 on the most frequent", 1, "paper_tables/perclass_crossing.json",
  "rows[cls=Happiness].n", "int", ident="res.n_happiness")
b("05_results_discussion", -1, "+0.305 on the rarest", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Fear].gap_native", "3dp", ident="res.gap_fear_native")
b("05_results_discussion", -1, "+0.305 on the rarest", 1, "paper_tables/perclass_crossing.json",
  "rows[cls=Fear].n", "int", ident="res.n_fear")
b("05_results_discussion", -1, "T = 1.46 surprise", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Happiness].crossing_T", "2dp", ident="res.cross_happiness")
b("05_results_discussion", -1, "T = 1.46 surprise", 1, "paper_tables/perclass_crossing.json",
  "rows[cls=Surprise].crossing_T", "2dp", ident="res.cross_surprise")
b("05_results_discussion", -1, "T = 1.46 surprise", 2, "paper_tables/perclass_crossing.json",
  "rows[cls=Sadness].crossing_T", "2dp", ident="res.cross_sadness")
b("05_results_discussion", -1, "1.82 while disgust", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Anger].crossing_T", "2dp", ident="res.cross_anger")
b("05_results_discussion", -1, "remain over-confident", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Disgust].gap_T22", "3dp", ident="res.gap_disgust_T22")
b("05_results_discussion", -1, "under-confidence", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Happiness].gap_T22", "3dp", ident="res.gap_happiness_T22")
b("05_results_discussion", -1, "under-confidence", 1, "paper_tables/perclass_crossing.json",
  "rows[cls=Neutral].gap_T22", "3dp", ident="res.gap_neutral_T22")
b("05_results_discussion", -1, "close (", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Sadness].gap_native", "3dp", ident="res.gap_sadness_native")
b("05_results_discussion", -1, "close (", 1, "paper_tables/perclass_crossing.json",
  "rows[cls=Surprise].gap_native", "3dp", ident="res.gap_surprise_native")
b("05_results_discussion", -1, "because it needs no binning", 0, "paper_tables/perclass_crossing.json",
  "rows[cls=Fear].n", "int", ident="res.n_fear_2")
b("05_results_discussion", -1, "corpus: of its", 0, "paper_tables/audit_population.json",
  "n_total", "int", ident="res.audit_n_total")
b("05_results_discussion", -1, "corpus: of its", 1, "paper_tables/audit_population.json",
  "off_standard_count", "int", ident="res.audit_offstandard")
b("05_results_discussion", -1, "( 21 % ) depart", 0, "paper_tables/audit_population.json",
  "off_standard_pct", "int", ident="res.audit_offstandard_pct")
b("05_results_discussion", -1, "accuracy-selected", 0, A_SG,
  "audit_deltas.b_best_minus_last.d_acc.mean", "2dp", ident="res.selection_inflation")
b("05_results_discussion", -1, "accuracy-selected", 1, A_SG,
  "audit_deltas.b_best_minus_last.d_acc.sd", "2dp", ident="res.selection_inflation_sd")
b("05_results_discussion", -1, "pp positive in", 0, "selection_audit/selection_distribution.json",
  "d_acc_pp.n_positive", "int", ident="res.selection_n_positive")
b("05_results_discussion", -1, "pp positive in", 1, "selection_audit/selection_distribution.json",
  "d_acc_pp.n", "int", ident="res.selection_n_runs")
b("05_results_discussion", -1, "the same contrast on FERPlus gives", 0, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].acc_pp.mean", "2dp", ident="res.ferplus_selection_inflation")
b("05_results_discussion", -1, "the same contrast on FERPlus gives", 1, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].acc_pp.sd", "2dp", ident="res.ferplus_selection_inflation_sd")
b("05_results_discussion", -1, "yields +0.645", 0, A_SG,
  "per_k[\"50\"].a2_pure_order_statistic.mean", "3dp", ident="res.orderstat_k50")
b("05_results_discussion", -1, "yields +0.645", 1, A_SG,
  "per_k[\"50\"].a2_pure_order_statistic.sd", "3dp", ident="res.orderstat_k50_sd")
b("05_results_discussion", -1, "yields +0.645", 3, A_SG,
  "per_k[\"100\"].a2_pure_order_statistic.mean", "3dp", ident="res.orderstat_k100")
b("05_results_discussion", -1, "yields +0.645", 4, A_SG,
  "per_k[\"100\"].a2_pure_order_statistic.sd", "3dp", ident="res.orderstat_k100_sd")
b("05_results_discussion", -1, "at K = 100 on", 1, A_SG,
  "per_k[\"100\"].n_runs", "int", ident="res.orderstat_n_runs")
b("05_results_discussion", -1, "+0.640 0.218", 0, A_OST,
  "results[\"50\"].a2_detrended.mean", "3dp", ident="res.orderstat_k50_detr")
b("05_results_discussion", -1, "+0.640 0.218", 1, A_OST,
  "results[\"50\"].a2_detrended.sd", "3dp", ident="res.orderstat_k50_detr_sd")
b("05_results_discussion", -1, "+0.640 0.218", 2, A_OST,
  "results[\"100\"].a2_detrended.mean", "3dp", ident="res.orderstat_k100_detr")
b("05_results_discussion", -1, "+0.640 0.218", 3, A_OST,
  "results[\"100\"].a2_detrended.sd", "3dp", ident="res.orderstat_k100_detr_sd")
b("05_results_discussion", -1, "the last 100", 1, A_OST,
  "results[\"100\"].window_drift_pp.mean", "3dp", ident="res.window_drift_k100")
b("05_results_discussion", -1, "On RAF-DB the ECE contrast is", 0, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.mean", "4dp", ident="res.rafdb_ece_contrast")
b("05_results_discussion", -1, "On RAF-DB the ECE contrast is", 1, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.sd", "4dp", ident="res.rafdb_ece_contrast_sd")
b("05_results_discussion", -1, "n = 131 SE 0.0008", 0, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.n", "int", ident="res.rafdb_ece_contrast_n")
b("05_results_discussion", -1, "n = 131 SE 0.0008", 1, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.se", "4dp", ident="res.rafdb_ece_contrast_se")
b("05_results_discussion", -1, "n = 131 SE 0.0008", 3, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.t", "2dp", ident="res.rafdb_ece_contrast_t")
b("05_results_discussion", -1, "0.0005 95 % CI", 0, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.p", "4dp", ident="res.rafdb_ece_contrast_p")
b("05_results_discussion", -1, "0.0005 95 % CI", 2, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.ci_lo", "4dp", ident="res.rafdb_ece_ci_lo")
b("05_results_discussion", -1, "0.0005 95 % CI", 3, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece.ci_hi", "4dp", ident="res.rafdb_ece_ci_hi")
b("05_results_discussion", -1, "than the last.", 0, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].ece.mean", "4dp", ident="res.ferplus_ece_contrast")
b("05_results_discussion", -1, "0.0074 n = 12", 0, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].ece.sd", "4dp", ident="res.ferplus_ece_contrast_sd")
b("05_results_discussion", -1, "0.0074 n = 12", 1, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].ece.n", "int", ident="res.ferplus_ece_contrast_n")
b("05_results_discussion", -1, "0.0074 n = 12", 2, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].ece.se", "4dp", ident="res.ferplus_ece_contrast_se")
b("05_results_discussion", -1, "resolvable (", 1, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].ece.t", "2dp", ident="res.ferplus_ece_contrast_t")
b("05_results_discussion", -1, "resolvable (", 2, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-last\"].ece.p", "3dp", ident="res.ferplus_ece_contrast_p")
b("05_results_discussion", -1, "on both datasets", 0, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].acc_pp.mean", "2dp", ident="res.rafdb_bestswa_acc")
b("05_results_discussion", -1, "on both datasets", 1, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].acc_pp.se", "3dp", ident="res.rafdb_bestswa_acc_se")
b("05_results_discussion", -1, "on both datasets", 3, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].acc_pp.t", "1dp", ident="res.rafdb_bestswa_acc_t")
b("05_results_discussion", -1, "4.3 10^ -7 on", 3, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].acc_pp.mean", "2dp", ident="res.ferplus_bestswa_acc")
b("05_results_discussion", -1, "4.3 10^ -7 on", 4, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].acc_pp.se", "3dp", ident="res.ferplus_bestswa_acc_se")
b("05_results_discussion", -1, "t(11) = 3.7 0.003", 1, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].acc_pp.t", "1dp", ident="res.ferplus_bestswa_acc_t")
b("05_results_discussion", -1, "t(11) = 3.7 0.003", 2, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].acc_pp.p", "3dp", ident="res.ferplus_bestswa_acc_p")
b("05_results_discussion", -1, "is unresolved", 0, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].ece.mean", "4dp", ident="res.rafdb_bestswa_ece")
b("05_results_discussion", -1, "is unresolved", 1, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].ece.se", "4dp", ident="res.rafdb_bestswa_ece_se")
b("05_results_discussion", -1, "is unresolved", 3, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].ece.t", "2dp", ident="res.rafdb_bestswa_ece_t")
b("05_results_discussion", -1, "0.59 ) but resolvable", 0, A_SAI,
  "datasets[\"RAF-DB\"].contrasts[\"best-swa\"].ece.p", "2dp", ident="res.rafdb_bestswa_ece_p")
# (cift bag: ayni jeton yukarida elle beyan edildi -- uretilen kopya dusuruldu)
b("05_results_discussion", -1, "+0.0069 (SD 0.0088", 1, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].ece.sd", "4dp", ident="res.ferplus_bestswa_ece_sd")
b("05_results_discussion", -1, "+0.0069 (SD 0.0088", 2, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].ece.n", "int", ident="res.ferplus_bestswa_ece_n")
b("05_results_discussion", -1, "+0.0069 (SD 0.0088", 3, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].ece.se", "4dp", ident="res.ferplus_bestswa_ece_se")
b("05_results_discussion", -1, "+0.0069 (SD 0.0088", 5, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].ece.t", "2dp", ident="res.ferplus_bestswa_ece_t")
b("05_results_discussion", -1, "0.020 ; 13 --", 0, A_SAI,
  "datasets[\"FERPlus\"].contrasts[\"best-swa\"].ece.p", "3dp", ident="res.ferplus_bestswa_ece_p")
b("05_results_discussion", -1, "The student carries", 0, A_EFF,
  "student.params_m", "3dp", ident="res.student_params")
b("05_results_discussion", -1, "The student carries", 1, A_EFF,
  "student.flops_g", "3dp", ident="res.student_flops")
b("05_results_discussion", -1, "its teacher's", 0, A_EFF,
  "teacher.params_m", "3dp", ident="res.teacher_params")
b("05_results_discussion", -1, "its teacher's", 1, A_EFF,
  "teacher.flops_g", "3dp", ident="res.teacher_flops")
b("05_results_discussion", -1, "its teacher's", 2, A_EFF,
  "compression.params_ratio", "1dp", ident="res.params_ratio")
b("05_results_discussion", -1, "25.8 smaller", 0, A_EFF,
  "compression.flops_ratio", "1dp", ident="res.flops_ratio")
b("05_results_discussion", -1, "25.8 smaller", 1, A_EFF,
  "compression.size_ratio", "1dp", ident="res.size_ratio")
b("05_results_discussion", -1, "97.96 % of that", 0, A_EFF,
  "by_checkpoint.swa.retention_pct", "2dp", ident="res.retention_swa")
b("05_results_discussion", -1, "97.96 % of that", 1, A_EFF,
  "by_checkpoint.best.retention_pct", "2dp", ident="res.retention_best")
b("05_results_discussion", -1, "compute ratio ---", 0, A_LAT,
  "speedups[device=cuda][batch=1][dtype=fp32].speedup", "2dp", ident="res.speedup_gpu_b1")
b("05_results_discussion", -1, "compute ratio ---", 2, A_LAT,
  "speedups[device=cuda][batch=32][dtype=fp32].speedup", "2dp", ident="res.speedup_gpu_b32")
b("05_results_discussion", -1, "batch 32 on the GPU", 1, A_LAT,
  "speedups[device=cpu][batch=1][dtype=fp32].speedup", "2dp", ident="res.speedup_cpu_b1")
b("05_results_discussion", -1, "batch 32 on the GPU", 2, A_LAT,
  "speedups[device=cpu][batch=32][dtype=fp32].speedup", "2dp", ident="res.speedup_cpu_b32")
b("05_results_discussion", -1, "minimum at t^ * = 1.34", 0, A_TSP,
  "half_fold_fits.stage1", "2dp", ident="s5.tstar_stage1")
b("05_results_discussion", -1, "minimum at t^ * = 1.34", 1, A_TDO,
  "arms.rafdb_stage1.points[1].teacher_ece", "4dp", ident="s5.teacher_ece_T1")
b("05_results_discussion", -1, "minimum at t^ * = 1.34", 2, A_TDO,
  "arms.rafdb_stage1.points[2].teacher_ece", "4dp", ident="s5.teacher_ece_Tstar")
b("05_results_discussion", -1, "ece follows it:", 0, A_TDO,
  "arms.rafdb_stage1.points[1].by_ckpt.swa.ece_mean", "4dp", ident="s5.stu_ece_T1")
b("05_results_discussion", -1, "ece follows it:", 1, A_TDO,
  "arms.rafdb_stage1.points[1].by_ckpt.swa.ece_sd", "4dp", ident="s5.stu_ece_T1_sd")
b("05_results_discussion", -1, "0.0428 0.0003 at t^ *", 0, A_TDO,
  "arms.rafdb_stage1.points[2].by_ckpt.swa.ece_mean", "4dp", ident="s5.stu_ece_Tstar")
b("05_results_discussion", -1, "0.0428 0.0003 at t^ *", 1, A_TDO,
  "arms.rafdb_stage1.points[2].by_ckpt.swa.ece_sd", "4dp", ident="s5.stu_ece_Tstar_sd")
b("05_results_discussion", -1, "0.1008 0.0025 at t = 2.2", 0, A_TDO,
  "arms.rafdb_stage1.points[4].by_ckpt.swa.ece_mean", "4dp", ident="s5.stu_ece_T22")
b("05_results_discussion", -1, "0.1008 0.0025 at t = 2.2", 1, A_TDO,
  "arms.rafdb_stage1.points[4].by_ckpt.swa.ece_sd", "4dp", ident="s5.stu_ece_T22_sd")
b("05_results_discussion", -1, "against within-cell seed spreads", 0, A_TDO,
  "arms.rafdb_stage1.points[2].by_ckpt.swa.ece_sd", "4dp", ident="s5.spread_min")
b("05_results_discussion", -1, "against within-cell seed spreads", 1, A_TDO,
  "arms.rafdb_stage1.points[3].by_ckpt.swa.ece_sd", "4dp", ident="s5.spread_max")
b("05_results_discussion", -1, "it stays within a 0.30 pp band", 1, A_TDO,
  "arms.rafdb_stage1.points[3].by_ckpt.swa.acc_mean", "2dp", ident="s5.acc_lo")
b("05_results_discussion", -1, "it stays within a 0.30 pp band", 2, A_TDO,
  "arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean", "2dp", ident="s5.acc_hi")
b("05_results_discussion", -1, "seven select t^ * = 1.34 on this teacher", 0, A_TSP,
  "half_fold_fits.stage1", "2dp", ident="s5.tstar_stage1_est")
b("05_results_discussion", -1, "on the control and six of seven", 0, A_TSS,
  "results.ferplus.T_star_nll", "2dp", ident="s5.tstar_ferplus_est")
b("05_results_discussion", -1, "systematic exception (ferplus nll", 0, A_ROB,
  "series[\"FERPlus\"].metrics.nll.argmin_T_all_seeds", "2dp", ident="s5.ferplus_nll_argmin")
b("05_results_discussion", -1, "(teacher ece 0.0136", 0, A_TDO,
  "arms.rafdb_vae9182.points[1].teacher_ece", "4dp", ident="s5.ctrl_teacher_ece")
b("05_results_discussion", -1, "(teacher ece 0.0136", 1, A_TSS,
  "results.vae9182.T_star_nll", "2dp", ident="s5.ctrl_tstar")
b("05_results_discussion", -1, "occurs at t = 1 ( 0.0330", 1, A_TDO,
  "arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_mean", "4dp", ident="s5.ctrl_ece_T1")
b("05_results_discussion", -1, "occurs at t = 1 ( 0.0330", 2, A_TDO,
  "arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_sd", "4dp", ident="s5.ctrl_ece_T1_sd")
b("05_results_discussion", -1, "0.0447 at t = 0.85 on the near side", 0, A_TDO,
  "arms.rafdb_vae9182.points[0].by_ckpt.swa.ece_mean", "4dp", ident="s5.ctrl_ece_085")
b("05_results_discussion", -1, "0.0447 at t = 0.85 on the near side", 2, A_TDO,
  "arms.rafdb_vae9182.points[2].by_ckpt.swa.ece_mean", "4dp", ident="s5.ctrl_ece_134")
b("05_results_discussion", -1, "0.1282 at t = 1.7", 0, A_TDO,
  "arms.rafdb_vae9182.points[3].by_ckpt.swa.ece_mean", "4dp", ident="s5.ctrl_ece_170")
b("05_results_discussion", -1, "0.1282 at t = 1.7", 2, A_TDO,
  "arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_mean", "4dp", ident="s5.ctrl_ece_220")
b("05_results_discussion", -1, "0.1282 at t = 1.7", 3, A_TDO,
  "arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_sd", "4dp", ident="s5.ctrl_ece_220_sd")
b("05_results_discussion", -1, "established as damage at 5.9", 0, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"0.85\"].ratio", "1dp", ident="s5.ctrl_ratio_085")
b("05_results_discussion", -1, "established as damage at 5.9", 1, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"1.3406\"].ratio", "1dp", ident="s5.ctrl_ratio_134")
b("05_results_discussion", -1, "( t^ * _ nll = 0.983", 0, A_TSS,
  "results.vae9182.T_star_nll", "3dp", ident="s5.ctrl_tstar_nll")
b("05_results_discussion", -1, "( t^ * _ nll = 0.983", 1, A_TSS,
  "results.vae9182.T_star_ece", "3dp", ident="s5.ctrl_tstar_ece")
b("05_results_discussion", -1, "-0.0033 0.0042 at t = 0.95", 0, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"0.95\"].mean", "4dp", ident="s5.ref095_mean")
b("05_results_discussion", -1, "-0.0033 0.0042 at t = 0.95", 1, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"0.95\"].sd", "4dp", ident="s5.ref095_sd")
b("05_results_discussion", -1, "1.68 the control seed deviation", 0, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"0.95\"].ratio", "2dp", ident="s5.ref095_ratio")
b("05_results_discussion", -1, "1.68 the control seed deviation", 1, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"1.1\"].mean", "4dp", ident="s5.ref110_mean")
b("05_results_discussion", -1, "1.68 the control seed deviation", 2, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"1.1\"].sd", "4dp", ident="s5.ref110_sd")
b("05_results_discussion", -1, "t = 1.10 ( + - + 0.98", 1, "paper_tables/control_grid_refinement.json",
  "gaps_vs_T1[\"1.1\"].ratio", "2dp", ident="s5.ref110_ratio")
b("05_results_discussion", -1, "point-estimate minimum sits at t = 0.95", 1, "paper_tables/control_grid_refinement.json",
  "series[\"0.95\"].ece_mean", "4dp", ident="s5.ref095_ece")
b("05_results_discussion", -1, "point-estimate minimum sits at t = 0.95", 2, "paper_tables/control_grid_refinement.json",
  "series[\"1.0\"].ece_mean", "4dp", ident="s5.ref100_ece")
b("05_results_discussion", -1, "disagreed in sign ( +0.0011", 0, "adaptive_t_headroom/adaptive_t_headroom.json",
  "block_b_miscalibration_causal.d_ece_all[0]", "4dp", ident="s5.miscal_seed1")
b("05_results_discussion", -1, "disagreed in sign ( +0.0011", 1, "adaptive_t_headroom/adaptive_t_headroom.json",
  "block_b_miscalibration_causal.d_ece_all[1]", "4dp", ident="s5.miscal_seed2")
b("05_results_discussion", -1, "disagreed in sign ( +0.0011", 2, "adaptive_t_headroom/adaptive_t_headroom.json",
  "block_b_miscalibration_causal.d_ece_mean", "4dp", ident="s5.miscal_mean")
b("05_results_discussion", -1, "0.0045 ) so the third seed", 0, "adaptive_t_headroom/adaptive_t_headroom.json",
  "block_b_miscalibration_causal.d_ece_sd", "4dp", ident="s5.miscal_sd")
b("05_results_discussion", -1, "soft vote distributions it is under-confident", 0, A_TDO,
  "arms.ferplus.points[3].teacher_ece", "4dp", ident="s5.fer_teacher_ece")
b("05_results_discussion", -1, "signed gap -0.1277", 0, A_TDO,
  "arms.ferplus.points[3].signed_gap", "4dp", ident="s5.fer_signed_gap")
b("05_results_discussion", -1, "signed gap -0.1277", 1, A_TSS,
  "results.ferplus.T_star_nll", "2dp", ident="s5.fer_tstar")
b("05_results_discussion", -1, "0.0783 0.0046 at the native teacher", 0, A_TDO,
  "arms.ferplus.points[3].by_ckpt.swa.ece_mean", "4dp", ident="s5.fer_ece_T1")
b("05_results_discussion", -1, "0.0783 0.0046 at the native teacher", 1, A_TDO,
  "arms.ferplus.points[3].by_ckpt.swa.ece_sd", "4dp", ident="s5.fer_ece_T1_sd")
b("05_results_discussion", -1, "0.0783 0.0046 at the native teacher", 2, A_TDO,
  "arms.ferplus.points[1].by_ckpt.swa.ece_mean", "4dp", ident="s5.fer_ece_Tstar")
b("05_results_discussion", -1, "0.0783 0.0046 at the native teacher", 3, A_TDO,
  "arms.ferplus.points[1].by_ckpt.swa.ece_sd", "4dp", ident="s5.fer_ece_Tstar_sd")
b("05_results_discussion", -1, "t^ * a 76 % reduction", 1, A_INF,
  "ferplus_effect.d_pooled", "1dp", ident="s5.fer_d_pooled")
b("05_results_discussion", -1, "d_z = 18.3", 0, A_INF,
  "ferplus_effect.d_z_paired", "1dp", ident="s5.fer_dz")
b("05_results_discussion", -1, "family ( p_ holm = 0.003", 0, A_INF,
  "results[5].p_holm", "3dp", ident="s5.fer_pholm")
b("05_results_discussion", -1, "pooling all 14 grid points", 0, A_TDO,
  "pooled_stats.swa.n_points", "int", ident="s5.pooled_n1")
b("05_results_discussion", -1, "= 0.789 (swa; 0.895", 0, A_TDO,
  "pooled_stats.swa.spearman_abs_signed_gap", "3dp", ident="s5.pooled_rho_swa")
b("05_results_discussion", -1, "= 0.789 (swa; 0.895", 1, A_TDO,
  "pooled_stats.best.spearman_abs_signed_gap", "3dp", ident="s5.pooled_rho_best")
b("05_results_discussion", -1, "= 0.789 (swa; 0.895", 2, A_TDO,
  "pooled_stats.last.spearman_abs_signed_gap", "3dp", ident="s5.pooled_rho_last")
b("05_results_discussion", -1, "checkpoints). the 14 grid points", 0, A_TDO,
  "pooled_stats.swa.n_points", "int", ident="s5.pooled_n2")
b("05_results_discussion", -1, "14 independent observations", 0, A_BOOT,
  "results.pooled_rho.n_points", "int", ident="s5.pooled_n3")
b("05_results_discussion", -1, "individual points gives = 0.789", 0, A_BOOT,
  "results.pooled_rho.point", "3dp", ident="s5.boot_rho")
b("05_results_discussion", -1, "[0.577 1.000]", 0, A_BOOT,
  "results.pooled_rho.ci95_cluster_bootstrap[0]", "3dp", ident="s5.boot_lo")
b("05_results_discussion", -1, "[0.577 1.000]", 1, A_BOOT,
  "results.pooled_rho.ci95_cluster_bootstrap[1]", "3dp", ident="s5.boot_hi")
b("05_results_discussion", -1, "the pooled correlation is -0.407", 0, A_TDO,
  "pooled_stats.swa.spearman_signed_gap", "3dp", ident="s5.pooled_signed")
b("05_results_discussion", -1, "two arms differ by -0.0391", 0, A_RT,
  "T11_collapse.pairs[\"T·τ = 5.10\"].mean", "4dp", ident="s5.collapse_510_mean")
b("05_results_discussion", -1, "two arms differ by -0.0391", 1, A_RT,
  "T11_collapse.pairs[\"T·τ = 5.10\"].sd", "4dp", ident="s5.collapse_510_sd")
b("05_results_discussion", -1, "10.20 by -0.0324", 1, A_RT,
  "T11_collapse.pairs[\"T·τ = 10.20\"].mean", "4dp", ident="s5.collapse_1020_mean")
b("05_results_discussion", -1, "10.20 by -0.0324", 2, A_RT,
  "T11_collapse.pairs[\"T·τ = 10.20\"].sd", "4dp", ident="s5.collapse_1020_sd")
b("05_results_discussion", -1, "t and moving shifts student ece by +0.0042", 0, "paper_tables/tau_t_factorial.json",
  "marginal_contrasts[0].d_ece_mean", "4dp", ident="s5.tau_at_T170_mean")
b("05_results_discussion", -1, "t and moving shifts student ece by +0.0042", 1, "paper_tables/tau_t_factorial.json",
  "marginal_contrasts[0].d_ece_sd", "4dp", ident="s5.tau_at_T170_sd")
b("05_results_discussion", -1, "t = 1.70 ) and -0.0025", 1, "paper_tables/tau_t_factorial.json",
  "marginal_contrasts[2].d_ece_mean", "4dp", ident="s5.tau_at_T085_mean")
b("05_results_discussion", -1, "t = 1.70 ) and -0.0025", 2, "paper_tables/tau_t_factorial.json",
  "marginal_contrasts[2].d_ece_sd", "4dp", ident="s5.tau_at_T085_sd")
b("05_results_discussion", -1, "to 1.70 shifts it by -0.0349", 1, "paper_tables/tau_t_factorial.json",
  "marginal_contrasts[1].d_ece_mean", "4dp", ident="s5.T_at_tau6_mean")
b("05_results_discussion", -1, "to 1.70 shifts it by -0.0349", 2, "paper_tables/tau_t_factorial.json",
  "marginal_contrasts[1].d_ece_sd", "4dp", ident="s5.T_at_tau6_sd")
b("05_results_discussion", -1, "( +0.0327 ) and then changes sign", 0, A_RT,
  "T12_alpha.gaps[\"0.5\"].mean", "4dp", ident="s5.alpha05_gap")
b("05_results_discussion", -1, "pre-scaling harms the student by -0.0352", 0, A_RT,
  "T12_alpha.gaps[\"0.9\"].mean", "4dp", ident="s5.alpha09_gap")
b("05_results_discussion", -1, "arm total student ece under over-confidence", 0, A_ASY,
  "comparisons[2].ratio_absolute", "2dp", ident="s5.asym_rafdb")
b("05_results_discussion", -1, "on raf-db (bootstrap 95 % ci", 1, A_ASY,
  "comparisons[2].ci_absolute[0]", "2dp", ident="s5.asym_rafdb_lo")
b("05_results_discussion", -1, "on raf-db (bootstrap 95 % ci", 2, A_ASY,
  "comparisons[2].ci_absolute[1]", "2dp", ident="s5.asym_rafdb_hi")
b("05_results_discussion", -1, "on raf-db (bootstrap 95 % ci", 3, A_ASY,
  "comparisons[5].ratio_absolute", "2dp", ident="s5.asym_ferplus")
b("05_results_discussion", -1, "ferplus ( [1.64 2.48]", 0, A_ASY,
  "comparisons[5].ci_absolute[0]", "2dp", ident="s5.asym_ferplus_lo")
b("05_results_discussion", -1, "ferplus ( [1.64 2.48]", 1, A_ASY,
  "comparisons[5].ci_absolute[1]", "2dp", ident="s5.asym_ferplus_hi")
b("05_results_discussion", -1, "beyond the measured grid and the headline", 0, A_ASY,
  "summary.interpolated_only.absolute.min", "1dp", ident="s5.asym_min")
b("05_results_discussion", -1, "beyond the measured grid and the headline", 1, A_ASY,
  "summary.interpolated_only.absolute.max", "1dp", ident="s5.asym_max")
b("05_results_discussion", -1, "1.74 0.43 --- consistent", 0, A_ASY,
  "summary.all_six.absolute.mean", "2dp", ident="s5.asym_six_mean")
b("05_results_discussion", -1, "1.74 0.43 --- consistent", 1, A_ASY,
  "summary.all_six.absolute.sd", "2dp", ident="s5.asym_six_sd")
b("05_results_discussion", -1, "teacher both comparisons' intervals straddle", 1, A_ASY,
  "comparisons[3].ci_absolute[0]", "2dp", ident="s5.asym_ctrl1_lo")
b("05_results_discussion", -1, "teacher both comparisons' intervals straddle", 2, A_ASY,
  "comparisons[3].ci_absolute[1]", "2dp", ident="s5.asym_ctrl1_hi")
b("05_results_discussion", -1, "[0.90 1.46]", 0, A_ASY,
  "comparisons[4].ci_absolute[0]", "2dp", ident="s5.asym_ctrl2_lo")
b("05_results_discussion", -1, "[0.90 1.46]", 1, A_ASY,
  "comparisons[4].ci_absolute[1]", "2dp", ident="s5.asym_ctrl2_hi")
b("05_results_discussion", -1, "sweeping student width over a factor", 0, "p5_efficiency/p5_efficiency.json",
  "params_spread_ratio", "2dp", ident="s5.params_ratio")
b("05_results_discussion", -1, "accuracy by +1.94 pp but student ece", 1, A_RT,
  "T10_axis_spans.swa.capacity_span", "5dp", ident="s5.capacity_span")
b("05_results_discussion", -1, "teacher's temperature on a fixed student", 0, A_RT,
  "T10_axis_spans.swa.teacher_span", "4dp", ident="s5.teacher_span")
b("05_results_discussion", -1, "at the same checkpoint. the teacher-side lever", 0, A_RT,
  "T10_axis_spans.swa.ratio", "int", ident="s5.lever_swa")
b("05_results_discussion", -1, "( 79 and 27 at the best", 0, A_RT,
  "T10_axis_spans.best.ratio", "int", ident="s5.lever_best")
b("05_results_discussion", -1, "( 79 and 27 at the best", 1, A_RT,
  "T10_axis_spans.last.ratio", "int", ident="s5.lever_last")
b("05_results_discussion", -1, "instead lowers it to 69", 0, "paper_tables/g42_init_matched_lever.json",
  "rows[0].ratio_init_matched", "int", ident="s5.lever_im_swa")
b("05_results_discussion", -1, "instead lowers it to 69", 1, "paper_tables/g42_init_matched_lever.json",
  "rows[1].ratio_init_matched", "int", ident="s5.lever_im_best")
b("05_results_discussion", -1, "instead lowers it to 69", 2, "paper_tables/g42_init_matched_lever.json",
  "rows[2].ratio_init_matched", "int", ident="s5.lever_im_last")
b("05_results_discussion", -1, "accuracy unchanged ( -0.02", 0, "vich_isolation/vich_isolation_verdict.json",
  "paired_delta_linear_minus_vich.d_acc_mean", "2dp", ident="s5.head_dacc")
b("05_results_discussion", -1, "accuracy unchanged ( -0.02", 1, "vich_isolation/vich_isolation_verdict.json",
  "paired_delta_linear_minus_vich.d_acc_sd", "2dp", ident="s5.head_dacc_sd")
b("05_results_discussion", -1, "+0.0062 0.0015 with the same sign", 0, "vich_isolation/vich_isolation_verdict.json",
  "paired_delta_linear_minus_vich.d_ece_mean", "4dp", ident="s5.head_dece")
b("05_results_discussion", -1, "+0.0062 0.0015 with the same sign", 1, "vich_isolation/vich_isolation_verdict.json",
  "paired_delta_linear_minus_vich.d_ece_sd", "4dp", ident="s5.head_dece_sd")
b("05_results_discussion", -1, "variational head accounts for roughly", 0, "vich_isolation/vich_isolation_verdict.json",
  "paired_delta_linear_minus_vich.ece_relative_reduction_pct", "int", ident="s5.head_pct")
b("05_results_discussion", -1, "-0.006 against a seed-noise envelope", 0, "a13_scratch_dose/a13_verdict.json",
  "comparisons[1].d_slope", "3dp", ident="s5.cap_dslope")
b("05_results_discussion", -1, "-0.006 against a seed-noise envelope", 1, "a13_scratch_dose/a13_verdict.json",
  "comparisons[1].combined_envelope", "3dp", ident="s5.cap_env")
b("05_results_discussion", -1, "contrast shifts it by -0.067", 0, "a13_scratch_dose/a13_verdict.json",
  "comparisons[0].d_slope", "3dp", ident="s5.init_dslope")
b("05_results_discussion", -1, "contrast shifts it by -0.067", 1, "a13_scratch_dose/a13_verdict.json",
  "comparisons[0].combined_envelope", "3dp", ident="s5.init_env")
b("05_results_discussion", -1, "confounded contrast that motivated the test", 0, "a13_scratch_dose/a13_verdict.json",
  "comparisons[2].d_slope", "3dp", ident="s5.conf_dslope")
b("05_results_discussion", -1, "0.080 ) turns out to be almost entirely", 0, "a13_scratch_dose/a13_verdict.json",
  "comparisons[2].combined_envelope", "3dp", ident="s5.conf_env")
b("05_results_discussion", -1, "0.655 ( 0.71 m scratch)", 0, "a13_scratch_dose/a13_verdict.json",
  "fits.scratch0712.slope", "3dp", ident="s5.slope_s0712")
b("05_results_discussion", -1, "0.655 ( 0.71 m scratch)", 2, "a13_scratch_dose/a13_verdict.json",
  "fits.scratch2248.slope", "3dp", ident="s5.slope_s2248")
b("05_results_discussion", -1, "0.655 ( 0.71 m scratch)", 4, "a13_scratch_dose/a13_verdict.json",
  "fits.pretrained2248.slope", "3dp", ident="s5.slope_p2248")
b("05_results_discussion", -1, "none of them ( at swa: -0.22", 0, A_CRIT,
  "cells[\"stage1/gate:oracle_error\"].swa.acc.mean", "2dp", ident="s5.oracle_acc_stage1")
b("05_results_discussion", -1, "none of them ( at swa: -0.22", 1, A_CRIT,
  "cells[\"stage1/gate:oracle_error\"].swa.acc.sd_paired", "2dp", ident="s5.oracle_acc_stage1_sd")
b("05_results_discussion", -1, "-0.01 0.72 and -0.23 0.49", 0, A_CRIT,
  "cells[\"primary/gate:oracle_error\"].swa.acc.mean", "2dp", ident="s5.oracle_acc_primary")
b("05_results_discussion", -1, "-0.01 0.72 and -0.23 0.49", 1, A_CRIT,
  "cells[\"primary/gate:oracle_error\"].swa.acc.sd_paired", "2dp", ident="s5.oracle_acc_primary_sd")
b("05_results_discussion", -1, "-0.01 0.72 and -0.23 0.49", 2, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.acc.mean", "2dp", ident="s5.oracle_acc_vae")
b("05_results_discussion", -1, "-0.01 0.72 and -0.23 0.49", 3, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.acc.sd_paired", "2dp", ident="s5.oracle_acc_vae_sd")
b("05_results_discussion", -1, "degrades student calibration by +0.0056", 0, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.ece.mean", "4dp", ident="s5.oracle_ece_vae")
b("05_results_discussion", -1, "degrades student calibration by +0.0056", 1, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.ece.sd_paired", "4dp", ident="s5.oracle_ece_vae_sd")
b("05_results_discussion", -1, "sign in all three seeds and a magnitude 2.1", 0, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.ece.ratio_vs_control_sd", "1dp", ident="s5.oracle_ece_vae_ratio")
b("05_results_discussion", -1, "( 1.10 the control seed deviation", 0, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.acc.ratio_vs_control_sd", "2dp", ident="s5.oracle_acc_vae_ratio")
b("05_results_discussion", -1, "control arm's the same cell is 1.4", 0, A_CRIT,
  "cells[\"vae9182/gate:oracle_error\"].swa.ece.ratio_vs_paired_sd", "1dp", ident="s5.oracle_ece_vae_pratio")
b("05_results_discussion", -1, "paired t -test at n = 3 gives", 1, A_INF,
  "results[4].p_raw", "3dp", ident="s5.oracle_p")
b("05_results_discussion", -1, "( +0.0015 0.0036", 0, A_CRIT,
  "cells[\"stage1/gate:oracle_error\"].swa.ece.mean", "4dp", ident="s5.oracle_ece_stage1")
b("05_results_discussion", -1, "( +0.0015 0.0036", 1, A_CRIT,
  "cells[\"stage1/gate:oracle_error\"].swa.ece.sd_paired", "4dp", ident="s5.oracle_ece_stage1_sd")
b("05_results_discussion", -1, "( +0.0015 0.0036", 2, A_CRIT,
  "cells[\"primary/gate:oracle_error\"].swa.ece.mean", "4dp", ident="s5.oracle_ece_primary")
b("05_results_discussion", -1, "( +0.0015 0.0036", 3, A_CRIT,
  "cells[\"primary/gate:oracle_error\"].swa.ece.sd_paired", "4dp", ident="s5.oracle_ece_primary_sd")
b("05_results_discussion", -1, "calibration effect smaller than 3.2", 0, A_CSM,
  "mde_ece_swa_pct_min", "1dp", ident="s5.mde_pct_min")
b("05_results_discussion", -1, "calibration effect smaller than 3.2", 1, A_CSM,
  "mde_ece_swa_pct_max", "1dp", ident="s5.mde_pct_max")
b("05_results_discussion", -1, "( 0.075 vs. 0.028", 1, A_CSM,
  "rows[checkpoint=swa][axis=ece][teacher=vae9182][class_weight_mode=none].control_level", "3dp", ident="s5.ctrl_level_vae")
b("05_results_discussion", -1, "-0.0042 0.0004 negative in all three seeds", 0, A_CRIT,
  "cells[\"stage1/g2g_kl\"].swa.ece.mean", "4dp", ident="s5.g2g_ece")
b("05_results_discussion", -1, "-0.0042 0.0004 negative in all three seeds", 1, A_CRIT,
  "cells[\"stage1/g2g_kl\"].swa.ece.sd_paired", "4dp", ident="s5.g2g_ece_sd")
b("05_results_discussion", -1, "-0.0042 0.0004 negative in all three seeds", 2, A_CRIT,
  "cells[\"stage1/g2g_kl\"].swa.ece.ratio_vs_control_sd", "1dp", ident="s5.g2g_ratio")
b("05_results_discussion", -1, "11.9 under the paired-difference denominator", 0, A_CRIT,
  "cells[\"stage1/g2g_kl\"].swa.ece.ratio_vs_paired_sd", "1dp", ident="s5.g2g_pratio")
b("05_results_discussion", -1, "third seed completes ( -0.0011", 0, A_CRIT,
  "cells[\"stage1/adaptive_t\"].swa.ece.mean", "4dp", ident="s5.adaptive_stage1")
b("05_results_discussion", -1, "third seed completes ( -0.0011", 1, A_CRIT,
  "cells[\"stage1/adaptive_t\"].swa.ece.sd_paired", "4dp", ident="s5.adaptive_stage1_sd")
b("05_results_discussion", -1, "( +0.0023 positive in all three seeds", 0, A_CRIT,
  "cells[\"primary/adaptive_t\"].swa.ece.mean", "4dp", ident="s5.adaptive_primary")
b("05_results_discussion", -1, "( +0.0023 positive in all three seeds", 1, A_CRIT,
  "cells[\"primary/adaptive_t\"].swa.ece.ratio_vs_control_sd", "1dp", ident="s5.adaptive_primary_ratio")
b("05_results_discussion", -1, "teacher it reverses once more", 0, A_CRIT,
  "cells[\"vae9182/adaptive_t\"].swa.ece.mean", "4dp", ident="s5.adaptive_vae")
b("05_results_discussion", -1, "2.10 its control's seed deviation", 0, A_CRIT,
  "cells[\"vae9182/adaptive_t\"].swa.ece.ratio_vs_control_sd", "2dp", ident="s5.adaptive_vae_ratio")
# 28 Agu 2026 -- KAPI BIR ATIF HATASI YAKALADI. Metin dalgasi bu cumleyi yeniden yazdi ve
# "the screening used the sibling MEAN-logvar signal's AUROC there, 0.46, as the proxy" dedi.
# Olculdu: VAE9182 x mean_logvar = 0.169 (0.17), VAE9182 x target_logvar = 0.4579 (0.46). Yani
# 0.46 sinyalin KENDI degeri, kardes sinyalin vekili degil; eleme kaydi da bunu soyluyor
# (mechanism_grid_gaps: "gate sinyali on-kayitli taramada aleyhte: AUROC 0.4579"). Cumle
# duzeltildi, baglar sinyaliyle birlikte yeniden capalandi. Uc bag da AYNI alanlarda kaldi.
b("05_results_discussion", -1, "that signal's own auroc there 0.46", 0, "rafdb_signal_quality/signal_quality_table.json",
  "[teacher=VAE9182][signal=target_logvar].auroc_signed", "2dp", ident="s5.auroc_vae")
b("05_results_discussion", -1, "0.70 and 0.84 on the teachers", 0, "rafdb_signal_quality/signal_quality_table.json",
  "[teacher=Stage1][signal=target_logvar].auroc_signed", "2dp", ident="s5.auroc_stage1")
b("05_results_discussion", -1, "0.70 and 0.84 on the teachers", 1, "rafdb_signal_quality/signal_quality_table.json",
  "[teacher=Primary][signal=target_logvar].auroc_signed", "2dp", ident="s5.auroc_primary")
b("05_results_discussion", -1, "direction. its effect on accuracy is small", 0, A_NU,
  "nine_cell_grid[\"swa|vae9182\"].d_acc_mean", "2dp", ident="s5.ls_acc_min")
b("05_results_discussion", -1, "-0.58 pp across teachers", 0, A_NU,
  "nine_cell_grid[\"last|vae9182\"].d_acc_mean", "2dp", ident="s5.ls_acc_max")
b("05_results_discussion", -1, "is large and one-signed increasing student ece", 0, A_NU,
  "nine_cell_grid[\"swa|primary\"].d_ece_mean", "3dp", ident="s5.ls_ece_min")
b("05_results_discussion", -1, "is large and one-signed increasing student ece", 1, A_NU,
  "nine_cell_grid[\"swa|vae9182\"].d_ece_mean", "3dp", ident="s5.ls_ece_max")
b("05_results_discussion", -1, "at swa and by up to +0.159", 0, A_NU,
  "nine_cell_grid[\"last|vae9182\"].d_ece_mean", "3dp", ident="s5.ls_ece_last")
b("05_results_discussion", -1, "reporting checkpoint the accuracy effect reaches", 0, A_NU,
  "nine_cell_grid[\"swa|primary\"].acc_units", "1dp", ident="s5.ls_acc_units")
b("05_results_discussion", -1, "units on any teacher whereas", 0, A_NU,
  "nine_cell_grid[\"swa|primary\"].ece_units", "int", ident="s5.ls_ece_units_min")
b("05_results_discussion", -1, "units on any teacher whereas", 1, A_NU,
  "nine_cell_grid[\"swa|stage1\"].ece_units", "int", ident="s5.ls_ece_units_max")
b("05_results_discussion", -1, "calibration harm exceeds the accuracy harm", 0, A_NU,
  "summary.median", "int", ident="s5.ls_ratio_median")
b("05_results_discussion", -1, "23 at the reporting checkpoint", 0, A_NU,
  "nine_cell_grid[\"swa|primary\"].ratio", "int", ident="s5.ls_ratio_swa_min")
b("05_results_discussion", -1, "lower ( 2.6 at a last-checkpoint cell", 0, A_NU,
  "summary.min", "1dp", ident="s5.ls_ratio_floor")
b("05_results_discussion", -1, "where the accuracy change ( -0.12 pp)", 0, A_NU,
  "nine_cell_grid[\"swa|vae9182\"].d_acc_mean", "2dp", ident="s5.ls_vae_dacc")
b("05_results_discussion", -1, "of its own control ( 0.37 pp)", 0, A_NU,
  "nine_cell_grid[\"swa|vae9182\"].sigma_acc", "2dp", ident="s5.ls_vae_sigma_acc")
b("05_results_discussion", -1, "calibration change is 69 times", 0, A_NU,
  "nine_cell_grid[\"swa|vae9182\"].ece_units", "int", ident="s5.ls_vae_ece_units")
b("05_results_discussion", -1, "all three teachers ( p_ holm 0.003", 0, A_INF,
  "results[2].p_holm", "3dp", ident="s5.ls_pholm")
b("05_results_discussion", -1, "deserve reporting. First the closest approach", 0, A_CRIT,
  "cells[\"stage1/gate:target_logvar\"].swa.ece.ratio_vs_control_sd", "2dp", ident="s5.gate_near_miss")
b("05_results_discussion", -1, "magnitude ( 2.51 )", 0, A_CRIT,
  "cells[\"stage1/gate:target_logvar\"].swa.acc.ratio_vs_control_sd", "2dp", ident="s5.gate_acc_ratio")
b("05_results_discussion", -1, "(target _logvar on primary auroc 0.84", 0, "rafdb_signal_quality/signal_quality_table.json",
  "[teacher=Primary][signal=target_logvar].auroc_signed", "2dp", ident="s5.auroc_primary2")
b("05_results_discussion", -1, "the smallest effect of the five ( 0.23", 0, A_CRIT,
  "cells[\"primary/gate:target_logvar\"].swa.ece.ratio_vs_control_sd", "2dp", ident="s5.gate_smallest")
b("05_results_discussion", -1, "less well (auroc 0.70", 0, "rafdb_signal_quality/signal_quality_table.json",
  "[teacher=Stage1][signal=target_logvar].auroc_signed", "2dp", ident="s5.auroc_stage1_2")
b("05_results_discussion", -1, "the three teachers span 0.42 pp", 1, A_P4,
  "recipe_step3_ranking.rows[teacher=stage1].teacher_acc", "2dp", ident="s5.teacher_acc_stage1")
b("05_results_discussion", -1, "92.01 91.82 ) and a factor of 2.9", 0, A_P4,
  "recipe_step3_ranking.rows[teacher=primary].teacher_acc", "2dp", ident="s5.teacher_acc_primary")
b("05_results_discussion", -1, "92.01 91.82 ) and a factor of 2.9", 1, A_P4,
  "recipe_step3_ranking.rows[teacher=vae9182].teacher_acc", "2dp", ident="s5.teacher_acc_vae")
b("05_results_discussion", -1, "( 0.0378 0.0396 0.0136 )", 0, A_P4,
  "recipe_step3_ranking.rows[teacher=stage1].teacher_ece", "4dp", ident="s5.teacher_ece_stage1")
b("05_results_discussion", -1, "( 0.0378 0.0396 0.0136 )", 1, A_P4,
  "recipe_step3_ranking.rows[teacher=primary].teacher_ece", "4dp", ident="s5.teacher_ece_primary")
b("05_results_discussion", -1, "( 0.0378 0.0396 0.0136 )", 2, A_P4,
  "recipe_step3_ranking.rows[teacher=vae9182].teacher_ece", "4dp", ident="s5.teacher_ece_vae")
b("05_results_discussion", -1, "-0.87 against student accuracy at the swa", 0, A_P4,
  "recipe_step3_ranking.per_checkpoint.by_ckpt.swa.spearman_teacherACC_vs_studentACC", "2dp", ident="s5.rank_acc_swa")
b("05_results_discussion", -1, "-0.87 against student accuracy at the swa", 1, A_P4,
  "recipe_step3_ranking.per_checkpoint.by_ckpt.best.spearman_teacherACC_vs_studentACC", "2dp", ident="s5.rank_acc_best")
b("05_results_discussion", -1, "calibration error recovers it ( +0.87", 0, A_P4,
  "recipe_step3_ranking.per_checkpoint.by_ckpt.swa.spearman_negTeacherECE_vs_studentACC", "2dp", ident="s5.rank_ece_swa")
b("05_results_discussion", -1, "calibration error recovers it ( +0.87", 1, A_P4,
  "recipe_step3_ranking.per_checkpoint.by_ckpt.best.spearman_negTeacherECE_vs_studentACC", "2dp", ident="s5.rank_ece_best")
b("05_results_discussion", -1, "( 89.60 pp each)", 0, A_P4,
  "recipe_step3_ranking.per_checkpoint.by_ckpt.swa.student_acc.stage1", "2dp", ident="s5.tie_swa")
b("05_results_discussion", -1, "checkpoint we report as primary ( 0.52 pp", 0, A_P4,
  "recipe_step3_ranking.cost_of_wrong_pick_pp", "2dp", ident="s5.sel_cost_best")
b("05_results_discussion", -1, "section ( 0.41 pp)", 0, A_RT,
  "T5_mechanisms[\"stage1/g2g_kl\"].swa.d_acc_mean", "2dp", ident="s5.largest_mech_acc")
# (cift beyan: `res.tstar_optima_gap_pct` ayni jetonu elle yazilan beyanla paylasiyordu; dusuruldu)
dv("res.jsd_slice_coverage_pct", "99.1", "pct_of",
   [op(A_JSD, "results[\"(a) all rows\"].n - results[\"(c) stratum 6-7\"].n"),
    op(A_JSD, "results[\"(a) all rows\"].n")],
   "1dp", "05_results_discussion", -1, "every slice holding", 1)
dv("res.tradeoff_ece_cost", "+0.0159", "diff",
   [op(A_FSJ, "by_checkpoint.swa[\"0.74\"].ece[0]"),
    op(A_FSJ, "by_checkpoint.swa[\"0.5063\"].ece[0]")],
   "4dp", "05_results_discussion", -1, "temperature costs", 0)
dv("res.tradeoff_jsd_gain", "-0.0051", "diff",
   [op(A_FSJ, "by_checkpoint.swa[\"0.74\"].jsd[0]"),
    op(A_FSJ, "by_checkpoint.swa[\"0.5063\"].jsd[0]")],
   "4dp", "05_results_discussion", -1, "temperature costs", 1)
# (cift beyan: `res.studentTS_jsd_advantage` ayni jetonu elle yazilan beyanla paylasiyordu; dusuruldu)
dv("res.sharpened_target_acc_gain", "+0.40", "diff",
   [op(A_TDO, "arms.ferplus.points[1].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "05_results_discussion", -1, "+0.40 pp on FERPlus", 0)
dv("res.ferplus_control_mde", "0.74", "sum",
   [op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.acc_sd"),
    op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.acc_sd")],
   "2dp", "05_results_discussion", -1, "T = 1 control", 2)
dv("res.corner_jsd_shortfall", "0.0002", "diff",
   [op(A_R3W, "occupancy[\"0.74\"].jsd - corner.JSD_min"),
    op(A_R3W, "occupancy[\"0.74\"].bar_jsd")],
   "4dp", "05_results_discussion", -1, "qualify missing", 0)
dv("res.detrend_shift_max", "0.04", "diff",
   [op(A_OST, "results[\"100\"].a2_raw.mean"),
    op(A_OST, "results[\"100\"].a2_detrended.mean")],
   "2dp", "05_results_discussion", -1, "ordinary least", 0)
dv("res.rafdb_ece_effect_pct", "4", "pct_drop",
   [op(A_SAI, "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece_scale_denominators[\"mean ECE @last\"]"),
    op(A_SAI, "datasets[\"RAF-DB\"].contrasts[\"best-last\"].ece_scale_denominators[\"mean ECE @best\"]")],
   "int", "05_results_discussion", -1, "calibration effect is", 0)
# (cift beyan: `res.ferplus_bestswa_ece_pct_lo` ayni jetonu elle yazilan beyanla paylasiyordu; dusuruldu)
# (cift beyan: `res.ferplus_bestswa_ece_pct_hi` ayni jetonu elle yazilan beyanla paylasiyordu; dusuruldu)
dv("res.fp16_b1_ratio_lo", "1.20", "ratio",
   [op("p5_efficiency/latency_benchmark_session2.json", "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=1][dtype=fp16].median_ms"),
    op("p5_efficiency/latency_benchmark_session2.json", "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=1][dtype=fp32].median_ms")],
   "2dp", "tables", -1, "independent measurement sessions (", 0)
dv("res.fp16_b1_ratio_hi", "1.34", "ratio",
   [op(A_LAT, "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=1][dtype=fp16].median_ms"),
    op(A_LAT, "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=1][dtype=fp32].median_ms")],
   "2dp", "tables", -1, "independent measurement sessions (", 1)
dv("res.fp16_b32_ratio_lo", "0.63", "ratio",
   [op(A_LAT, "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=32][dtype=fp16].median_ms"),
    op(A_LAT, "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=32][dtype=fp32].median_ms")],
   "2dp", "tables", -1, "( 0.63 --", 0)
dv("res.fp16_b32_ratio_hi", "0.69", "ratio",
   [op("p5_efficiency/latency_benchmark_session2.json", "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=32][dtype=fp16].median_ms"),
    op("p5_efficiency/latency_benchmark_session2.json", "measurements[device=cuda][model=teacher_POSTERv2_VAE][batch=32][dtype=fp32].median_ms")],
   "2dp", "tables", -1, "( 0.63 --", 1)
dv("s5.ece_reduction_rafdb", "41", "pct_drop",
   [op(A_TDO, "arms.rafdb_stage1.points[1].by_ckpt.swa.ece_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.ece_mean")],
   "int", "05_results_discussion", -1, "0.0428 0.0003 at t^ *", 2)
dv("s5.full_swing", "2.4", "ratio",
   [op(A_TDO, "arms.rafdb_stage1.points[4].by_ckpt.swa.ece_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.ece_mean")],
   "1dp", "05_results_discussion", -1, "0.1008 0.0025 at t = 2.2", 3)
dv("s5.acc_band_stage1", "0.30", "diff",
   [op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "05_results_discussion", -1, "it stays within a 0.30 pp band", 0)
dv("s5.acc_paired_gain", "+0.13", "diff",
   [op(A_TDO, "arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_stage1.points[1].by_ckpt.swa.acc_mean")],
   "2dp", "05_results_discussion", -1, "against the native teacher is +0.13", 0)
dv("s5.ctrl_deterioration", "6.4", "ratio",
   [op(A_TDO, "arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_mean"),
    op(A_TDO, "arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_mean")],
   "1dp", "05_results_discussion", -1, "6.4 -fold deterioration", 0)
dv("s5.acc_band_vae9182", "0.51", "diff",
   [op(A_TDO, "arms.rafdb_vae9182.points[2].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.rafdb_vae9182.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "05_results_discussion", -1, "within 0.51 pp.", 0)
dv("s5.ece_reduction_ferplus", "76", "pct_drop",
   [op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.ece_mean"),
    op(A_TDO, "arms.ferplus.points[1].by_ckpt.swa.ece_mean")],
   "int", "05_results_discussion", -1, "t^ * a 76 % reduction", 0)
dv("s5.collapse_ratio_510", "16.3", "ratio",
   [op(A_RT, "T11_collapse.pairs[\"T·τ = 5.10\"].mean"),
    op(A_RT, "T11_collapse.two_bar")],
   "1dp", "05_results_discussion", -1, "seeds and magnitudes 16.3", 0)
dv("s5.collapse_ratio_1020", "13.5", "ratio",
   [op(A_RT, "T11_collapse.pairs[\"T·τ = 10.20\"].mean"),
    op(A_RT, "T11_collapse.two_bar")],
   "1dp", "05_results_discussion", -1, "seeds and magnitudes 16.3", 1)
dv("s5.acc_band_ferplus", "0.49", "diff",
   [op(A_TDO, "arms.ferplus.points[0].by_ckpt.swa.acc_mean"),
    op(A_TDO, "arms.ferplus.points[3].by_ckpt.swa.acc_mean")],
   "2dp", "05_results_discussion", -1, "not flat: it decreases monotonically", 0)
dv("s5.capacity_acc_span", "+1.94", "diff",
   [op(A_RT, "T10_capacity_cells.swa[\"scratch w100ns\"].acc_mean"),
    op(A_RT, "T10_capacity_cells.swa[\"scratch w050\"].acc_mean")],
   "2dp", "05_results_discussion", -1, "accuracy by +1.94 pp but student ece", 0)
dv("s5.teacher_acc_span", "0.42", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].teacher_acc"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].teacher_acc")],
   "2dp", "05_results_discussion", -1, "the three teachers span 0.42 pp", 0)
dv("s5.teacher_ece_factor", "2.9", "ratio",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=primary].teacher_ece"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].teacher_ece")],
   "1dp", "05_results_discussion", -1, "92.01 91.82 ) and a factor of 2.9", 2)
dv("s5.sel_cost_swa", "0.35", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.swa.acc_mean"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.swa.acc_mean")],
   "2dp", "05_results_discussion", -1, "cost of the accuracy rule is 0.35 pp", 0)
dv("s5.sel_cost_last", "0.83", "diff",
   [op(A_P4, "recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.last.acc_mean"),
    op(A_P4, "recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.last.acc_mean")],
   "2dp", "05_results_discussion", -1, "checkpoint 0.83 pp at the last)", 0)
dv("s5.baseline_ece_overconf", "0.075", "mean",
   [op(A_CSM, "rows[checkpoint=swa][axis=ece][teacher=stage1][class_weight_mode=none].control_level"),
    op(A_CSM, "rows[checkpoint=swa][axis=ece][teacher=primary][class_weight_mode=none].control_level")],
   "3dp", "05_results_discussion", -1, "( 0.075 vs. 0.028", 0)
EX_05 = [
    ("visibly different", 0, "table_reference",
     "Supplementary Figure S3 atfi -- capraz referans, olcum degil"),
    ("teacher optima", 0, "criterion_constant",
     "'complete-row' kesitinin TANIMI: oy toplami = 10; esik tanimi, olcum degil"),
    ("every slice holding", 0, "criterion_constant",
     "kesit buyuklugu esigi 1000 satir -- S2 duzyazisinda ayni esik zaten criterion_constant olarak muaf"),
    ("(Supplementary Table S3);", 0, "table_reference",
     "Supplementary Table S3 atfi"),
    ("the student distilled", 0, "hyperparameter",
     "kolun damitma sicakligi (T=0.5063'un yuvarlanmisi) -- kol ETIKETI; olculen T*_NLL 05:608'de ayrica baglandi"),
    ("( 0.0185 0.0016", 2, "hyperparameter",
     "kol etiketi T=0.74 (damitma sicakligi), olcum degil"),
    ("inconclusive", 0, "sample_size",
     "n = 3 tohum -- mevcut tab_human/tab_holm muafiyetleriyle ayni"),
    ("scaling preserves", 0, "hyperparameter",
     "olceklenmemis kol T=1"),
    ("T = 1 control", 0, "hyperparameter",
     "kontrol kolu T=1"),
    ("human-aligned", 0, "hyperparameter",
     "aday tarifin kol etiketi T=0.74"),
    # 21 Agu (jeton final, 9b dalgasi): figur atfi S4 -> S3 ve cumle yeniden yazildi.
    ("Resolved by class", 0, "table_reference",
     "Supplementary Figure S3 atfi (9b: S-numaralari yeniden hizalandi)"),
    ("remain over-confident", 2, "hyperparameter",
     "izgaranin ucu T=2.2 -- kol ayari"),
    ("(Supplementary Table S6", 0, "table_reference",
     "Supplementary Table S6 atfi"),
    ("(Supplementary Table S6", 1, "table_reference",
     "Supplementary Figure S2 atfi"),
    ("yields +0.645", 2, "benchmark_protocol",
     "son-K penceresinin uzunlugu K=50 -- kestiricinin olcum protokolu (alternatif: criterion_constant)"),
    ("at K = 100 on", 0, "benchmark_protocol",
     "son-K penceresinin uzunlugu K=100"),
    ("the last 100", 0, "benchmark_protocol",
     "egilimin uydurulduğu pencere: son 100 epok"),
    ("n = 131 SE 0.0008", 2, "sample_size",
     "serbestlik derecesi df = n-1 = 130; n'den tureyen sabit"),
    ("0.0005 95 % CI", 1, "criterion_constant",
     "%95 guven duzeyi -- olcut, olcum degil"),
    ("resolvable (", 0, "sample_size",
     "serbestlik derecesi df = 11"),
    ("on both datasets", 2, "sample_size",
     "serbestlik derecesi df = 117"),
    ("4.3 10^ -7 on", 1, "scientific_notation",
     "YENI SINIF ONERISI: bilimsel gosterimin TABANI (10). Tek bir p degerinin yazimindan dogan jeton, ayri bir nicelik degil"),
    ("t(11) = 3.7 0.003", 0, "sample_size",
     "serbestlik derecesi df = 11"),
    ("is unresolved", 2, "sample_size",
     "serbestlik derecesi df = 117"),
    ("+0.0069 (SD 0.0088", 4, "sample_size",
     "serbestlik derecesi df = 11"),
    ("Table S7). Measured", 0, "table_reference",
     "Supplementary Table S7 atfi"),
    ("at the accuracy-selected one; the teacher is", 0, "teacher_name_digits",
     "'VAE9182' ogretmen adinin icindeki basamak"),
    ("compute ratio ---", 1, "benchmark_protocol",
     "olcum protokolu: batch 1"),
    ("batch 32 on the GPU", 0, "benchmark_protocol",
     "olcum protokolu: batch 32"),
    # 22 Agu: yarim-hassasiyet pasaji supplementary'ye tasindi ("tables" birimi).
    # 22 Agu: fp16 pasaji supplementary'ye tasindi; muafiyetleri "tables" biriminde.
    ("the VAE9182 one-seed-to-three", 0, "teacher_name_digits",
     "'VAE9182' adinin icindeki basamak"),
    ("are not among", 0, "teacher_name_digits",
     "'Stage1' adinin icindeki basamak"),
    ("G2G + adaptive-", 0, "hyperparameter",
     "'G2G' mekanizma adinin icindeki 2 -- S1 muafiyetlerinde ('G2G basligindaki 2') ayni sinif kullanildi"),
    ("G2G + adaptive-", 1, "teacher_name_digits",
     "'VAE9182' adinin icindeki basamak"),
    ("deviations over seeds ( n = 3", 0, "sample_size",
     "n=3 tohum sayisi -- tasarim, olcum degil"),
    ("0.1008 0.0025 at t = 2.2", 2, "hyperparameter",
     "izgara sicakligi T=2.2"),
    # 21 Agu (jeton final): "in 20 of 21 cells" cumlesi §5'ten CIKTI ("by seed majority
    # ... under all seven estimators" olarak yeniden yazildi); §3'teki 20/21 baglari duruyor.
    ("seven metrics --- NLL Brier equal-width ECE", 0, "benchmark_protocol",
     "kutu sayisi 10 -- olcum protokolu (S2 duzyazisindaki ayni muafiyetin esi)"),
    ("seven metrics --- NLL Brier equal-width ECE", 1, "benchmark_protocol",
     "kutu sayisi 15 -- olcum protokolu"),
    ("seven metrics --- NLL Brier equal-width ECE", 2, "benchmark_protocol",
     "kutu sayisi 25 -- olcum protokolu"),
    ("same temperature in 20 of 21", 1, "sample_size",
     "3 seri x 7 kestirici = 21 hucre; tasarim sayimi"),
    ("the seed-majority rule of supplementary", 0, "table_reference",
     "Supplementary Section S2 atfi"),
    ("seven select t^ * = 1.34 on this teacher", 1, "hyperparameter",
     "kontrol kolunun olceklenmemis noktasi T=1"),
    ("(supplementary table s1)", 0, "table_reference",
     "Supplementary Table S1 atfi"),
    ("in all three seeds) is reported in supplementary", 0, "table_reference",
     "Supplementary Section S2 atfi"),
    # 22 Agu: kill-switch lead'i artik HARFLE ("frozen eight hours before launch") --
    # jeton yok; deger prereg_lead_audit.items.A2 ile tutarli (8.72 sa, floor 8).
    ("predicted a flat-to-shallow response", 0, "hyperparameter",
     "on-beyanin merkezi T=1"),
    ("and no deep interior dip with t = 1.34", 0, "hyperparameter",
     "kontrol kolunun on-beyanli izgara noktasi T=1.34 -- bu ogretmenin KENDI fiti degil, RAF-DB Stage1 fitinin izgara etiketi olarak yeniden kullanimi"),
    # 21 Agu (jeton final): "every departure worsens" cumlesi yeniden yazildi; T=1
    # gecisleri "occurs at t = 1 ( 0.0330" ciftiyle zaten kapsanmakta. VAE9182 adi simdi
    # :71'in sonunda, yeni satir etiketiyle:
    ("observed pattern is stronger", 0, "teacher_name_digits",
     "VAE9182 adinin icindeki basamak"),
    ("occurs at t = 1 ( 0.0330", 0, "hyperparameter",
     "olceklenmemis kol T=1"),
    ("occurs at t = 1 ( 0.0330", 3, "hyperparameter",
     "olceklenmemis kol T=1 (ayni cumlede ikinci gecis)"),
    ("Supplementary Section S2 by seed majority", 0, "table_reference",
     "Supplementary Section S2 atfi (satir basinda; capa S2'nin basamagini icermek zorunda)"),
    ("0.0447 at t = 0.85 on the near side", 1, "hyperparameter",
     "izgara sicakligi T=0.85"),
    ("0.0447 at t = 0.85 on the near side", 3, "hyperparameter",
     "izgara sicakligi T=1.34 (kontrol kolundaki etiket)"),
    ("0.1282 at t = 1.7", 1, "hyperparameter",
     "izgara sicakligi T=1.7"),
    ("0.1282 at t = 1.7", 4, "hyperparameter",
     "izgara sicakligi T=2.2"),
    ("0.15 from the native teacher", 0, "hyperparameter",
     "on-beyanli izgaranin adim genisligi 0.15 (1.00-0.85)"),
    ("t = 0.95 and t = 1.10 (three seeds each", 0, "hyperparameter",
     "sonradan eklenen kolun sicakligi T=0.95"),
    ("t = 0.95 and t = 1.10 (three seeds each", 1, "hyperparameter",
     "sonradan eklenen kolun sicakligi T=1.10"),
    ("of the pre-declared counts) bracket those optima", 0, "hyperparameter",
     "ince izgaranin cozunurlugu 0.05"),
    ("-0.0033 0.0042 at t = 0.95", 2, "hyperparameter",
     "kol sicakligi T=0.95"),
    ("t = 1.10 ( + - + 0.98", 0, "hyperparameter",
     "kol sicakligi T=1.10"),
    ("point-estimate minimum sits at t = 0.95", 0, "hyperparameter",
     "kol sicakligi T=0.95"),
    ("t = 1 ) which is exactly the shape", 0, "hyperparameter",
     "olceklenmemis kol T=1"),
    ("clears -0.0034 --- the mechanism's own", 0, "criterion_constant",
     "kill-switch'in on-beyanli esigi; artefaktta ELLE YAZILMIS sabit (adaptive_t_headroom.block_b_miscalibration_causal.prereg_bar = -0.0034) -- BEYAN, olc"),
    ("worst arm --- were frozen 19", 0, "preregistration_provenance",
     "on-beyan dondurma suresi (19 s)"),
    ("supplementary table s4", 0, "table_reference",
     "Supplementary Table S4 atfi"),
    ("curves (individual seeds:", 0, "table_reference",
     "Supplementary Table S10 atfi"),
    ("individual points gives = 0.789", 1, "criterion_constant",
     "%95 guven duzeyi -- istatistik konvansiyonu"),
    ("Because is fixed at", 0, "hyperparameter",
     "ogrenci tarafi damitma sicakligi tau=6 (21 Agu: 'which.' onceki satira tasindi)"),
    # Capa 21 Agu 2026'da kisaltildi: eski hali 3.06'yi iceriyordu ve makale 3.04'e duzelince
    # iki muafiyet birden dustu (jetonlar KAYITSIZ oldu). "Stage1" tek basina benzersiz DEGIL
    # (iki satir onunla basliyor), o yuzden en kisa benzersiz onek "Stage1 6.0 on" -- yani bu
    # satirda capa bir sayidan (6.0) tamamen kacinamiyor; kacinilamayan sinif, adiyla burada.
    ("stage1 6.0 on", 0, "teacher_name_digits",
     "Stage1 adinin icindeki basamak"),
    ("stage1 6.0 on", 2, "teacher_name_digits",
     "VAE9182 adinin icindeki basamak"),
    ("stage1 teacher at three seeds each", 0, "teacher_name_digits",
     "Stage1 adinin icindeki basamak"),
    ("prediction is falsified in both pairs", 0, "hyperparameter",
     "bilesik sicaklik etiketi T*tau=5.10 (esli izgara noktasinin adi)"),
    ("10.20 by -0.0324", 0, "hyperparameter",
     "bilesik sicaklik etiketi T*tau=10.20 (esli izgara noktasinin adi)"),
    ("t = 1.70 ) and -0.0025", 0, "hyperparameter",
     "kol sicakligi T=1.70"),
    ("t = 1.70 ) and -0.0025", 3, "hyperparameter",
     "kol sicakligi T=0.85"),
    ("inconsistent) whereas holding = 6", 0, "hyperparameter",
     "sabit tutulan tau=6"),
    ("inconsistent) whereas holding = 6", 1, "hyperparameter",
     "kol sicakligi T=0.85"),
    ("to 1.70 shifts it by -0.0349", 0, "hyperparameter",
     "kol sicakligi T=1.70"),
    ("not. the benefit peaks near = 0.5", 0, "hyperparameter",
     "sert etiket agirligi alpha=0.5"),
    ("( +0.0327 ) and then changes sign", 1, "hyperparameter",
     "sert etiket agirligi alpha=0.9"),
    ("holds in 3/3 seeds", 0, "sign_count",
     "3/3 tohum isaret sayimi -- pay"),
    ("holds in 3/3 seeds", 1, "sign_count",
     "3/3 tohum isaret sayimi -- payda"),
    ("= 0.3 used throughout this paper", 0, "hyperparameter",
     "sert etiket agirligi alpha=0.3"),
    ("on raf-db (bootstrap 95 % ci", 0, "criterion_constant",
     "%95 guven duzeyi -- istatistik konvansiyonu"),
    ("ferplus ( [1.64 2.48]", 2, "benchmark_protocol",
     "parametrik bootstrap cekim sayisi 20000 -- olcum protokolu. Binlik ayraci "
     "duzeltilmeden once bu sayi iki jetona bolunuyordu ve iki muafiyet gerekiyordu."),
    ("exclude 1 . averaging all six", 0, "null_value",
     "bootstrap araliginin disladigi NULL deger 1"),
    ("teacher both comparisons' intervals straddle", 0, "null_value",
     "araliklarin kapsadigi NULL deger 1"),
    ("Table S5 and Figure S1) moves", 0, "table_reference",
     "Supplementary Table S5 atfi"),
    ("Table S5 and Figure S1) moves", 1, "table_reference",
     "Supplementary Figure S1 atfi"),
    ("( 0.71 2.25 M all trained from scratch; Supp", 0, "architecture_dim",
     "ogrenci parametre sayisi 0.71 M -- mimari boyutu"),
    ("( 0.71 2.25 M all trained from scratch; Supp", 1, "architecture_dim",
     "ogrenci parametre sayisi 2.25 M -- mimari boyutu"),
    ("the same three temperatures on three arms", 0, "architecture_dim",
     "ogrenci parametre sayisi 0.71 M"),
    ("2.25 m scratch and 2.25 m pre-trained", 0, "architecture_dim",
     "ogrenci parametre sayisi 2.25 M (scratch kol)"),
    ("2.25 m scratch and 2.25 m pre-trained", 1, "architecture_dim",
     "ogrenci parametre sayisi 2.25 M (pre-trained kol)"),
    ("therefore resolvable. (both scratch arms use n = 3", 0, "sample_size",
     "n=3 tohum sayisi"),
    ("therefore resolvable. (both scratch arms use n = 3", 1, "hyperparameter",
     "kol sicakligi T=1"),
    ("therefore resolvable. (both scratch arms use n = 3", 2, "sample_size",
     "n=2 tohum sayisi"),
    ("therefore resolvable. (both scratch arms use n = 3", 3, "hyperparameter",
     "kol sicakligi T=1.7"),
    ("and 2.2 ; the pre-trained arm uses n = 3", 0, "hyperparameter",
     "kol sicakligi T=2.2"),
    ("and 2.2 ; the pre-trained arm uses n = 3", 1, "sample_size",
     "n=3 tohum sayisi"),
    ("arms hold the dose--response with r^ 2", 0, "metric_name_digits",
     "YENI SINIF onerisi: R^2 metrik adindaki us; bir olcum degil, ad/formul parcasi (S1'de benzerleri bugun 'hyperparameter' olarak beyan edilmis, dogru si"),
    ("0.655 ( 0.71 m scratch)", 1, "architecture_dim",
     "ogrenci parametre sayisi 0.71 M"),
    ("0.655 ( 0.71 m scratch)", 3, "architecture_dim",
     "ogrenci parametre sayisi 2.25 M"),
    ("( 2.25 m pre-trained) so initialisation", 0, "architecture_dim",
     "ogrenci parametre sayisi 2.25 M"),
    ("seeds on all three teachers (the vae9182", 0, "teacher_name_digits",
     "VAE9182 adinin icindeki basamak"),
    ("carried three pre-declared predictions", 0, "teacher_name_digits",
     "Stage1 adinin icindeki basamak"),
    ("1 in the harmful direction)", 0, "criterion_constant",
     "on-beyanli sinir 1x kontrol tohum sd'si -- esik tanimi"),
    ("paired t -test at n = 3 gives", 0, "sample_size",
     "n=3 tohum sayisi"),
    ("table s9: at the swa checkpoint", 0, "table_reference",
     "Supplementary Table S9 atfi"),
    ("head and ; supplementary section s5", 0, "table_reference",
     "Supplementary Section S5 atfi"),
    ("calibration on the stage1 teacher consistently", 0, "teacher_name_digits",
     "Stage1 adinin icindeki basamak"),
    ("+-- and -++ against stage1's", 0, "teacher_name_digits",
     "Stage1 adinin icindeki basamak"),
    ("the miscalibrated teacher at n = 2", 0, "sample_size",
     "n=2 tohum sayisi"),
    ("empty: the G", 0, "method_name_digits",
     "YENI SINIF onerisi: G2G (Gaussian-to-Gaussian) yontem adinin icindeki basamak -- olcum degil; teacher_name_digits'in yontem karsiligi"),
    ("stage1 target _logvar", 0, "teacher_name_digits",
     "\\texttt{stage1} hucre etiketindeki basamak"),
    ("(Supplementary Section S", 0, "table_reference",
     "Supplementary Section S5 atfi"),
    ("two-sided p at n = 3 is 0.333", 0, "sample_size",
     "n=3 tohum/ogretmen sayisi"),
    ("two-sided p at n = 3 is 0.333", 1, "criterion_constant",
     "n=3'te iki yanli permutasyon testinin ULASABILECEGI en kucuk p (2/6 = 0.333) -- kombinatorik sabit, bir olcum degil"),
]
for _row, _idx, _cls, _why in EX_05:
    ex("05_results_discussion", -1, _row, _idx, _cls, _why)


# --- §4 veri kumesi buyuklukleri: BINLIK AYRACI duzeltilince baglanabilir oldular ----------
# Bu bes sayi 19 Agu'da `split_identity` uretilirken zaten OLCULMUSTU, ama tarayici `$15{,}339$`
# gibi yazimlari ikiye boluyordu ve jetonlar "15" + "339" olarak kayitsiz kaliyordu. Yani
# eksik olan olcum degil, JETONLASTIRMAYDI (20 Agu'da duzeltildi).
b("04_experiments", -1, "RAF-DB : 15339 images", 0, A_SPL,
  'datasets["RAF-DB"].rows_total', "int", ident="s4.rafdb_rows_total")
b("04_experiments", -1, "12271 training and 3068", 0, A_SPL,
  'datasets["RAF-DB"].n_train', "int", ident="s4.rafdb_n_train")
b("04_experiments", -1, "12271 training and 3068", 1, A_SPL,
  'datasets["RAF-DB"].n_reporting', "int", ident="s4.rafdb_n_reporting")
b("04_experiments", -1, "annotators per image. We use 28259", 0, A_SPL,
  'datasets["FERPlus"].n_train', "int", ident="s4.ferplus_n_train")
b("04_experiments", -1, "canonical train and validation partitions merged", 0, A_SPL,
  'datasets["FERPlus"].n_reporting', "int", ident="s4.ferplus_n_reporting")

# --- §1 katki listesinin madde numaralari + iki ad-icindeki basamak ------------------------
# "(1) ... (5)" bir NUMARALANDIRMADIR; makale bunlari duzyazida da geri cagiriyor
# ("(1) and (2) rest on paired interventions"). Olcum degil, gonderge.
INTRO_ENUM = [("(1) A causal dose", 0), ("(2) Evidence that calibration", 0),
              ("(3) A controlled replication", 0), ("(4) A FER-specific", 0),
              ("(5) A checkpoint-selection", 0),
              ("calibration so unlike (1) it is", 0),
              ("is used. (1) and (2) rest", 0), ("is used. (1) and (2) rest", 1),
              ("asymmetry are post-hoc. (5)", 0),
              ("runs; (3) is observational", 0),
              ("decision rule rather than a causal finding; (4)", 0)]
for _row, _idx in INTRO_ENUM:
    ex("01_introduction", -1, _row, _idx, "enumerator",
       "katki listesinin madde numarasi -- gonderge, olcum degil")
ex("01_introduction", -1,
   "the difference survives distillation into the student. Such distributions", 0,
   "dataset_name_digits", "'CIFAR-10H' veri kumesi adinin icindeki basamak")
ex("abstract", -1, "calibration leaving top-1", 0, "metric_name_digits",
   "'top-1' metrik adinin icindeki basamak -- olcum degil")
b("02_related_work", -1, "sits in this regime", 0,
  "p5_efficiency/capacity_law_check.json", "capacity_cells_at_T1.w100ns.params_m", "2dp",
  ident="related_work.student_params_m")


# "20 of 21 cells" §5'te bir kez daha geciyor. Ayni turetme, ayri jeton -- §3'teki
# `meth.argmin_cells_agreeing` ile ayni operandlar. 21 Agu (jeton final): eskiden IKI gecisti;
# "calibration estimator in 20 of 21 cells" cumlesi §5 dalgasinda yeniden yazildi ve o dv
# SILINDI. Bu olu dv'yi check_numbers GORMUYORDU: `derived_matched_nothing` VIOLATION_KINDS'ta
# degildi (oz sinamanin tabani yakaladi). Sinif ayni gun ihlal listesine eklendi.
for _i, _row in enumerate(("same temperature in 20 of 21",)):
    dv(f"res.argmin_cells_agreeing_{_i}", "20", "sum",
       [op(A_ROB, 'series["RAF-DB stage1"]._consensus_metrics_agreeing'),
        op(A_ROB, 'series["RAF-DB vae9182"]._consensus_metrics_agreeing'),
        op(A_ROB, 'series["FERPlus"]._consensus_metrics_agreeing')],
       "int", "05_results_discussion", -1, _row, 0)


# =============================================================================
# N19b (20 Agu 2026) — SON 23 KAYITSIZ SAYI
# =============================================================================
# Hedef bu turda "kapi yesil" degil, "makalede kaynagi gosterilemeyen sayi kalmasin". Bu blok
# 23 jetonun hepsini beyana baglar. UCU BILEREK KIRMIZI kaliyor ve gerekceleri asagida her
# birinin yaninda yaziyor: uretici basili degeri TUTTURACAK SEKILDE AYARLANMADI; sabit tohumla
# (ve mumkun oldugu yerde kapali formla) kosuldu, cikan yazildi, fark raporlandi.
#
# --- (a) YANLIS-POZITIF SIMULASYONU (§4.7 + §5.3), 7 jeton -----------------------------------
# Bes nicelik, iki yerde: §4.7 uc/dort basamakla, §5.3 iki basamakla. AYNI ALANLARA baglaniyor
# -- §5 icin yeni nicelik ACILMIYOR, cunku ayni buyuklugun iki yazimi ayni buyukluktur.
#
# OLCUM (kritik). Basili 0.543 / 0.740 / 0.007, `criterion_applied`in 200k (aile) ve 40k
# (bagimli) tekrarlik MC kosularindan geliyordu; uretici bugun de ayni tohumla ayni sayilari
# veriyor, yani sayilarin KAYNAGI belli. Ama ayni olcutun yanlis-pozitif orani KAPALI FORMA
# indirgenebiliyor (bkz. `criterion_applied.fpr_exact`) ve tam deger soyle:
#     tek hucre, medyan k : 0.0351548  -> %3.5   (basili 3.5, TUTUYOR)
#     aile 22, medyan k   : 0.5449411  -> 0.545  (basili 0.543, TUTMUYOR: MC gurultusu)
#     aile 22, kendi k'si : 0.7410378  -> 0.741  (basili 0.740, TUTMUYOR)
#     bagimsizlik acigi   : 0.0086132  -> 0.009  (basili 0.007, TUTMUYOR)
# 200k tekrarda aile-bazli oranin standart hatasi ~0.004; yani basili UCUNCU BASAMAK gurultuydu.
# Ucu de TAM alana baglandi ve 20 Agu 2026'da KIRMIZI birakildi: kapinin gormedigi bir kusur,
# kusur degil bir varsayimdir. Iki basamakli §5 gecisleri ayni alanlarda ZATEN TUTUYORDU (0.54
# ve 0.74) -- duzeltme yalnizca uc basamak basilan yerleri ilgilendiriyordu.
# 21 AGU 2026: makalede uc deger de duzeltildi (0.545 / 0.741 / 0.009) ve uc bag YESILE dondu.
# Alanlar DEGISMEDI -- degisen yalnizca basili taraf; yani bag, kendisini dogrulatmak icin
# artefakti oynatmadi. Ureticinin bugunku degeri hala kapali formdan geliyor.
b("04_experiments", -1, "per-cell firing rate of about", 0, A_CRIT,
  "false_positive_simulation.per_cell_rate_at_median_k", "percent_of_fraction:1dp",
  ident="s4.fpr_per_cell")
b("04_experiments", -1, "twenty-two cells the corresponding family-wise probability is", 0,
  A_CRIT, "false_positive_simulation.family_wise_at_median_k", "3dp",
  ident="s4.fpr_family_median_k")
b("04_experiments", -1, "rising to", 0,
  A_CRIT, "false_positive_simulation.family_wise_at_own_k", "3dp",
  ident="s4.fpr_family_own_k")
b("04_experiments", -1, "sharing a control arm correlate at", 0, A_CRIT,
  "false_positive_simulation.rho_shared_control", "3dp", ident="s4.fpr_rho_shared")
b("04_experiments", -1, "re-simulating with that shared component moves the rate by", 0,
  A_CRIT, "false_positive_simulation.independence_gap_own_k_minus_shared", "3dp",
  ident="s4.fpr_independence_gap")
b("05_results_discussion", -1, "reference rate of 0.54 (rising to 0.74", 0, A_CRIT,
  "false_positive_simulation.family_wise_at_median_k", "2dp",
  ident="s5.fpr_family_median_k_2dp")
b("05_results_discussion", -1, "reference rate of 0.54 (rising to 0.74", 1, A_CRIT,
  "false_positive_simulation.family_wise_at_own_k", "2dp", ident="s5.fpr_family_own_k_2dp")

# CAPA KURALI (20 Agu 2026, N19b'de olculdu). Satir capasi, satirin BASINDAN itibaren bir
# ONEKTIR; bagli sayinin kendisi o onegin icine girerse, makale o sayiyi duzelttiginde capa
# eslesmeyi birakir ve jeton `rounding_mismatch` yerine KAYITSIZ dusher. Kapi yine kirmiziya
# doner (kacan bir sey yok) ama teshis yaniltici olur -- ve AYNI satira capalanmis KOMSU
# beyanlar da birlikte dusher. Bu yuzden capa, mumkun oldugunda sayidan ONCE bitirilir.
# Sayi satirin basindaysa (ornek: p-degerinin mantisi, §5:813) bu mumkun degildir; o vakalar
# oz sinamada `unregistered` beklentisiyle yaziliyor, cunku olculen davranis budur.

# --- (b) KOSU MANIFESTI SAYIMLARI (§4.8), 4 jeton --------------------------------------------
# "Hangi 90?" sorusunun cevabi sayimin YANINDA duruyor: `run_manifest_census.window.label`
# alani "17 June--24 July 2026" degerini SAYILAN manifestlerin kendi zaman damgalarindan
# uretiyor, elle yazmiyor. Uc sinif toplandiginda toplami vermeli -- `checksum_ok` bunu
# uretici tarafinda dogruluyor.
#
# 21 AGU 2026 -- CAPA KURALI'NIN ILK SAHA SINAMASI. Fatih §4.8'i yeniden yazdi ("all manifests
# were written retroactively ...; for 26 the code state at launch could be verified"), cunku
# olcum "written at launch" nitelemesinin dar oldugunu gostermisti: `retroactive` bayragi 90'in
# 90'inda acik, ayrimi yapan alan `code_state_verified`. Cumle degisince DORT jeton birden
# dustu: iki capa artik eslesmiyordu (biri sayi iceriyordu, biri silinen ifadeye dayaniyordu)
# ve satir sonlari kaydigi icin `idx=4` diye bir jeton kalmadi. Kural tam da bunu ongoruyordu.
# Yeni capalarin ucu de SAYIDAN ONCE bitiyor.
b("04_experiments", -1, "Of the", 0, A_RMC, "n_manifests", "int",
  ident="s4.manifest_total")
b("04_experiments", -1, "manifests were written retroactively by a single script; for", 0,
  A_RMC, "n_code_state_verified", "int", ident="s4.manifest_verified")
b("04_experiments", -1, "code state at launch could be verified for", 0, A_RMC,
  "n_retroactive_unverified", "int", ident="s4.manifest_retroactive")
b("04_experiments", -1, "(code _state _verified:false) and", 0, A_RMC, "n_unfinished", "int",
  ident="s4.manifest_unfinished")

# --- (c) ALANI OLMAYAN SEKIZ OLCUM ------------------------------------------------------------
# 1-2) En yuksek guven kutusundaki kutle (§5.1). Uretici bu iki sayiyi EKRANA basiyordu ama
#      artefakta yazmiyordu; sayiyi ekrana basmak onu kayda gecirmez.
b("05_results_discussion", -1, "and the mass sitting in the highest-confidence bin falls from",
  0, A_REL, 'conditions["T=1"].top_bin.share_pct', "1dp", ident="s5.top_bin_raw")
b("05_results_discussion", -1, "to 82.7", 0, A_REL,
  'conditions["T=1.3406"].top_bin.share_pct', "1dp", ident="s5.top_bin_calibrated")

# 3) R^2 tabani (§5.4). Bu bir OLCUM degil bir BARAJ: "uc kolun hepsi > 0.998". Belirleyici
#    olan en kucuk R^2 (0.99881781, scratch2248); bag `min` uzerinden ve ASAGI yuvarlamayla
#    kuruluyor. Yariyi yukari yuvarlanmis olsaydi 0.999 cikardi ve cumle YANLIS olurdu.
dv("s5.r2_floor", "0.998", "min",
   [op(A_A13, "fits.scratch0712.r2"), op(A_A13, "fits.scratch2248.r2"),
    op(A_A13, "fits.pretrained2248.r2")],
   "3dp_floor", "05_results_discussion", -1, "arms hold the dose--response with R^ 2 >", 1,
   note="uc kolun EN KUCUK R^2'si; alt sinir iddiasi oldugu icin ASAGI yuvarlanir "
        "(scratch2248 = 0.99881781, digerleri 0.99996+)")

# 4) Taban ECE orani (§5.5). Payda ADIYLA: vae9182 kontrol kolunun @swa ECE duzeyi.
dv("s5.baseline_ece_ratio", "2.7", "ratio_of_mean",
   [op(A_CSM, "rows[checkpoint=swa][axis=ece][teacher=stage1][class_weight_mode=none]"
              ".control_level"),
    op(A_CSM, "rows[checkpoint=swa][axis=ece][teacher=primary][class_weight_mode=none]"
              ".control_level"),
    op(A_CSM, "rows[checkpoint=swa][axis=ece][teacher=vae9182][class_weight_mode=none]"
              ".control_level")],
   "1dp", "05_results_discussion", -1, "2.7 larger than the well-calibrated", 0,
   note="pay = stage1 ve primary kontrol kollarinin @swa ECE duzeylerinin ORTALAMASI (0.075); "
        "PAYDA = vae9182 kontrol kolunun @swa ECE duzeyi (0.0278). Basili iki yuvarlanmis "
        "degerden hesaplansaydi 2.679 cikardi; alanlardan 2.701 cikiyor -- ikisi de 1 basamakta "
        "2.7 veriyor ama hesap alanlardan yapiliyor.")

# 5) Bilesik sicaklik T* x tau (§5.3), UC jeton. Operandlar: kolun KENDI kaydindaki T ve
#    `tau_t_factorial`in kaydindaki tau=6. VAE9182'de operand T*=0.983 DEGIL: cumle
#    "student-side optimum" diyor ve o kolda ogrenci en iyi ECE'yi T=1'de veriyor.
#    FERPlus 20 Agu'da KIRMIZIYDI: 0.5063 x 6 = 3.0378 -> 3.04 iken basili deger 3.06'ydi ve
#    3.06 ancak 0.5063'un iki basamaga yuvarlanmis hali (0.51) ile carpilinca cikiyordu -- yine
#    cift yuvarlama. 21 Agu 2026'da makalede duzeltildi; kampanyanin ucuncu cift yuvarlamasi.
_TAU = op("paper_tables/tau_t_factorial.json", 'arms["tau6_T0.85"].tau')
dv("s5.composite_T_stage1", "8.04", "product",
   [op(A_TDO, "arms.rafdb_stage1.points[2].T"), _TAU],
   "2dp", "05_results_discussion", -1, "optimum lands at composite temperature T^ * =", 0,
   note="stage1 ogrenci-optimum kolu T=1.3406, tau=6 -> 8.0436")
dv("s5.composite_T_vae9182", "6.0", "product",
   [op(A_TDO, "arms.rafdb_vae9182.points[1].T"), _TAU],
   "1dp", "05_results_discussion", -1, "Stage1 6.0 on", 1,
   note="vae9182 ogrenci-optimum kolu T=1 (T*=0.983 DEGIL: ogrencinin en dusuk ECE'si T=1 "
        "kolunda), tau=6 -> 6.0")
dv("s5.composite_T_ferplus", "3.04", "product",
   [op(A_TDO, "arms.ferplus.points[1].T"), _TAU],
   "2dp", "05_results_discussion", -1, "Stage1 6.0 on", 3,
   note="FERPlus ogrenci-optimum kolu T=0.5063, tau=6 -> 3.0378 = 3.04. Basili deger 20 Agu "
        "2026'da 3.06'ydi (CIFT YUVARLAMA: 0.5063 -> 0.51 -> x6); 21 Agu 2026'da makalede "
        "3.04'e duzeltildi ve bag YESILE dondu.")

# 6) DeltaECE, stage1 x target_logvar (§5.5). §5:655'teki 0.0041 ile AYNI SAYI, AYRI NICELIK:
#    o bir JSD farki, bu bir ECE farki. Adlari ayrisiyor (`s5.target_logvar_dece` vs
#    `res.jsd_*`) -- 13-14/13-15 vakasindaki disiplinin aynisi.
b("05_results_discussion", -1, "( = -0.0041 the same sign in all three seeds)", 0, A_CRIT,
  'cells["stage1/gate:target_logvar"].swa.ece.mean', "4dp", ident="s5.target_logvar_dece")

# --- (d) MEKANIK DORT --------------------------------------------------------------------------
# 7) +0.165 (§5.4): uretici degeri 4dp YUVARLANMIS sakliyordu (0.1655) ve defter onu bir kez
#    daha yuvarlayinca 0.166 veriyordu -- makale 0.165 basiyor. Uretici duzeltildi (yuvarlanmamis
#    yaziyor: 0.16546105) ve bag 3dp'de TUTUYOR. Yani makale dogruydu, ARTEFAKT yanlisti.
b("05_results_discussion", -1, "remain over-confident ( +0.063 and +0.165", 1, A_PCC,
  'classes.Fear.gap_mean[4]', "3dp", ident="s5.perclass_gap_fear_T22")

# 8-9) 34 / 67 (§5.4): alan KESIR, makale YUZDE. Yeni kip `percent_of_fraction`. Sayimin
#      kendisi de artik alan: 45/131 ve 88/131.
b("05_results_discussion", -1, "inside the last K in", 0, A_SG,
  'per_k["50"].argmax_in_last_K_frac', "percent_of_fraction:int", ident="s5.argmax_in_k50")
b("05_results_discussion", -1, "inside the last K in", 1, A_SG,
  'per_k["100"].argmax_in_last_K_frac', "percent_of_fraction:int", ident="s5.argmax_in_k100")

# 10) 4.3 (§5.5): bilimsel gosterimin MANTISI. Us (-7) da AYNI ALANA baglaniyor -- daha once
#     "gosterimden dogan jeton" diye muaf tutulmustu, ama us bir yazim susu degil, alanin
#     olculebilir bir ozelligi. Taban (10) muaf kaliyor: o gercekten gosterimin kendisi.
b("05_results_discussion", -1, "4.3 10^ -7 on RAF-DB", 0, A_SAI,
  'datasets["RAF-DB"].contrasts["best-swa"].acc_pp.p', "sci_mantissa:1dp",
  ident="s5.best_swa_p_mantissa")
b("05_results_discussion", -1, "4.3 10^ -7 on RAF-DB", 2, A_SAI,
  'datasets["RAF-DB"].contrasts["best-swa"].acc_pp.p', "sci_exponent",
  ident="s5.best_swa_p_exponent")


# =============================================================================
# N19d (21 Agu 2026, jeton final) -- 03:31'den sonra degisen metnin baglari
# =============================================================================
# (1) SS4.1: FERPlus etiket yayimimizin HAM fold sayimlari. Eski cumle kanonik yayinin
#     sayilarini aktariyordu (28,709/3,589 -- citation muafiyeti); yeni cumle BIZIM
#     kopyamizin olcumunu soyluyor ve olcum split_identity'de zaten alandi. Reviewer zinciri:
#     ham 28559/3579/3573 -> cogunluk-oyu suzgeci -> 25060/3199/3153 -> egitim 28259 (fold0+1)
#     + raporlama 3153. CAPA KURALI notu: satir sayilarla BASLIYOR, capa onlari icermek
#     zorunda (p-degeri mantisi sinifi); oz sinamada beklenti bu yuzden `unregistered` olur.
b("04_experiments", -1, "measures", 0, A_SPL,
  'datasets["FERPlus"].unfiltered_by_fold["0"]', "int", ident="s4.ferplus_raw_fold0")
b("04_experiments", -1, "measures", 1, A_SPL,
  'datasets["FERPlus"].unfiltered_by_fold["1"]', "int", ident="s4.ferplus_raw_fold1")
b("04_experiments", -1, "measures", 2, A_SPL,
  'datasets["FERPlus"].unfiltered_by_fold["2"]', "int", ident="s4.ferplus_raw_fold2")

# (2) SS4.6: on-beyan lead araliginin iki ucu. Alt uc TURETILMIS: alti lead'in MINIMUMU
#     (cumle "ranging from ... to ..." diyor, yani iddia min/max'tir; A4'un 18 s'i bugun
#     minimum ama yarin baska kalem eklenirse cumleyi min korur, tek-alan bagi korumazdi).
#     Ust uc A8'in kendi alani. Ikisi de `int_floor`. Satir 18 ile basliyor -> capa sayi icerir.
dv("s4.prereg_lead_min", "18", "min",
   [op(A_PL, "items.A1.lead_seconds"), op(A_PL, "items.A2.lead_seconds"),
    op(A_PL, "items.A3.lead_seconds"), op(A_PL, "items.A4.lead_seconds"),
    op(A_PL, "items.A7.lead_seconds"), op(A_PL, "items.A8.lead_seconds"),
    op(A_PL, "items.A9.lead_seconds")],
   "int_floor", "04_experiments", -1, "18 s to 12 h (intervals", 0,
   note="lead-tasiyan on-beyanlarin en kisasi = A4 (human-alignment), 18 s; saniyeler "
        "tamsayi-kesin oldugu icin floor==deger. 27 Agu (EK-1): A9 (108 s) kumeye girdi, "
        "min degismedi")
b("04_experiments", -1, "18 s to 12 h (intervals", 1, A_PL,
  "items.A8.lead_hours", "int_floor", ident="s4.prereg_lead_max_h")

# (3) SS3.4: headroom'un ikinci +0.0232 gecisi -- ILK gecisle (meth.stage1_headroom_point_boot,
#     SS3:325) AYNI alana baglanir; ayni buyuklugun iki yazimi ayni buyukluktur (N19b kurali).
b("03_methodology", -1, "bootstrap above gives", 0, A_BOOT,
  "results.stage1.point.headroom_eq8", "4dp", ident="meth.stage1_headroom_point_boot2")

# (4) fig_perclass (YENI BIRIM, 21 Agu 2026): figur altyazilari kapsam DISIYDI; F3/F5
#     bulgulari (baslik metni + 10.5) uzerine fig_perclass.tex tarayiciya girdi. Tek jeton
#     tasir: sinyal/gurultu tabani. "at least" bir ALT SINIR iddiasidir -> `1dp_floor`
#     (0.998 ile ayni kip). Olculdu: min = Disgust 10.5557 -> 10.5; yari-yukari 10.6 verirdi
#     ve 20 Agu'ya kadar basili deger tam da oydu (F5 bulgusu) -- perclass_calibration'in
#     docstring'i de ayni yari-yukari degeri tasiyordu, duzeltildi.
dv("figp.snr_floor", "10.5", "min",
   [op(A_PCC, "classes.Surprise.range_over_seed_sd"),
    op(A_PCC, "classes.Fear.range_over_seed_sd"),
    op(A_PCC, "classes.Disgust.range_over_seed_sd"),
    op(A_PCC, "classes.Happiness.range_over_seed_sd"),
    op(A_PCC, "classes.Sadness.range_over_seed_sd"),
    op(A_PCC, "classes.Anger.range_over_seed_sd"),
    op(A_PCC, "classes.Neutral.range_over_seed_sd")],
   "1dp_floor", "fig_perclass", -1, "deviation) is at least", 0,
   note="yedi sinifin en kucuk (araligin tohum sd'sine orani) = Disgust 10.5557; alt sinir "
        "iddiasi oldugu icin ASAGI yuvarlanir")

# =============================================================================
# N20 (22 Agu 2026, defter final2) -- uc dalga + S12'nin ureticiye baglanmasi
# =============================================================================
# (1) SS5.9: SS4.4'ten tasinan denetim buyume sayilari. Satir sayilarla basliyor ->
#     "125 to the frozen" capasi sayi icermek zorunda (kacinilamayan sinif).
b("05_results_discussion", -1, "insensitive to the inclusion set", 0,
  "selection_audit/selection_optimism_headline.json",
  "stability_across_inclusion_sets.series[0].n", "int", ident="s5.audit.growth_n116")
b("05_results_discussion", -1, "125 to the frozen", 0,
  "selection_audit/selection_optimism_headline.json",
  "stability_across_inclusion_sets.series[1].n", "int", ident="s5.audit.growth_n125")
b("05_results_discussion", -1, "125 to the frozen", 1,
  "selection_audit/selection_optimism_headline.json",
  "stability_across_inclusion_sets.series[2].n", "int", ident="s5.audit.growth_n131")
b("05_results_discussion", -1, "125 to the frozen", 2,
  "selection_audit/selection_optimism_headline.json",
  "stability_across_inclusion_sets.span_pp", "2dp", ident="s5.audit.growth_span_pp")

# (2) SS3 giris: iki ad-basamagi yeni cumlelerde.
ex("03_methodology", -1, "stated where they appear", 0, "teacher_name_digits",
   "Stage1 adinin icindeki basamak")
ex("03_methodology", -1, "Primary and VAE", 0, "teacher_name_digits",
   "VAE9182 adinin icindeki basamak")

# (3) SS5'te yeni/tasinan tekil muafiyetler.
ex("05_results_discussion", -1, "term =", 0, "hyperparameter",
   "sert etiket agirligi alpha=0.3 (sabit-nokta cumlesi)")
ex("05_results_discussion", -1, "0.0004 ). The T =", 1, "hyperparameter",
   "insan-hizali kol etiketi T=0.74 (capa ayni satirdaki bagli 0.0004'u icermek zorunda)")

# (4) "tables" birimi (supplementary app:tables duzyazisi): gecikme protokolu + fp16.
#     SS4/SS5'ten tasinan metnin muafiyetleri; fp16 turetmeleri de bu birime tasindi.
ex("tables", -1, "Inference latency is measured on GPU", 0, "benchmark_protocol",
   "GPU isinma yinelemesi sayisi 50; olcum protokolu")
ex("tables", -1, "followed by", 0, "benchmark_protocol",
   "GPU zamanlanmis yineleme sayisi 200")
ex("tables", -1, "followed by", 1, "dtype_name", "fp32 veri tipi adi")
ex("tables", -1, "followed by", 2, "dtype_name", "fp16 veri tipi adi")
ex("tables", -1, "torch.cuda.synchronize()) and on CPU", 0, "benchmark_protocol",
   "CPU isinma yinelemesi sayisi 5")
ex("tables", -1, "20 timed iterations", 0, "benchmark_protocol",
   "CPU zamanlanmis yineleme sayisi 20 (capa satir basindaki sayiyi icerir)")
ex("tables", -1, "20 timed iterations", 1, "dtype_name", "fp32 veri tipi adi")
ex("tables", -1, "batch sizes", 0, "hyperparameter", "olcum yigin boyutu b=1")
ex("tables", -1, "batch sizes", 1, "hyperparameter", "olcum yigin boyutu b=32")
ex("tables", -1, "Half precision at batch", 0, "hyperparameter",
   "paragraf basligindaki yigin boyutu b=1")
ex("tables", -1, "Contradicting a common recommendation", 0, "benchmark_protocol",
   "olcum protokolu: batch 1")
ex("tables", -1, "independent measurement sessions (", 2, "dtype_name",
   "fp32 veri tipi adinin icindeki basamak")
ex("tables", -1, "latency) while at batch", 0, "hyperparameter",
   "olcum yigin boyutu b=32")

# (5) tab_collapse kurucu degerleri: tau=3 ve tau=12 makalede ILK KEZ basiliyor; dordu de
#     tau_t_factorial'in KENDI kayitlarina bagli (T11'in esli karsilastirma kollari).
for _r, _arms in (("( = 3 T = 1.70", ("tau3_T1.70", "tau6_T0.85")),
                  ("( = 6 T = 1.70", ("tau6_T1.70", "tau12_T0.85"))):
    for _j, _a in enumerate(_arms):
        b("tab_collapse", 0, _r, 2 * _j, "paper_tables/tau_t_factorial.json",
          f'arms["{_a}"].tau', "int", ident=f"tab_collapse.pair.{_a}.tau")
        b("tab_collapse", 0, _r, 2 * _j + 1, "paper_tables/tau_t_factorial.json",
          f'arms["{_a}"].T', "2dp", ident=f"tab_collapse.pair.{_a}.T")

# (6) tab_mechanisms dipnotu artik S12'ye de atif veriyor (idx16 = 'S12'nin 12'si).
ex("tab_mechanisms", 0, "§header", 16, "table_reference",
   "Supplementary Table S12 capraz referansi")

# (7) S12 -- tab_app_paired_sd (URETILMIS dosya): 17 satir x 4 deger, hepsi T5'in
#     MEVCUT alanlarina bagli (tab_mechanisms ile ayni hucreler + sd'leri). Uretici
#     paper_tables.py'nin kendisi; elle blok 22 Agu'da \input ile degisti ve takas
#     oncesi 68 hucre elle blokla karsilastirildi: 68/68 birebir.
S12_ROWS = [("Stage1", "stage1", [("adaptive temperature", "adaptive_t"),
                                  ("G2G", "g2g_kl"),
                                  ("gate: mean logvar", "gate:mean_logvar"),
                                  ("gate: target logvar", "gate:target_logvar"),
                                  ("gate: oracle error", "gate:oracle_error"),
                                  ("logit standardisation", "logit_std")]),
            ("Primary", "primary", [("adaptive temperature", "adaptive_t"),
                                    ("G2G", "g2g_kl"),
                                    ("gate: mean logvar", "gate:mean_logvar"),
                                    ("gate: target logvar", "gate:target_logvar"),
                                    ("gate: oracle error", "gate:oracle_error"),
                                    ("logit standardisation", "logit_std")]),
            ("VAE9182", "vae9182", [("adaptive temperature", "adaptive_t"),
                                    ("G2G", "g2g_kl"),
                                    ("gate: mean logvar", "gate:mean_logvar"),
                                    ("gate: oracle error", "gate:oracle_error"),
                                    ("logit standardisation", "logit_std")])]
for _T, _t, _mechs in S12_ROWS:
    for _name, _mech in _mechs:
        _row = f"{_T} {_name}"
        _cell = f'T5_mechanisms["{_t}/{_mech}"].swa'
        b("tab_app_paired_sd", -1, _row, 0, A_RT, f"{_cell}.d_acc_mean", "2dp",
          ident=f"tab_paired.{_t}.{_mech}.d_acc_mean")
        b("tab_app_paired_sd", -1, _row, 1, A_RT, f"{_cell}.d_acc_sd", "2dp",
          ident=f"tab_paired.{_t}.{_mech}.d_acc_sd")
        b("tab_app_paired_sd", -1, _row, 2, A_RT, f"{_cell}.d_ece_mean", "4dp",
          ident=f"tab_paired.{_t}.{_mech}.d_ece_mean")
        b("tab_app_paired_sd", -1, _row, 3, A_RT, f"{_cell}.d_ece_sd", "4dp",
          ident=f"tab_paired.{_t}.{_mech}.d_ece_sd")
ex("tab_app_paired_sd", -1, "paired-difference seed standard deviations", 0, "sample_size",
   "n=3 tohum sayisi (altyazi)")

# (8) SS5 giris: kontrolun on-beyani artik SS5'te de anilir ("frozen 20 s before") -- ve
#     bu bir MUAFIYET degil BAG: A1'in lead'i prereg_lead_audit'te alan (int_floor; saniye
#     tamsayi-kesin, floor==deger). Ayni cumle sinifindan iki kalinti muafiyet asagida.
b("05_results_discussion", -1, "The control's pre-declaration (frozen", 0, A_PL,
  "items.A1.lead_seconds", "int_floor", ident="s5.control_prereg_lead_s")
ex("05_results_discussion", -1, "measurement protocol and a reproduced batch", 0,
   "benchmark_protocol", "olcum protokolu: batch-1 ('-1' jetonu ad ekinden)")
ex("05_results_discussion", -1, "are reported alongside Supplementary Table S", 0,
   "table_reference", "Supplementary Table S7 capraz referansi")

# N22 (23 Agu 2026, bant bosluk turu). `fig_reliability` altyazisindaki ortalama guven
# ciftinin kaydi YOKTU. Altyazilar kapsam disi (BEYAN, kusur degil) -- kapsami acmadan
# baglanabilecegi tek yol `pv`: cumle tek tek beyan edilir, denetci O SATIRI okur ve alanin
# yuvarlanmis degerinin orada gectigini dogrular. Alan zaten artefaktta duruyordu
# (`pooled_mean_conf`), yalniz beyan edilmemisti. Aritmetik de tutuyor (acc + signed_gap)
# ama TURETME degil dogrudan ALAN baglandi: turetme, var olan bir alani yeniden hesaplamak
# olurdu.
pv("fig_reliability.mean_conf_native", A_REL, 'conditions["T=1"].pooled_mean_conf', "3dp",
   "figures/fig_reliability.tex#and mean confidence falls from",
   note="ogrenci ortalama top-1 guveni, dogal ogretmen kolunda (@SWA, uc tohum havuzlanmis)")
pv("fig_reliability.mean_conf_prescaled", A_REL,
   'conditions["T=1.3406"].pooled_mean_conf', "3dp",
   "figures/fig_reliability.tex#and mean confidence falls from",
   note="ayni nicelik, ogretmen T*'ye on-olceklenmis kolda")

# =============================================================================
# N21 (22 Agu 2026, defter final3) -- ISARET DESENLERI
# =============================================================================
# NEDEN BU TURDA. Ligatur duzeltmesi (`[--+]` -> `[-{}-+]`) tam bu desenlere dokundu ve
# olcum sunu gosterdi: desenler HICBIR kapinin gorus alaninda degildi. Rakam tasimadiklari
# icin sayi ayiklayici onlari gormuyor; tablo farki kapisi artefakt-artefakt karsilastirir,
# basili metne bakmaz. Yani `[+++]` -> `[++-]` gibi bir bozulma butun kapilardan sessizce
# gecerdi. Oysa her desen bir VERI iddiasi: tohum basina farkin isaretleri. Artefaktta
# zaten var (`d_ece_signs` / `d_acc_signs`), yalniz beyan edilmemisti.
# 17'si tabloda (ECE ekseni, @SWA -- dipnotun dedigi gibi), 7'si §5 duzyazisinda.
SIGN_ROWS = [("Adaptive temperature", ("stage1/adaptive_t", "primary/adaptive_t",
                                       "vae9182/adaptive_t")),
             ("G2G (class-space KL)", ("stage1/g2g_kl", "primary/g2g_kl", "vae9182/g2g_kl")),
             ("Gate mean logvar", ("stage1/gate:mean_logvar", "primary/gate:mean_logvar",
                                   "vae9182/gate:mean_logvar")),
             # VAE9182'de target-logvar gecidi elenmisti: o hucre `---` basiyor, deseni yok.
             ("Gate target logvar", ("stage1/gate:target_logvar",
                                     "primary/gate:target_logvar")),
             ("Gate oracle error", ("stage1/gate:oracle_error", "primary/gate:oracle_error",
                                    "vae9182/gate:oracle_error")),
             ("Logit standardisation", ("stage1/logit_std", "primary/logit_std",
                                        "vae9182/logit_std"))]
for _row, _cells in SIGN_ROWS:
    for _i, _c in enumerate(_cells):
        sg("tab_mechanisms", -1, _row, _i, A_RT, f'T5_mechanisms["{_c}"].swa.d_ece_signs',
           "tohum basina DeltaECE isaretleri (@SWA)", ident=f"sign.T5.{_c}")

# §5 duzyazisi ayni desenlere adiyla atif veriyor. Ucunde capa desenle BASLIYOR (satir basi);
# kacinilamayan sinif -- normalizasyon sayesinde capa basili bicime gore sabit.
sg("05_results_discussion", -1, "-++ on both", 0, A_RT,
   ['T5_mechanisms["stage1/gate:oracle_error"].swa.d_ece_signs',
    'T5_mechanisms["primary/gate:oracle_error"].swa.d_ece_signs'],
   "iki asiri-guvenli ogretmende AYNI desen -- cumle 'on both' diyor, iki alan da esit olmali",
   ident="sign.s5.oracle_both")
for _i, _c in enumerate(("primary/g2g_kl", "vae9182/g2g_kl", "stage1/g2g_kl")):
    sg("05_results_discussion", -1, "+-- and -++ against Stage1's", _i, A_RT,
       f'T5_mechanisms["{_c}"].swa.d_ece_signs',
       "G2G'nin tekrarlanmadigi cumlesi: iki ogretmende isaretler ayrisiyor",
       ident=f"sign.s5.g2g.{_c}")
sg("05_results_discussion", -1, "third seed completes", 0, A_RT,
   'T5_mechanisms["stage1/adaptive_t"].swa.d_ece_signs',
   "eslesen ucuncu tohum tamamlaninca uyarlanan sicakligin isaretleri",
   ident="sign.s5.adaptive_stage1")
sg("05_results_discussion", -1, "--+: here the magnitude", 0, A_RT,
   'T5_mechanisms["vae9182/adaptive_t"].swa.d_ece_signs',
   "iyi kalibre ogretmende buyukluk esigi geciyor, isaret testi gecmiyor",
   ident="sign.s5.adaptive_vae")
# Bu TEK desen ECE degil DOGRULUK eksenine ait ("its accuracy axis fails the complementary
# condition"): alan `d_acc_signs`. Yanlis eksene baglamak sessiz bir yanlis bag olurdu.
sg("05_results_discussion", -1, "magnitude ( 2.51 ) but not the sign test", 0, A_RT,
   'T5_mechanisms["stage1/gate:target_logvar"].swa.d_acc_signs',
   "hedef-logvar gecidinin DOGRULUK ekseni: tamamlayici kosul isaret testinde dusuyor",
   ident="sign.s5.target_logvar_acc")

# =============================================================================
# TEYIT KAYITLARI (cross_checks) — ayni niceligi hesaplayan IKINCI kaynak
# =============================================================================
# NEDEN VAR (17 Agu 2026, N14 karari). T*_NLL'i iki BAGIMSIZ uygulama buluyor ve degerler
# 1e-5..1e-4 duzeyinde ayrisiyor. Gun boyu kovaladigimiz hastalik "ayni ad, iki farkli nicelik"ti;
# bu onun TERSI -- iki farkli hesap AYNI niceligi buluyor. Karar: BIRLESTIRME, ILAN ET. Kanonik
# kaynak beyan edilir, ikinci kaynak TEYIT olarak kaydedilir, ve ayrisma bir ESIGE baglanir ki
# bugun sessiz olan sey yarin SINYAL olsun.
#
# TOLERANS ELLE YAZILMAZ, MAKALENIN KENDI HASSASIYETINDEN TURETILIR:
#     tol = 0.5 x 10^(-d),  d = o niceligin makalede kullanildigi EN SIKI yuvarlama
# Yani "iki kaynak, basilan hicbir hucreyi degistirmeyecek kadar yakin olmali". Kucuk bir
# sabit uydurmaktan iyidir: esik, tablolar degistiginde kendiliginde siklasir/gevser.
# Ikinci ve daha keskin kapi yapisaldir: iki kaynak, o yola bagli HER hucrenin beyan edilen
# yuvarlamasinda AYNI degere yuvarlanmali.
def xc(ident, quantity, canonical, confirm, relays, why):
    CROSS_CHECKS.append({"id": ident, "quantity": quantity, "canonical": canonical,
                         "confirm": confirm, "relays": relays, "why": why})


for _t in ("stage1", "primary", "vae9182"):
    xc(f"tstar_nll.{_t}", f"T*_NLL ({_t}, tam fold)",
       (A_TSS, f"results.{_t}.T_star_nll"), (A_TEG, f"{_t}.T_star"),
       [(A_P4, f"recipe_step3_ranking.rows[teacher={_t}].T_star"),
        (A_TSP, f"full_fold_fits.{_t}")],
       why="kanonik `student_ts_baseline.fit_ts` (log-uzay Brent, kampanyanin dagittigi fit); "
           "teyit `teacher_ece_grid.fit_temperature` (bagimsiz uygulama). p4 ve tstar_provenance "
           "teyit degerini AYNEN roleliyor, dolayisiyla uc artefakt IKI hesap tasiyor. Amac "
           "farki `tstar_sensitivity.results.<t>.cross_fit.d_nll` altinda olculuyor.")


# =============================================================================
# ROUND-6 (28 Agu 2026) — K1 / K5 / K6 jetonlari
# =============================================================================
# Metin dalgasi §5.7'ye iki paragraf, S11'e bir cumle ekledi. Uc kural bu blokta gorunur
# duruyor: (a) her oranin paydasi artefaktta ADIYLA yaziyor ve bag o alana gidiyor; (b)
# "tohum basina" iddialari ORTALAMA alanina baglanmiyor -- her biri kendi sayim alanina;
# (c) basili yuvarlanmis degerden turetme yok, fark artefaktin icinde hesaplaniyor.
#
# (b) neden ayri bir kural: §5.7 "the T*_ECE arm worst (0.0296, ALL THREE SEEDS)" diyor.
# Defterde hazir duran `untreated_beats_tstar_ece_scaled` de 3/3'tu -- ama o BASKA bir soru
# ("islenmemis kol T*'i geciyor mu"). Degeri tesadufen esit olan bir alana baglanmasin diye
# uretici `tstar_ece_worst_of_all_scaled` alanini acti. Ayni sebeple K5'te
# `dose_ordered_per_seed` ve `tstar_vs_native.*.tstar_beats_native_per_seed` acildi.

# --- K1: FERPlus ogrenci-tarafi olcekleme, ECE ekseni (§5.7)
b("05_results_discussion", -1, "6.4 (removing 84.3 % of it", 0, A_FSE,
  "collapse.ece.factor", "1dp", ident="s57.ece_collapse_factor")
b("05_results_discussion", -1, "6.4 (removing 84.3 % of it", 1, A_FSE,
  "removal.ece.spread_removed_frac", "percent_of_fraction:1dp",
  ident="s57.ece_spread_removed_pct")
b("05_results_discussion", -1, "the 37 jsd collapse below)", 0, A_FSE,
  "collapse.jsd.factor", "int", ident="s57.jsd_collapse_ref")
b("05_results_discussion", -1, "( 0.0203 ; best in two of three seeds)", 0, A_FSE,
  "scaled_best_arm.ts_ece[0]", "4dp", ident="s57.scaled_best_ece")
b("05_results_discussion", -1, "the t^ * _ ece arm worst ( 0.0296", 0, A_FSE,
  "scaled_worst_arm.ts_ece[0]", "4dp", ident="s57.scaled_worst_ece")

# --- K5: RAF-DB ogrenci-tarafi olcekleme (§5.7, bolum sorusu)
b("05_results_discussion", -1, "removes 82 -- 90 % of the between-arm spread", 0, A_RTD,
  "collapse.stage1.spread_removed_frac", "percent_of_fraction:int",
  ident="s57.rafdb_removed_stage1")
b("05_results_discussion", -1, "removes 82 -- 90 % of the between-arm spread", 1, A_RTD,
  "collapse.vae9182.spread_removed_frac", "percent_of_fraction:int",
  ident="s57.rafdb_removed_vae")
b("05_results_discussion", -1, "ordering survives: stage1's scaled optimum remains", 1, A_RTD,
  "seed_consistency.stage1.scaled_best_T", "4dp", ident="s57.rafdb_stage1_scaled_best_T")
b("05_results_discussion", -1, "dose-consistent residuals of 0.0103 and 0.0187", 0, A_RTD,
  'spans["stage1/ts"].span', "4dp", ident="s57.rafdb_residual_stage1")
b("05_results_discussion", -1, "dose-consistent residuals of 0.0103 and 0.0187", 1, A_RTD,
  'spans["vae9182/ts"].span', "4dp", ident="s57.rafdb_residual_vae")
b("05_results_discussion", -1, "that stage1's t^ * -versus-native scaled gap shrinks to", 1,
  A_RTD, "tstar_vs_native.stage1.gap_scaled", "4dp", ident="s57.rafdb_tstar_native_gap")

# --- K6: sonlu-oy teyidi (S11 duzyazisi, birim `robust`)
b("robust", -1, "stratum places t^ * _ jsd at 0.88 against 0.74", 0, A_JSD,
  'results["(c) stratum 6-7"].T_jsd', "2dp", ident="s11.tjsd_stratum67")
b("robust", -1, "stratum places t^ * _ jsd at 0.88 against 0.74", 1, A_JSD,
  'results["(c) stratum 8-9"].T_jsd', "2dp", ident="s11.tjsd_stratum89")

# --- Ayni turetme, ikinci jeton: `76` artik tab_capacity ALTYAZISINDA da geciyor (28 Agu).
# Dipnottaki gecis (CAP_FOOT idx 3) yerinde duruyor; bu ikincisi ayni iki alandan.
dv("capacity_vs_teacher_lever_caption", "76", "ratio",
   [op(A_RT, "T10_axis_spans.swa.teacher_span"),
    op(A_RT, "T10_axis_spans.swa.capacity_span")],
   "int", "tab_capacity", -1, "student's calibration by far more --- a factor of 76", 0,
   note="tab_capacity altyazisi: 'a factor of 76 on this grid'")

# --- §5.2: asimetri araligi burada IKI basamakla basiliyor (ozet ve girinte 1dp: "1.8--2.0").
# Ayni iki alan, ayri jeton, farkli yuvarlama; yuvarlama beyanda duruyor, sessiz donusum yok.
b("05_results_discussion", -1, "response is asymmetric --- 1.77 / 2.04", 0, A_ASY,
  "summary.interpolated_only.absolute.min", "2dp", ident="s52.asymmetry_min_2dp")
b("05_results_discussion", -1, "response is asymmetric --- 1.77 / 2.04", 1, A_ASY,
  "summary.interpolated_only.absolute.max", "2dp", ident="s52.asymmetry_max_2dp")

# --- Round-6 dalgasinin olcum-olmayan jetonlari
R6_EX = [
    ("05_results_discussion", "makes the dissociation conservative (supplementary section s2)",
     0, "table_reference", "Supplementary Section S2 atfi"),
    ("05_results_discussion", "ordering survives: stage1's scaled optimum remains", 0,
     "teacher_name_digits", "'Stage1' ogretmen adinin icindeki basamak"),
    ("05_results_discussion", "and vae9182 stays dose-ordered in all three seeds", 0,
     "teacher_name_digits", "'VAE9182' ogretmen adinin icindeki basamak"),
    ("05_results_discussion", "that stage1's t^ * -versus-native scaled gap shrinks to", 0,
     "teacher_name_digits", "'Stage1' ogretmen adinin icindeki basamak"),
    ("04_experiments", "denominator at n = 3 both figures are lower bounds", 0,
     "sample_size", "n=3 tohum sayisi -- tasarim, olcum degil"),
    # S11'in sonlu-oy cumlesi: kesitin TANIMI (oy toplami [6,7]), esik degil olcum degil.
    # Kaynak: jsd_sensitivity.json results["(c) stratum 6-7"].why == "vote sum in [6, 7]".
    ("robust", "stratum table shows the predicted effect --- the 6 -- 7 -vote", 0,
     "criterion_constant", "kesit tanimi: oy toplami alt siniri 6 (jsd_sensitivity .why)"),
    ("robust", "stratum table shows the predicted effect --- the 6 -- 7 -vote", 1,
     "criterion_constant", "kesit tanimi: oy toplami ust siniri 7 (jsd_sensitivity .why)"),
]
for _u, _row, _idx, _cls, _why in R6_EX:
    ex(_u, -1, _row, _idx, _cls, _why)


# =============================================================================
# COZUMLEYICI + YUVARLAMA
# =============================================================================
class Unresolved(Exception):
    pass


def _seg(path):
    """Yol ayristirici: `a.b[0].c`, `a["0.1"].b`, `rows[k=v][k2=v2].f`."""
    out, i, n = [], 0, len(path)
    buf = ""
    while i < n:
        c = path[i]
        if c == ".":
            if buf:
                out.append(("key", buf))
                buf = ""
            i += 1
        elif c == "[":
            if buf:
                out.append(("key", buf))
                buf = ""
            j = path.index("]", i)
            inner = path[i + 1:j]
            if inner.startswith('"') and inner.endswith('"'):
                out.append(("key", inner[1:-1]))
            elif "=" in inner:
                k, v = inner.split("=", 1)
                out.append(("sel", (k, v)))
            else:
                out.append(("idx", int(inner)))
            i = j + 1
        else:
            buf += c
            i += 1
    if buf:
        out.append(("key", buf))
    return out


def resolve(store, artifact, path):
    """Artefakt alanini coz. `a - b` bicimi iki alanin farkidir (turetilmis pay/payda)."""
    if " - " in path:
        a, bb = path.split(" - ", 1)
        return resolve(store, artifact, a.strip()) - resolve(store, artifact, bb.strip())
    cur = _lookup(store, artifact, path)
    if isinstance(cur, bool) or not isinstance(cur, (int, float)):
        raise Unresolved(f"{path}: sayi degil ({type(cur).__name__})")
    return float(cur)


def resolve_text(store, artifact, path):
    """Ayni yol dilbilgisi, METIN alani icin (isaret desenleri). Sayi cozucuyle AYNI
    yurutucuyu kullanir -- iki ayri yol ayristiricisi iki ayri davranis demek olurdu."""
    cur = _lookup(store, artifact, path)
    if not isinstance(cur, str):
        raise Unresolved(f"{path}: metin degil ({type(cur).__name__})")
    return cur


def _lookup(store, artifact, path):
    if artifact not in store:
        p = D / artifact
        if not p.exists():
            raise Unresolved(f"artefakt yok: {artifact}")
        store[artifact] = json.loads(p.read_text(encoding="utf-8"))
    cur = store[artifact]
    for kind, val in _seg(path):
        # Zincirli seciciler SUZER (tek satira indirmez): `rows[a=x][b=y][c=z]` uc kosulu
        # birlikte uygular. Bir alan erisimi geldiginde liste tek elemanliysa acilir; degilse
        # beyan belirsizdir ve DURUR -- "ilkini al" sessiz bir yanlis bag uretirdi.
        if kind == "key" and isinstance(cur, list):
            if len(cur) != 1:
                raise Unresolved(f"{path}: alan erisimi {len(cur)} satirda belirsiz")
            cur = cur[0]
        try:
            if kind == "key":
                cur = cur[val]
            elif kind == "idx":
                cur = cur[val]
            else:
                k, v = val
                if isinstance(cur, dict):
                    cur = [dict(x, **{"__key": kk}) for kk, x in cur.items()]
                if k == "rank":
                    cur = [cur[int(v)]]
                else:
                    cur = [x for x in cur if str(x.get(k, x.get("__key"))) == v]
                if not cur:
                    raise Unresolved(f"secici {k}={v} hicbir satir sectmedi")
        except Unresolved:
            raise
        except Exception as e:
            raise Unresolved(f"{path}: {type(e).__name__} ({kind} {val})")
    if isinstance(cur, list) and len(cur) == 1:
        cur = cur[0]
    return cur


def fmt_round(value, rounding):
    """Beyan edilen yuvarlama. Varsayilan YARIYI YUKARI (LaTeX'te elle yazilan sayi boyle
    yuvarlanir). Dort ek KIP var; hepsi "alan ile basili deger ayni YAZIMDA degil" vakasi
    icin ve hepsi beyanda ACIKCA yaziliyor -- sessiz bir donusum yok.

      percent_of_fraction[:kip]  alan KESIR (0.3435), makale YUZDE basiyor (34). Once 100 ile
                                 carpilir, sonra verilen kiple yuvarlanir. Varsayilan `int`.
      sci_mantissa[:kip]         alan tam p degeri (4.256e-07), makale MANTISI basiyor (4.3).
                                 Varsayilan `1dp`.
      sci_exponent               ayni alanin USSU (-7). Us TAM SAYIDIR, yuvarlama yok.
      <kip>_floor                ALT SINIR iddiasi. "R^2 > 0.998" cumlesinde basili sayi bir
                                 olcum degil bir BARAJDIR ve asagi yuvarlanir; yariyi yukari
                                 yuvarlamak (0.99882 -> 0.999) cumleyi YANLIS yapardi cunku
                                 uc koldan biri 0.999'un altinda. Yon, iddianin yonudur.
    """
    v = float(value)
    mode, _, spec = rounding.partition(":")
    if mode == "percent_of_fraction":
        v, rounding = 100.0 * v, (spec or "int")
    elif mode == "sci_mantissa":
        e = 0 if v == 0 else math.floor(math.log10(abs(v)))
        v, rounding = v / (10.0 ** e), (spec or "1dp")
    elif mode == "sci_exponent":
        return Decimal(0 if v == 0 else math.floor(math.log10(abs(v))))
    rmode = ROUND_HALF_UP
    if rounding.endswith("_floor"):
        rounding, rmode = rounding[: -len("_floor")], ROUND_FLOOR
    if rounding == "int":
        q = Decimal(1)
    else:
        nd = int(rounding.replace("dp", ""))
        q = Decimal(1).scaleb(-nd)
    return Decimal(repr(v)).quantize(q, rounding=rmode)


def printed_dec(s):
    return Decimal(s.replace("+", ""))


# =============================================================================
# ESLEME + ANA AKIS
# =============================================================================
def norm(s):
    return " ".join(str(s).split()).lower()


def match_tokens(toks, unit, section, row, idx):
    """Bir beyanin (unit, section, row-oneki, idx) esledigi jetonlar.

    Satir ONEKLE eslesir: dipnot/caption satirlarinin etiketi satirin tamamidir ve beyanda
    tamamini yazmak hem okunmaz hem kirilgan olurdu. Onek birden fazla jetona eslesirse bu bir
    HATADIR (belirsiz beyan) ve raporlanir -- sessizce ilki alinmaz.
    """
    r = norm(row)
    return [t for t in toks
            if t["unit"] == unit and t["section"] == section
            and (idx is None or t["idx"] == idx)
            and norm(t["row"]).startswith(r)]


def line_numbers(paper_root, where):
    """`sections/x.tex#capa cumlesi` -> capanin gectigi satir ve KOMSULARINDAKI sayi jetonlari.

    SATIR NUMARASINA CAPA ATILMAZ: bu betik ilk yazildiginda `:693` kullaniliyordu ve makale
    ayni gun duzenlenince capa kaydi (cumle 693-694'e yayildi). Capa artik cumlenin KENDI
    metni; pencere +-1 satir, cunku LaTeX cumleleri satir sonunda kirilir.
    """
    rel, anchor = where.split("#", 1)
    fp = Path(paper_root) / rel
    if not fp.exists():
        raise Unresolved(f"duzyazi dosyasi yok: {rel}")
    lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise Unresolved(f"{where}: capa {len(hits)} satirda gecti (tam 1 olmali)")
    i = hits[0]
    from paper_number_scan import COMMENT, NUM, strip_layout
    win = " ".join(lines[max(0, i - 1):i + 2])
    cleaned, _ = strip_layout(COMMENT.sub("", win))
    return NUM.findall(cleaned), f"{rel}:{i + 1}"


def build(paper_root):
    """(payload, derived_entries) -- defterin tamami. check_numbers de bunu cagirir."""
    toks, dropped, files, secs, signs = scan_paper(paper_root)
    store = {}
    entries, problems = [], []

    exempt_keys, exempt_rows = set(), []
    for e in EXEMPT:
        hit = match_tokens(toks, e["unit"], e["section"], e["row"], e["idx"])
        if not hit and not e.get("optional"):
            problems.append({"kind": "exempt_matched_nothing", "id": e["class"],
                             "detail": f"{e['unit']} {e['row'][:40]!r}"})
        for t in hit:
            exempt_keys.add(t["key"])
            exempt_rows.append({"key": t["key"], "class": e["class"], "why": e["why"],
                                "printed": t["printed"]})

    bound_keys = {}
    for bd in BINDINGS:
        hit = match_tokens(toks, bd["unit"], bd["section"], bd["row"], bd["idx"])
        if len(hit) != 1:
            problems.append({"kind": "binding_matched_nothing" if not hit else "ambiguous",
                             "id": bd["id"], "detail": f"{len(hit)} jeton · "
                                                       f"{bd['unit']} {bd['row'][:40]!r} "
                                                       f"idx={bd['idx']}"})
            continue
        t = hit[0]
        if t["key"] in bound_keys:
            problems.append({"kind": "double_bound", "id": bd["id"], "detail": t["key"]})
            continue
        try:
            exact = resolve(store, bd["artifact"], bd["path"])
        except Unresolved as e:
            problems.append({"kind": "unresolved_path", "id": bd["id"], "detail": str(e)})
            continue
        rounded = fmt_round(exact, bd["rounding"])
        pr = printed_dec(t["printed"])
        ok = rounded == pr
        bound_keys[t["key"]] = bd["id"]
        entries.append({"id": bd["id"], "printed": t["printed"], "artifact": bd["artifact"],
                        "path": bd["path"], "exact": exact, "rounding": bd["rounding"],
                        "rounded": str(rounded), "matches": ok,
                        "where": [f"paper/{t['file']}:{t['line']}"],
                        "token": t["key"], "row": t["row"], "idx": t["idx"]})
        if not ok:
            problems.append({"kind": "rounding_mismatch", "id": bd["id"],
                             "detail": f"basili {t['printed']} vs alan {exact!r} -> "
                                       f"{bd['rounding']} {rounded}"})

    dentries = []
    for d in DERIVED:
        try:
            vals = [resolve(store, o["artifact"], o["path"]) for o in d["operands"]]
        except Unresolved as e:
            problems.append({"kind": "unresolved_path", "id": d["id"], "detail": str(e)})
            continue
        if d["formula"] == "ratio":
            val = abs(vals[0]) / abs(vals[1])
        elif d["formula"] == "diff":
            val = vals[0] - vals[1]
        elif d["formula"] == "pct_of":
            val = 100.0 * vals[0] / vals[1]
        elif d["formula"] == "sum":
            val = sum(vals)
        elif d["formula"] == "mean":
            val = sum(vals) / len(vals)
        elif d["formula"] == "pct_excess":
            # a'nin b'yi asma orani, PAYDA b. `pct_drop`tan tek farki paydasi; ayri isim
            # verildi cunku bir oranin paydasi FORMULUN ADINDA da gorunmeli -- 20 Agu'da
            # `pct_drop` ile denendi ve 63 yerine 39 verdi, yani iki formul ayni sayiyi
            # ASLA vermiyor ve karistirilmalari sessiz kalmiyor.
            val = 100.0 * (vals[0] - vals[1]) / vals[1]
        elif d["formula"] == "product":
            # Operandlarin CARPIMI. Kampanyada tek kullanimi bilesik sicaklik T* x tau; iki
            # operand da ALAN olarak cozuluyor (tau bir yapilandirma sabiti degil, kosulan
            # kolun kendi kaydindaki deger) -- elle yazilmis bir carpan olsaydi bag KURULMAZDI.
            val = 1.0
            for x in vals:
                val *= x
        elif d["formula"] == "min":
            # ALT SINIR iddialarinin operandi: "uc kolun hepsi > X" cumlesinde belirleyici
            # olan EN KUCUK koldur; digerleri iddiayi test etmez.
            val = min(vals)
        elif d["formula"] == "ratio_of_mean":
            # pay = SON operand HARIC operandlarin ortalamasi; payda = SON operand.
            # Paydanin hangi alan oldugu beyanin `note` alaninda ADIYLA yazilir (17 Agu
            # kurali); formul adi da paydanin tek bir operand oldugunu gosteriyor.
            val = (sum(vals[:-1]) / len(vals[:-1])) / vals[-1]
        elif d["formula"] == "pct_drop":
            # yuzde AZALMA: (taban - duzeltilmis) / taban x 100. Payda ACIKCA TABAN -- bir oranin
            # paydasi cumlede adlandirilmali (17 Agu kurali), burada da alan yolu olarak duruyor.
            val = 100.0 * (vals[0] - vals[1]) / vals[0]
        else:
            problems.append({"kind": "unknown_formula", "id": d["id"], "detail": d["formula"]})
            continue
        rounded = fmt_round(val, d["rounding"])
        tok = None
        # YETKILI DEGER MAKALENIN KENDISI. Bir jetona baglanmis turetilmis nicelikte
        # karsilastirma, koda yazilmis `printed` ile degil MAKALEDE BASILI degerle yapilir --
        # aksi halde makale duzenlenince denetci sessiz kalirdi (kendi ozsinamasinda olctuk).
        if d["unit"]:
            hit = match_tokens(toks, d["unit"], d["section"], d["row"], d["idx"])
            if len(hit) == 1:
                tok = hit[0]
                # 20 Agu 2026: bu satir eskiden KOSULSUZ atiyordu. Bir jeton hem `b()` hem
                # `dv()` tarafindan sahiplenildiginde hicbir sey bagirmiyor, ama jeton
                # muhasebesi (bound + derived_in_scope + exempt + unbound = tokens) fazla
                # veriyordu -- altisi birden bugun olculdu. Artik ihlal.
                if tok["key"] in bound_keys:
                    problems.append({"kind": "double_bound", "id": d["id"],
                                     "detail": f"turetilmis beyan zaten sahiplenilmis jetonu "
                                               f"isaretliyor: {tok['key']}"})
                    tok = None
                else:
                    bound_keys[tok["key"]] = d["id"]
            else:
                problems.append({"kind": "derived_matched_nothing", "id": d["id"],
                                 "detail": f"{len(hit)} jeton · {d['unit']} "
                                           f"{str(d['row'])[:40]!r} idx={d['idx']}"})
        pr = printed_dec(tok["printed"] if tok else d["printed"])
        ok = rounded == pr
        if tok and printed_dec(d["printed"]) != pr:
            problems.append({"kind": "derived_printed_drift", "id": d["id"],
                             "detail": f"defter {d['printed']} vs makale {tok['printed']}"})
        dentries.append({"id": d["id"], "printed": d["printed"], "formula": d["formula"],
                         "operands": d["operands"], "operand_values": vals,
                         "exact": val, "rounding": d["rounding"], "rounded": str(rounded),
                         "matches": ok, "note": d["note"],
                         "where": [f"paper/{tok['file']}:{tok['line']}"] if tok else []})
        if not ok:
            problems.append({"kind": "derived_mismatch", "id": d["id"],
                             "detail": f"basili {pr} vs yeniden hesap {val!r} -> {rounded}"})
        if d.get("where_literal"):
            try:
                nums, _loc = line_numbers(paper_root, d["where_literal"])
                word = SPELLED.get(str(rounded))
                spelled_ok = bool(word) and word in open(
                    Path(paper_root) / d["where_literal"].split("#")[0],
                    encoding="utf-8", errors="replace").read()
                if str(rounded) not in [x.lstrip("+") for x in nums] and not spelled_ok:
                    problems.append({"kind": "printed_not_found_at_location", "id": d["id"],
                                     "detail": f"{d['where_literal']}: {rounded} yok, "
                                               f"satirdaki sayilar {nums[:8]}"})
            except Unresolved as e:
                problems.append({"kind": "prose_location_bad", "id": d["id"],
                                 "detail": str(e)})

    pentries = []
    for pr in PROSE:
        try:
            exact = resolve(store, pr["artifact"], pr["path"])
        except Unresolved as e:
            problems.append({"kind": "unresolved_path", "id": pr["id"], "detail": str(e)})
            continue
        rounded = fmt_round(exact, pr["rounding"])
        row = {"id": pr["id"], "artifact": pr["artifact"], "path": pr["path"],
               "exact": exact, "rounding": pr["rounding"], "rounded": str(rounded),
               "where": [f"paper/{pr['where']}"], "note": pr["note"], "matches": None}
        try:
            nums, loc = line_numbers(paper_root, pr["where"])
            row["line_numbers"] = nums
            row["where"] = [f"paper/{loc}"]
            row["matches"] = str(rounded) in [x.lstrip("+") for x in nums]
            if not row["matches"]:
                problems.append({"kind": "printed_not_found_at_location", "id": pr["id"],
                                 "detail": f"{pr['where']}: {rounded} yok, satirdaki sayilar "
                                           f"{nums[:8]}"})
        except Unresolved as e:
            problems.append({"kind": "prose_location_bad", "id": pr["id"], "detail": str(e)})
        pentries.append(row)

    # --- TEYIT KAYITLARI: ayni niceligin ikinci kaynagi (bkz. CROSS_CHECKS beyani)
    xentries = []
    for x in CROSS_CHECKS:
        ca, cp = x["canonical"]
        # Tolerans, o yola bagli hucrelerin EN SIKI yuvarlamasindan turetilir. Bag yoksa beyan
        # bosa dusmus demektir ve bu bir SORUNDUR -- teyit ettigi sey makalede gecmiyor.
        rounds = sorted({bd["rounding"] for bd in BINDINGS
                         if bd["artifact"] == ca and bd["path"] == cp})
        if not rounds:
            problems.append({"kind": "cross_check_unbound", "id": x["id"],
                             "detail": f"{ca} -> {cp}: bu yola bagli hucre yok"})
            continue
        dps = [0 if r == "int" else int(r.replace("dp", "")) for r in rounds]
        tol = 0.5 * 10 ** (-max(dps))
        try:
            a = resolve(store, ca, cp)
            bconf = resolve(store, *x["confirm"])
        except Unresolved as e:
            problems.append({"kind": "unresolved_path", "id": x["id"], "detail": str(e)})
            continue
        row = {"id": x["id"], "quantity": x["quantity"],
               "canonical": {"artifact": ca, "path": cp, "value": a},
               "confirm": {"artifact": x["confirm"][0], "path": x["confirm"][1],
                           "value": bconf},
               "abs_diff": abs(a - bconf), "tolerance": tol,
               "tolerance_from": f"en siki yuvarlama {max(rounds, key=lambda r: 0 if r == 'int' else int(r.replace('dp', '')))}",
               "roundings_in_paper": rounds, "why": x["why"], "relays": [], "matches": True}
        if row["abs_diff"] > tol:
            row["matches"] = False
            problems.append({"kind": "cross_source_divergence", "id": x["id"],
                             "detail": f"|{a!r} - {bconf!r}| = {row['abs_diff']:.3e} > "
                                       f"tol {tol:.1e} ({row['tolerance_from']})"})
        for r in rounds:
            if fmt_round(a, r) != fmt_round(bconf, r):
                row["matches"] = False
                problems.append({"kind": "cross_source_rounding_disagreement", "id": x["id"],
                                 "detail": f"{r}: kanonik {fmt_round(a, r)} vs teyit "
                                           f"{fmt_round(bconf, r)}"})
        # ROLELER: p4 ve tstar_provenance teyit degerini KOPYALIYOR, hesaplamiyor. Kopya
        # ayrisirsa bayat bir role var demektir ve o sessizce yanlis bir teyit uretirdi.
        for ra, rp in x["relays"]:
            try:
                rv = resolve(store, ra, rp)
            except Unresolved as e:
                problems.append({"kind": "unresolved_path", "id": x["id"] + ".relay",
                                 "detail": str(e)})
                continue
            ok_r = abs(rv - bconf) <= 1e-12
            row["relays"].append({"artifact": ra, "path": rp, "value": rv, "exact_copy": ok_r})
            if not ok_r:
                row["matches"] = False
                problems.append({"kind": "cross_source_relay_drift", "id": x["id"],
                                 "detail": f"{ra} -> {rp}: {rv!r} != teyit {bconf!r}"})
        xentries.append(row)

    # --- ISARET DESENLERI (22 Agu 2026, defter final3). Sayi muhasebesinden AYRI tutulur:
    # jeton degiller (rakam yok), o yuzden `tokens` toplamina girmezler. Kural ayni: her desen
    # ya bir alana bagli, ya ihlal.
    sign_entries, sign_bound = [], set()
    for g in SIGNS:
        hit = match_tokens(signs, g["unit"], g["section"], g["row"], g["idx"])
        if not hit:
            problems.append({"kind": "sign_matched_nothing", "id": g["id"],
                             "detail": f"{g['unit']} {g['row'][:40]!r} idx={g['idx']}"})
            continue
        if len(hit) > 1:
            problems.append({"kind": "ambiguous", "id": g["id"],
                             "detail": f"{len(hit)} isaret desenine birden eslesti"})
            continue
        t = hit[0]
        if t["key"] in sign_bound:
            problems.append({"kind": "double_bound", "id": g["id"], "detail": t["key"]})
        sign_bound.add(t["key"])
        vals, ok = [], True
        for pth in g["paths"]:
            try:
                v = resolve_text(store, g["artifact"], pth)
            except Unresolved as e:
                problems.append({"kind": "unresolved_path", "id": g["id"], "detail": str(e)})
                ok = False
                continue
            vals.append(v)
            if v != t["printed"]:
                ok = False
                problems.append({"kind": "sign_mismatch", "id": g["id"],
                                 "detail": f"basili {t['printed']} != {pth} {v}"})
        sign_entries.append({"id": g["id"], "unit": g["unit"], "row": t["row"][:60],
                             "idx": g["idx"], "printed": t["printed"],
                             "artifact": g["artifact"], "paths": g["paths"], "values": vals,
                             "why": g["why"], "where": f"paper/{t['file']}:{t['line']}",
                             "matches": ok})
    for t in signs:
        if t["key"] not in sign_bound:
            problems.append({"kind": "unregistered_sign", "id": t["printed"],
                             "detail": f"{t['unit']} {t['row'][:40]!r} idx={t['idx']} · "
                                       f"paper/{t['file']}:{t['line']}"})

    # --- BANT KONTROLU (23 Agu 2026). Defter bugune kadar degerin ALANLA eslesmesini
    # denetliyordu, kaynagin YAYIMLI olmasini degil: bir bag dogru olabilir ve yine de
    # hakem kaynaga ULASAMAZ. Bu, 18 Agu'da tab_human'in 29 hucresinde yakalanan sinifin
    # defter tarafindaki hali -- "kayitli" ile "gosterilebilir" ayni sey degil. Bant beyani
    # `export_to_drive.EXPORTS`; ithal FONKSIYON ICINDE, cunku oz sinama bandi gecici olarak
    # kisaltip sinifin gercekten atesledigini gosteriyor.
    # Bant beyani PUBLIC depoda YOK (PROVENANCE.md S3). Orada kontrol YAPILMAZ ve bu
    # sayacta gorunur -- her kaynagi "bantsiz" ilan etmek yanlis alarm olurdu.
    try:
        import export_to_drive as EX
        band_checked = True
    except ModuleNotFoundError:        # pragma: no cover -- yalniz public depoda
        EX, band_checked = None, False
    banded = set()
    for _e in (EX.EXPORTS if band_checked else []):
        _src = _e[0]
        banded.add(_src)
        if _src.startswith("diagnostics/"):
            banded.add(_src[len("diagnostics/"):])
    sources = {}
    for _x in BINDINGS:
        sources.setdefault(_x["artifact"], []).append(_x["id"])
    for _x in DERIVED:
        for _o in _x["operands"]:
            sources.setdefault(_o["artifact"], []).append(_x["id"])
    for _x in PROSE:
        sources.setdefault(_x["artifact"], []).append(_x["id"])
    for _x in SIGNS:
        sources.setdefault(_x["artifact"], []).append(_x["id"])
    for _x in CROSS_CHECKS:
        sources.setdefault(_x["canonical"][0], []).append(_x["id"])
        sources.setdefault(_x["confirm"][0], []).append(_x["id"])
        for _a, _p in _x["relays"]:
            sources.setdefault(_a, []).append(_x["id"])
    # IKINCI KANAL (23 Agu 2026 eki). Bant Drive'a gider; HAKEM ise DOI'yi cozup GitHub/Zenodo
    # arsivini indirir. Bugun olculdu: 49 kaynagin biri (a13_verdict.json, 10 beyan) bantta
    # VARDI ama public depoda YOKTU -- yani kapi yesil, hakemin eli bos. Kaynak artik iki
    # kanalda birden aranir. Public klasoru bu makinede yoksa (arsivden kosan bir okur) kontrol
    # SESSIZCE atlanmaz, sayacta "olculmedi" olarak gorunur.
    published, published_checked = None, False
    try:
        from public_repo_sync import PUBLIC as _PUB
        if Path(_PUB).exists():
            _r = subprocess.run(["git", "ls-files"], cwd=str(_PUB), capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
            if _r.returncode == 0:
                published = set(_r.stdout.split())
                published_checked = True
    except Exception:
        published = None

    unbanded = sorted(a for a in sources if a not in banded) if band_checked else []
    if published_checked:
        for _a in sorted(sources):
            if ("diagnostics/" + _a) in published or _a in published:
                continue
            if _a in unbanded:
                continue                      # zaten bant kanalindan raporlaniyor
            if BAND_EXEMPT.get(_a):
                continue                      # gerekcesi yazili: iki kanal icin de gecerli
            problems.append({"kind": "binding_source_unpublished", "id": _a,
                             "detail": f"{len(sources[_a])} beyan bu artefakta bagli; ihrac "
                                       f"bandinda VAR ama PUBLIC DEPODA YOK -- hakem DOI'den "
                                       f"inen arsivde bulamaz"})
    band_exempt_rows = []
    for _a in unbanded:
        why = BAND_EXEMPT.get(_a)
        if why:
            band_exempt_rows.append({"artifact": _a, "why": why,
                                     "declarations": len(sources[_a]),
                                     "ids": sorted(set(sources[_a]))})
            continue
        problems.append({"kind": "binding_source_unpublished", "id": _a,
                         "detail": f"{len(sources[_a])} beyan bu artefakta bagli ama artefakt "
                                   f"ihrac bandinda (export_to_drive.EXPORTS) yok: "
                                   f"{', '.join(sorted(set(sources[_a]))[:3])}"})
    # CURUMUS MUAFIYET: artefakt banda girdiyse beyan da olmelidir. Aksi halde liste sessizce
    # yaslanir ve bir gun gercek bir boslugu ortmeye baslar (`exempt_matched_nothing` ile ayni
    # gerekce).
    for _a, _why in sorted(BAND_EXEMPT.items() if band_checked else []):
        if _a in banded:
            problems.append({"kind": "band_exempt_rotten", "id": _a,
                             "detail": "artefakt artik ihrac bandinda; bant muafiyeti "
                                       "gerekcesiyle birlikte SILINMELI"})

    unbound = [t for t in toks if t["key"] not in bound_keys and t["key"] not in exempt_keys]
    payload = {
        "note": "review-responsive, not pre-declared",
        "scope": {"in": ["paper/tables/*.tex", "abstract", "supplementary S8-S11",
                         "individually anchored prose sentences (declared one by one)"],
                  "out": ["sections/*.tex prose, except the individually anchored sentences "
                          "(revision window)",
                          "supplementary S1-S3 (today's headroom verdict not applied yet)"],
                  "not_a_measurement": sorted({e["class"] for e in EXEMPT})},
        "paper_files": files, "sections": secs,
        "counts": {"tokens": len(toks), "bound": len(entries), "derived": len(dentries),
                   "exempt": len(exempt_keys), "unbound": len(unbound),
                   "layout_dropped": len(dropped),
                   "mismatch": sum(1 for e in entries if not e["matches"]),
                   "derived_mismatch": sum(1 for e in dentries if not e["matches"]),
                   "prose": len(pentries),
                   # SÜTUN TOPLANSIN DİYE (18 Ağu, N16). `derived` BEYAN sayar, `tokens` JETON
                   # sayar: türetilmiş beyanların bir kısmı kapsam DIŞI düzyazıya çapalı,
                   # dolayısıyla kapsam içi hiçbir jetonu tüketmez. Sütunu toplayan bir okur
                   # 719'u bulamıyordu. Jeton muhasebesi artık ayrı basılıyor:
                   #     bound + derived_in_scope + exempt = tokens
                   "derived_in_scope": sum(1 for e in dentries if e["where"]),
                   "derived_prose_anchored": sum(1 for e in dentries if not e["where"]),
                   "artifact_sources": len(sources),
                   "artifact_sources_unbanded": len(unbanded),
                   "artifact_sources_band_exempt": len(band_exempt_rows),
                   "artifact_sources_published_checked": published_checked,
                   "artifact_sources_band_checked": band_checked,
                   "signs": len(sign_entries),
                   "sign_tokens": len(signs),
                   "sign_mismatch": sum(1 for e in sign_entries if not e["matches"]),
                   "cross_checks": len(xentries),
                   "cross_check_fail": sum(1 for e in xentries if not e["matches"]),
                   "problems": len(problems)},
        "entries": entries, "exempt": exempt_rows, "prose_entries": pentries,
        "signs": sign_entries, "band_exempt": band_exempt_rows,
        "cross_checks": xentries,
        "unbound": [{"key": t["key"], "printed": t["printed"], "unit": t["unit"],
                     "row": t["row"], "idx": t["idx"],
                     "where": f"paper/{t['file']}:{t['line']}"} for t in unbound],
        "problems": problems,
        "dropped_layout_classes": sorted({d["class"] for d in dropped}),
    }
    return payload, dentries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-root", default=os.environ.get("VELD_PAPER_ROOT"))
    args, _unknown = ap.parse_known_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    if not args.paper_root or not Path(args.paper_root).exists():
        print("kagit agaci verilmedi (--paper-root / VELD_PAPER_ROOT): mevcut defter KORUNDU, "
              "hicbir dosya yazilmadi.")
        return 0

    payload, dentries = build(args.paper_root)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "number_ledger.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "derived_registry.json").write_text(json.dumps(
        {"note": payload["note"],
         "counts": {"derived": len(dentries),
                    "mismatch": sum(1 for e in dentries if not e["matches"])},
         "entries": dentries}, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md(payload, dentries)

    c = payload["counts"]
    print(f"jeton {c['tokens']} · bagli {c['bound']} · turetilmis {c['derived']} · "
          f"muaf {c['exempt']} · KAYITSIZ {c['unbound']} · uyusmazlik {c['mismatch']} · "
          f"teyit {c['cross_checks']} (basarisiz {c['cross_check_fail']}) · "
          f"sorun {c['problems']}")
    for p in payload["problems"][:45]:
        print(("  ! " + p["kind"].ljust(26) + " " + str(p.get("id", "")) + " " +
               str(p.get("detail", "")))[:158])
    if len(payload["problems"]) > 45:
        print(f"  ... +{len(payload['problems']) - 45} sorun")
    return 0


def write_md(payload, dentries):
    c = payload["counts"]
    L = ["# N13 — Number provenance ledger", "",
         "> **Review-responsive, not pre-declared (17 Aug 2026).** The ledger records the "
         "value-to-FIELD binding, not the value: a stale number exists somewhere too, so "
         "existence proves nothing.", "",
         "Producer: `diagnostics/number_ledger.py` · scanner: `diagnostics/paper_number_scan.py`"
         " · auditor: `diagnostics/check_numbers.py`", "",
         "### Token accounting — this column adds up", "",
         "| in-scope numeric token | count |", "|---|---|",
         f"| bound to an artifact field | {c['bound']} |",
         f"| derived, occupying an in-scope token | {c.get('derived_in_scope', 0)} |",
         f"| declared not-a-measurement | {c['exempt']} |",
         f"| **unregistered** | **{c['unbound']}** |",
         f"| **= numeric tokens in scope** | **{c['tokens']}** |", "",
         "The four categories are disjoint (bound ∩ exempt is checked to be empty) and the "
         "column sums to the total. Two kinds of declaration are **not** in that table because "
         "they occupy no in-scope token — they are anchored to sentences the scanner "
         "deliberately does not read:", "",
         "| declaration anchored outside the scanned scope | count |", "|---|---|",
         f"| derived quantity on a prose anchor | {c.get('derived_prose_anchored', 0)} |",
         f"| prose field binding (`pv`) | {c.get('prose', 0)} |", "",
         f"The registry therefore holds **{c['derived']}** derived quantities in total: "
         f"{c.get('derived_in_scope', 0)} on in-scope tokens + "
         f"{c.get('derived_prose_anchored', 0)} on prose anchors. Adding *declaration* counts "
         "to *token* counts is what made an earlier version of this table appear not to sum.",
         "",
         "| other | count |", "|---|---|",
         f"| printed-vs-field mismatch | {c['mismatch']} |",
         f"| confirmation records (second source) | {c.get('cross_checks', 0)} "
         f"({c.get('cross_check_fail', 0)} failing) |",
         f"| layout tokens dropped by the scanner | {c['layout_dropped']} |",
         f"| sign patterns bound (non-numeric, see below) | {c.get('signs', 0)} of "
         f"{c.get('sign_tokens', 0)} |", "",
         "## Scope (declared)", "",
         "**In:** " + ", ".join("`" + x + "`" for x in payload["scope"]["in"]) + "  ",
         "**Out:** " + " · ".join(payload["scope"]["out"]) + "  ",
         "**Not a measurement:** "
         + ", ".join("`" + x + "`" for x in payload["scope"]["not_a_measurement"]),
         "", "## Unregistered numbers", ""]
    if payload["unbound"]:
        L += ["| printed | unit | row | where |", "|---|---|---|---|"]
        for u in payload["unbound"]:
            L.append(f"| `{u['printed']}` | {u['unit']} | {u['row'][:46]} | {u['where']} |")
    else:
        L.append("None — every in-scope number is bound, derived or declared.")
    L += ["", "## Mismatches", ""]
    bad = [e for e in payload["entries"] if not e["matches"]]
    if bad:
        L += ["| id | printed | field value | rounded | where |", "|---|---|---|---|---|"]
        for e in bad:
            L.append(f"| `{e['id']}` | {e['printed']} | {e['exact']:.6g} | {e['rounded']} | "
                     f"{e['where'][0]} |")
    else:
        L.append("None.")
    gs = payload.get("signs") or []
    if gs:
        L += ["", "## Sign patterns (data claims that carry no digit)", "",
              "`tab_mechanisms` prints the per-seed sign string next to each cell "
              "(`[++-]`) and the discussion refers to those strings by name. They are **not "
              "numeric tokens** — the scanner's number extractor cannot see them — but they "
              "are copies of artifact fields, so a corrupted sign string would have passed "
              "every gate silently. Since 22 Aug 2026 each one is bound and checked. Empty "
              "LaTeX groups (`-{}-`, inserted to defeat an en-dash ligature in the printed "
              "PDF) are normalised away before comparison: the printed characters, not the "
              "source bytes, are what the claim is about.", "",
              "| printed | field | value | where |", "|---|---|---|---|"]
        for e in gs:
            L.append(f"| `{e['printed']}` | `{' + '.join(e['paths'])}` | "
                     f"{' / '.join('`' + v + '`' for v in e['values'])} | {e['where']} |")

    xs = payload.get("cross_checks") or []
    if xs:
        L += ["", "## Confirmation records (same quantity, second source)", "",
              "Some quantities are computed twice by independent implementations. They are "
              "**deliberately not merged**: agreement between two computations is a cross-check, "
              "and merging destroys it. One source is declared canonical and bound; the other is "
              "recorded here and audited. The tolerance is not hand-written — it is "
              "`0.5 x 10^-d`, where `d` is the **tightest rounding the paper uses for that "
              "quantity**, so the gate tightens automatically if a table starts printing more "
              "digits. A second, sharper gate is structural: both sources must round to the same "
              "value at *every* rounding declared for that field.", "",
              "| quantity | canonical | confirming | \\|diff\\| | tolerance | roundings | ok |",
              "|---|---|---|---|---|---|---|"]
        for e in xs:
            L.append(f"| {e['quantity']} | `{e['canonical']['path']}` = "
                     f"{e['canonical']['value']:.7f} | `{e['confirm']['path']}` = "
                     f"{e['confirm']['value']:.7f} | {e['abs_diff']:.2e} | "
                     f"{e['tolerance']:.1e} | {', '.join(e['roundings_in_paper'])} | "
                     f"{'yes' if e['matches'] else '**NO**'} |")
        rel = [(e, r) for e in xs for r in e["relays"]]
        if rel:
            L += ["", "Relays — artifacts that **copy** the confirming value rather than "
                  "computing it. A drifted relay would produce a silently false confirmation.", "",
                  "| quantity | relay | value | exact copy |", "|---|---|---|---|"]
            for e, r in rel:
                L.append(f"| {e['quantity']} | `{r['artifact']}` → `{r['path']}` | "
                         f"{r['value']:.7f} | {'yes' if r['exact_copy'] else '**NO**'} |")
    L += ["", "## Derived quantities", "",
          "| id | printed | formula | recomputed | ok |", "|---|---|---|---|---|"]
    for e in dentries:
        L.append(f"| `{e['id']}` | {e['printed']} | {e['formula']} | {e['exact']:.6g} | "
                 f"{'yes' if e['matches'] else '**NO**'} |")
    L += ["", "## Bindings", "",
          "| id | printed | artifact | path | rounding |", "|---|---|---|---|---|"]
    for e in payload["entries"]:
        L.append(f"| `{e['id']}` | {e['printed']} | `{e['artifact']}` | `{e['path']}` | "
                 f"{e['rounding']} |")
    (OUT_DIR / "number_ledger.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    dl = ["# N13 — Derived quantity registry", "",
          "Every printed ratio or difference, with its numerator and denominator as artifact "
          "field paths, so it can be recomputed from the ledger instead of from printed values. "
          "Two of today's three errors came from dividing rounded printed cells.", "",
          "| id | printed | formula | operands | recomputed | ok |",
          "|---|---|---|---|---|---|"]
    for e in dentries:
        ops = " ÷ ".join("`" + o["artifact"] + "` → `" + o["path"] + "`"
                         for o in e["operands"])
        dl.append(f"| `{e['id']}` | {e['printed']} | {e['formula']} | {ops} | "
                  f"{e['exact']:.6g} | {'yes' if e['matches'] else '**NO**'} |")
    (OUT_DIR / "derived_registry.md").write_text("\n".join(dl) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
