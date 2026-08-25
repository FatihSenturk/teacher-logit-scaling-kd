"""MUTLAK-YOL KAPISI: public depoda DİSKE YAZILANDA beyan edilmemiş mutlak yol var mı?

NEDEN AYRI BİR KAPI. `public_repo_sync.py` "hiçbir dosyada mutlak yol kalmadı" derken KENDİ
dönüşümüne bakar: kaynağı okur, dönüştürür, sonuca bakar. Bu kapı DİSKTEKİ sonuca bakar.
İki ayrı sorudur ve ayrı olmaları kasıtlı -- senkron hiç yazmadığı (ya da bir gün yazıp
sonra kapsam dışına çıkardığı) bir dosyayı göremez. 8 Ağu'da tam bu oldu: iki dosya C
kovasına alındı ama diskte kaldı ve senkron onları hiç raporlamadı.

NEDEN BETİK, GREP DEĞİL (8 Ağu dersi). Gönderim dizisi 1c'nin birinci kapısı şuydu:

    grep -rn "D:.<çalışma dizini>" . --exclude-dir=.git | wc -l    # 0 OLMALI

Bu desen SADECE kampanya deposunun önekini yakalar. Başka sürücü kökleri (Veriseti,
datasets, kullanıcı ev dizinleri), UNC payları ve JSON kaçışlı çift-ters-bölü biçiminin
hiçbirini görmez. Ölçüldü: o grep 0 derken diskte **21 dosya** mutlak yol taşıyordu.
"Kısmen çalışan bir kontrol, hiç çalışmayandan daha tehlikelidir, çünkü geçer."

İKİLİ DOSYALAR SINANMAZ ve bu bir SINIR, sessiz bir kolaylık değil. Bayt regex'i
sıkıştırılmış dizilerde yanlış pozitif verir (ölçüldü: 42 npz'nin 4'ünde sürücü-harfi-iki-nokta
-bölü biçimine benzeyen rastgele baytlar) ve UTF-16/32 saklanmış GERÇEK yolu kaçırır (aynı npz'lerin
`meta.run_dir` alanı tam olarak böyle görünmez kalıyor). Uzantı listesi
`public_repo_sync.BINARY_SUF` -- tek kaynak, iki liste ayrışmasın diye ithal ediliyor.

DESEN VE BEYAN SINIFLARI TEK KAYNAKTAN. `ABS_ANY`, `THIRD_PARTY`, `DECLARED_ABS` ve
`DECLARED_DATED` `public_repo_sync`'ten İTHAL edilir, burada yeniden yazılmaz -- yoksa iki
liste ayrışır ve hangisinin doğru olduğu belirsizleşir.

BİRİM: DOSYA, eşleşme değil. Bir dosyada üç mutlak yol varsa bir kez sayılır. (8 Ağu'da bu
iki birim bir kez karıştırıldı; sayı artık raporda birimiyle yazılıyor.)

Kullanım: python diagnostics/abs_path_gate.py [--public <yol>]
Çıktı -> diagnostics/reports/abs_path_gate.{md,json}; beyansız kalıntı varsa çıkış kodu 1.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

# 23 Agu 2026 -- BEYANLI DUSUS. Bu betik PUBLIC depoda da bulunuyor, orada senkron modulu
# YOK (PROVENANCE.md S3) ve korumasiz import hakemin elinde ciplak bir
# ModuleNotFoundError uretiyordu: mekanizma gorunur, neden kosmadigi gorunmez.
# Desen producer_freshness_gate.py:65-73'ten -- sessiz yutma DEGIL, cikis 2.
try:
    from public_repo_sync import (ABS_ANY, BINARY_SUF, DECLARED_ABS,  # noqa: E402
                                  DECLARED_DATED, PUBLIC, THIRD_PARTY)
    SYNC_OK, SYNC_ERR = True, ""
except ModuleNotFoundError as _e:      # pragma: no cover -- yalniz public depoda
    ABS_ANY = BINARY_SUF = DECLARED_ABS = DECLARED_DATED = PUBLIC = THIRD_PARTY = None
    SYNC_OK, SYNC_ERR = False, str(_e)

OUT_MD = ROOT / "diagnostics" / "reports" / "abs_path_gate.md"
OUT_JSON = ROOT / "diagnostics" / "reports" / "abs_path_gate.json"

# Tek kaynak: senkronun kendi kontrolü hangi uzantıları atlıyorsa bu kapı da onları atlar.
# İki liste ayrı yazılırsa biri diğerinin görmediğini görür ve hangisinin doğru olduğu
# belirsizleşir. Atlanan sayı raporda yazılı -- kapsam daralması sessiz olmasın.
SKIP = BINARY_SUF

CLASSES = {
    "third_party": "üçüncü taraf (POSTERv2/CrossViT mirası, beyanlı muaf)",
    "declared": "tek tek gerekçelendirilmiş kalıntı",
    "dated": "tarihli rapor sınıfı (o günün gerçeği, geriye dönük değişmez)",
    "UNDECLARED": "BEYAN EDİLMEMİŞ",
}

# KAPSAM DIŞI AMA DİSKTE — kapının beyanlı listesine düşülen not (8 Ağu kararı K1, Fatih).
#
# Bu iki dosya C kovasına alındı: repro deposunun konusu makalenin sayıları, bizim ihraç
# altyapımız değil. Diskte kalmalarının nedeni Fatih'in kapı notunun birebir kendisi:
#
#     "sync silme yapmaz; depo günü sil/yeniden-kur zaten sıfırdan kurar."
#
# Beyanlı muaf DEĞİLLER ve öyle işaretlenmeyecekler — kapı onlar için düşmeye devam eder.
# Buradaki not muafiyet değil, TEŞHİS: kapı düştüğünde okuyan kişi nedenini ve çözümünü
# aynı yerde görsün diye duruyor. Çözüm silmektir (ya da depo günü sıfırdan kurmaktır),
# beyan etmek değil.
OUT_OF_SCOPE_NOTE = {
    "diagnostics/export_to_drive.py":
        "8 Ağu'da C kovasına alındı (ihraç altyapısı, makalenin sayısı değil); "
        "silinmeli — sync silme yapmaz, depo günü sil/yeniden-kur sıfırdan kurar.",
    "tools/sanitize_public_export.py":
        "8 Ağu'da C kovasına alındı (ihraç altyapısı, makalenin sayısı değil); "
        "silinmeli — sync silme yapmaz, depo günü sil/yeniden-kur sıfırdan kurar.",
}


def classify(rel):
    if rel in THIRD_PARTY:
        return "third_party"
    if rel in DECLARED_ABS:
        return "declared"
    if DECLARED_DATED.match(rel):
        return "dated"
    return "UNDECLARED"


def scan(public):
    """(rows, skipped, unreadable) -- okunamayan dosyalar SESSİZCE ATLANMAZ, sayılır.

    HATA SINIFI BOŞ DEĞİLKEN GEÇTİ RAPORLANMAZ (9 Ağu 2026 kuralı, Fatih). Bu döngü
    `except OSError: continue` ile okunamayan dosyayı sessizce geçiyordu -- yani o dosyaya
    soru hiç sorulmuyor ama kapı yine "GEÇTİ" diyebiliyordu. Level-1 kapısının `başka hata`
    sütununun aynısı, ve orada 8 Ağu'da tam bu yüzden üç gerçek ihlal gizlenmişti.
    """
    rows, skipped, unreadable = [], 0, []
    for p in sorted(public.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.suffix.lower() in SKIP:
            skipped += 1
            continue
        try:
            data = p.read_bytes()
        except OSError as e:
            unreadable.append({"path": str(p.relative_to(public)).replace("\\", "/"),
                               "error": type(e).__name__})
            continue
        hits = ABS_ANY.findall(data)
        if not hits:
            continue
        rel = str(p.relative_to(public)).replace("\\", "/")
        rows.append({"path": rel, "class": classify(rel), "matches": len(hits)})
    return rows, skipped, unreadable


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    # BEYANLI DUSUS (23 Agu 2026). Senkron/bant modulu yoksa (public depo) kapi GECTI demez;
    # ne yapamadigini SOYLER ve cikis 2 verir -- 'denetlenemedi' ile 'ihlal yok' ayni sey degil.
    if not SYNC_OK:
        print("DENETLENEMEDI: senkron beyanlari bu depoda yok "
              f"({SYNC_ERR}). Mutlak-yol kapisi yalniz calisma deposunda kosar; "
              "bu arsivdeki kopya beyan icin duruyor. Cikis 2.")
        return 2
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", type=Path, default=PUBLIC)
    # `parse_known_args` -- ŞART. Level-1 kapısı üreticileri `runpy` ile çağırıyor ve betiğin
    # yolunu argv[1]'de bırakıyor; `parse_args` bunu tanımadığı argüman sayıp SystemExit
    # atıyor ve kapı "başka hata" yazıyor. Yani Level-1 sorusu hiç sorulmamış oluyor. Dört
    # kardeş betik (level1_gate, public_repo_sync, student_ts_baseline, bootstrap_cis) hâlâ
    # bu durumda; yenisi eklenirken aynı gürültüye katılmasın diye burada kapatıldı.
    args, _unknown = ap.parse_known_args()

    rows, skipped, unreadable = scan(args.public)
    n = Counter(r["class"] for r in rows)
    bad = [r for r in rows if r["class"] == "UNDECLARED"]
    fell = bool(bad or unreadable)

    # HEDEF, SÜRÜCÜ HARFİYLE DEĞİL ADIYLA yazılır: bu rapor de yayımlanıyor ve kendi
    # kapısına takılmaması gerekiyor (ilk sürümde tam bunu yaptı -- kapı kendi raporunu
    # ihlal saydı ve yazılmasını engelledi). Klasör adı okur için yeterli bilgi.
    L = ["# Mutlak-yol kapısı — diske YAZILANDA beyansız mutlak yol var mı", "",
         f"Hedef klasör: `{args.public.name}`", "",
         "> **Neden senkronun kendi doğrulamasından ayrı.** `public_repo_sync.py` \"hiçbir "
         "dosyada mutlak yol kalmadı\" derken kendi DÖNÜŞÜMÜNE bakar; bu kapı DİSKE yazılana "
         "bakar. Senkron hiç yazmadığı — ya da bir gün yazıp sonra kapsam dışına çıkardığı — "
         "bir dosyayı göremez.", "",
         "> **Neden grep değil.** Gönderim dizisi 1c'nin ilk hâli yalnız kampanya deposunun "
         "önekini arayan tek bir `grep` idi. Ölçüldü: o desen 0 derken diskte 21 dosya "
         "mutlak yol taşıyordu — başka veri kökleri, başka kullanıcı ev dizinleri, UNC "
         "payları ve JSON kaçışlı çift-ters-bölü biçimi. Bu kapı deseni "
         "`public_repo_sync.ABS_ANY`'den ithal eder, yeniden yazmaz.", "",
         "> **Hata sınıfı boş değilken GEÇTİ raporlanmaz** (9 Ağu 2026 kuralı). Bu betik "
         "okunamayan bir dosyayı `except OSError: continue` ile sessizce geçiyordu — o dosyaya "
         "soru sorulmuyor ama kapı yine GEÇTİ diyebiliyordu. Level-1 kapısında aynı desen "
         "(`başka hata` sütunu) üç gerçek ihlali gizlemişti. Okunamayan dosya artık sayılıyor "
         "ve sıfır değilse kapı düşüyor.", "",
         f"**SONUÇ: {'KAPI DÜŞTÜ' if fell else 'KAPI GEÇTİ'}** — beyansız mutlak yol "
         f"{len(bad)} · okunamayan dosya {len(unreadable)}",
         "",
         "**Birim: DOSYA.** Bir dosyada kaç eşleşme olduğu ayrı sütunda; kapı dosya sayar.", "",
         "| sınıf | dosya | eşleşme |", "|---|---|---|"]
    for cls in ("UNDECLARED", "declared", "third_party", "dated"):
        sel = [r for r in rows if r["class"] == cls]
        if not sel and cls != "UNDECLARED":
            continue
        L.append(f"| {CLASSES[cls]} | {len(sel)} | {sum(r['matches'] for r in sel)} |")
    L += [f"| **toplam** | **{len(rows)}** | **{sum(r['matches'] for r in rows)}** |", "",
          f"Metin dışı (ikili) dosya atlandı: {skipped}. Uzantı listesi betikte yazılı — "
          "kapsam daralması sessiz olmasın. **Okunamayan dosya: "
          f"{len(unreadable)}** (sıfır olmak zorunda; değilse kapı düşer).", ""]
    if unreadable:
        L += ["## Okunamayan dosyalar — kapının düşme sebebi", "", "| dosya | hata |",
              "|---|---|"] + [f"| `{u['path']}` | {u['error']} |" for u in unreadable] + [""]

    if bad:
        L += ["## Beyansız kalıntılar — kapının düşme sebebi", "",
              "| dosya | eşleşme | not |", "|---|---|---|"]
        L += [f"| `{r['path']}` | {r['matches']} | "
              f"{OUT_OF_SCOPE_NOTE.get(r['path'], '—')} |" for r in bad]
        L += ["", "Bir dosya ya dönüştürülür, ya kapsam dışına çıkarılıp SİLİNİR, ya da "
                  "`public_repo_sync.DECLARED_ABS` içinde tek tek gerekçelendirilir. Üçüncüsü "
                  "bir karardır; sessizce kalması karar değildir. Yukarıdaki not sütunu "
                  "muafiyet DEĞİL teşhistir: notu olan dosya için de kapı düşer.", ""]

    L += ["## Beyanlı listenin tamamı", "",
          "Depo günü \"36'dan şuna indi, kalanlar şunlar ve muaf\" cümlesi bu tablodan "
          "kurulur.", "", "| dosya | sınıf | eşleşme |", "|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["class"] != "UNDECLARED", r["path"])):
        L.append(f"| `{r['path']}` | {CLASSES[r['class']]} | {r['matches']} |")
    L += ["", "---", "", "Üretici: `diagnostics/abs_path_gate.py` · desen ve beyan sınıfları "
                        "`public_repo_sync`'ten ithal (tek kaynak)", ""]

    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"public": args.public.name, "unit": "file (not match)",
         "total_files": len(rows), "total_matches": sum(r["matches"] for r in rows),
         "by_class": dict(n), "skipped_binary": skipped,
         "unreadable": unreadable, "verdict": "DÜŞTÜ" if fell else "GEÇTİ",
         "undeclared": [r["path"] for r in bad], "rows": rows},
        indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  mutlak yol taşıyan DOSYA : {len(rows)}  "
          f"(eşleşme {sum(r['matches'] for r in rows)})")
    for cls in ("declared", "third_party", "dated", "UNDECLARED"):
        print(f"    {n.get(cls, 0):3d}  {CLASSES[cls]}")
    print(f"  okunamayan dosya         : {len(unreadable)}")
    if bad:
        print("\n  !! beyansız mutlak yol:")
        for r in bad:
            print(f"       {r['path']}")
    if unreadable:
        print("\n  !! okunamadı (soru sorulamadı):")
        for u in unreadable:
            print(f"       {u['path']}  ({u['error']})")
    print(f"\n  SONUÇ: {'KAPI DÜŞTÜ' if fell else 'KAPI GEÇTİ'}"
          f"  (beyansız {len(bad)} · okunamayan {len(unreadable)})")
    print(f"  rapor -> {OUT_MD.relative_to(ROOT)}")
    return 1 if fell else 0


if __name__ == "__main__":
    sys.exit(main())
