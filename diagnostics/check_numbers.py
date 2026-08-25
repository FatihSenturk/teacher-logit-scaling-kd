"""N13 denetcisi — defteri okur, makaleyi dogrular, ihlalde CIKIS KODU 1 verir.

DORT IHLAL SINIFI (Fatih'in 17 Agu tanimi)
  1. rounding_mismatch            basili deger, bagli alanin beyan edilen yuvarlamasiyla
                                  eslesmiyor
  2. unresolved_path / stale      bagli alan artefaktta ARTIK YOK (bayatlik)
  3. derived_mismatch             turetilmis nicelik pay/paydadan yeniden hesaplaninca tutmuyor
     printed_not_found_at_location  ... ya da defterdeki deger, cumlenin kendisinde gecmiyor
  4. unregistered                 makalede deftere kayitli OLMAYAN olcum sayisi var
                                  (kapsam disi beyan edilmemisse)
Dorduncu madde asil korumadir: yanlis sayiyi yakalamak degil, KAYITSIZ sayinin varligini
yasaklamak. Bir bayat deger de bir yerde vardir; bir kayitsiz sayi ise hicbir alana bagli
degildir ve onu ancak bu kural gorur.

BESINCI SINIF ledger_drift: depodaki `number_ledger.json` ile beyanlarin (number_ledger.py)
verdigi baglar ayrisirsa. Boylece "artefakti elle duzelt" yolu da kapali: artefakt beyanin
turevi, tersi degil.

CIKIS KODLARI: 0 ihlal yok · 1 IHLAL var · 2 denetlenemedi (kagit agaci yok).
Kullanim: python diagnostics/check_numbers.py --paper-root "<...>/paper" [--json]
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

# TEK TARAYICI, TEK BEYAN KUMESI: denetci kendi tanimini getirmez, defterin kendisini cagirir.
from number_ledger import OUT_DIR, build  # noqa: E402

VIOLATION_KINDS = {
    "rounding_mismatch": "basili deger bagli alanla uyusmuyor",
    "unresolved_path": "bagli alan artefaktta yok (BAYAT)",
    "derived_mismatch": "turetilmis nicelik yeniden hesapta tutmuyor",
    "printed_not_found_at_location": "defterdeki deger cumlede gecmiyor",
    "prose_location_bad": "duzyazi capasi bulunamadi",
    "binding_matched_nothing": "beyan edilen hucre makalede yok",
    # 21 Agu 2026 (jeton final): bu sinif bugune kadar SUZULUYORDU -- capasi hicbir jetona
    # eslesmeyen bir dv, kapidan sessizce geciyordu. Oz sinamanin (daha siki) taban
    # karsilastirmasi yakaladi: 'calibration estimator in 20 of 21 cells' dv'si §5'ten
    # cumle silinince olu kalmis, kapi yesil kalmisti.
    "derived_matched_nothing": "turetilmis beyanin capasi makalede yok",
    # 23 Agu 2026 (bant bosluk turu): KAYNAGIN YAYIMLILIGI. Defter bugune kadar degerin
    # ALANLA eslesmesini denetliyordu; alan dogru olsa bile artefakt ihrac bandinda yoksa
    # hakem kaynaga ULASAMAZ. "Kayitli" ile "gosterilebilir" ayni sey degil.
    "binding_source_unpublished": "bagli artefakt ihrac bandinda yok (gosterilemez kaynak)",
    # Muafiyet YOLU var (number_ledger.BAND_EXEMPT): gerekcesi yazili muafiyet ihlal saymaz,
    # gerekcesiz olan sayar. Muafiyetin kendisi de denetlenir -- artefakt banda girdiginde
    # beyan CURUR ve o da ihlaldir; yoksa liste sessizce yaslanir.
    "band_exempt_rotten": "curumus bant muafiyeti (artefakt artik bantta)",
    # 22 Agu 2026 (defter final3): ISARET DESENLERI. Rakamsiz veri iddialari (`[++-]`).
    # Sinif adlarinin BURADA olmasi sart -- VIOLATION_KINDS'te olmayan bir sinif kapidan
    # sessizce gecer (21 Agu'daki `derived_matched_nothing` acigi tam boyleydi).
    "sign_mismatch": "basili isaret deseni bagli alanla uyusmuyor",
    "sign_matched_nothing": "beyan edilen isaret deseni makalede yok",
    "unregistered_sign": "makalede deftere KAYITSIZ isaret deseni var",
    "ambiguous": "beyan birden fazla hucreye eslesiyor",
    "double_bound": "ayni hucre iki kez baglanmis",
    "exempt_matched_nothing": "curumus muafiyet (artik hicbir jetona denk gelmiyor)",
    "unknown_formula": "tanimsiz turetme formulu",
    # ALTINCI SINIF (17 Agu, N14): ayni niceligi hesaplayan IKI kaynak ayrismis.
    # Iki kaynak BILEREK birlestirilmedi -- uyusmalari bir capraz dogrulama. Ama dogrulama
    # ancak bir ESIGE bagliysa dogrulamadir; aksi halde "yakin sayilar" gozlemidir.
    "cross_source_divergence": "iki kaynak beyan edilen toleransi asti",
    "cross_source_rounding_disagreement": "iki kaynak basili yuvarlamada AYRI degere gidiyor",
    "cross_source_relay_drift": "teyit degerini kopyalayan artefakt ayrismis (bayat role)",
    "cross_check_unbound": "teyit beyani makalede hicbir hucreye denk gelmiyor",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-root", default=os.environ.get("VELD_PAPER_ROOT"))
    ap.add_argument("--json", action="store_true", help="ozeti JSON olarak bas")
    args, _unknown = ap.parse_known_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    if not args.paper_root or not Path(args.paper_root).exists():
        print("DENETLENEMEDI: kagit agaci yok (--paper-root / VELD_PAPER_ROOT). Cikis 2.")
        return 2

    payload, dentries = build(args.paper_root)
    viol = [p for p in payload["problems"] if p["kind"] in VIOLATION_KINDS]
    unreg = payload["unbound"]

    # --- besinci sinif: depodaki artefakt ile beyanlar ayrismis mi?
    drift = []
    stored_p = OUT_DIR / "number_ledger.json"
    if stored_p.exists():
        stored = json.loads(stored_p.read_text(encoding="utf-8"))
        old = {e["id"]: (e["artifact"], e["path"], e["rounding"]) for e in stored["entries"]}
        new = {e["id"]: (e["artifact"], e["path"], e["rounding"]) for e in payload["entries"]}
        for k in sorted(set(old) - set(new)):
            drift.append({"id": k, "detail": "artefaktta var, beyanda yok"})
        for k in sorted(set(new) & set(old)):
            if old[k] != new[k]:
                drift.append({"id": k, "detail": f"bag degisti: {old[k]} -> {new[k]}"})
    else:
        drift.append({"id": "-", "detail": "depoda number_ledger.json yok; defter hic "
                                          "uretilmemis"})

    c = payload["counts"]
    print(f"kapsam: {c['tokens']} jeton · bagli {c['bound']} · turetilmis {c['derived']} · "
          f"duzyazi bagi {c.get('prose', 0)} · muaf {c['exempt']} · "
          f"teyit kaydi {c.get('cross_checks', 0)}")
    print(f"        {c.get('sign_tokens', 0)} isaret deseni · bagli {c.get('signs', 0)} · "
          f"kaynak artefakt {c.get('artifact_sources', 0)} "
          f"(bantsiz {c.get('artifact_sources_unbanded', 0)})")
    print(f"IHLAL: {len(viol)} tanim/uyusmazlik · {len(unreg)} KAYITSIZ · "
          f"{len(drift)} defter kaymasi")
    for v in viol:
        print(f"  [{v['kind']}] {v.get('id', '')}: {v.get('detail', '')}"[:200])
    for u in unreg:
        print(f"  [unregistered] {u['printed']} · {u['unit']} · {u['row'][:44]!r} · "
              f"{u['where']}")
    for d in drift:
        print(f"  [ledger_drift] {d['id']}: {d['detail']}"[:200])

    if args.json:
        print(json.dumps({"violations": viol, "unregistered": unreg, "drift": drift,
                          "counts": c}, indent=2, ensure_ascii=False))
    total = len(viol) + len(unreg) + len(drift)
    print(f"\nSONUC: {'IHLAL VAR' if total else 'GECTI'} ({total} kalem)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
