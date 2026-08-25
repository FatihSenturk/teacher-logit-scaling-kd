"""Level-1 DEĞİŞMEZİ: her tablo üreticisi koşu dizinleri OLMADAN çalışabilmeli.

NEDEN VAR (8 Ağu). Deponun "makaledeki her sayı ham koşu dizini olmadan türetilebilir"
özelliği bir DEĞİŞMEZ, ve 7 Ağu'da yazılan tek bir betik (`tstar_provenance.py`) onu
sessizce bozdu: `results/unified_students/` altındaki her koşunun `run_args.json`'unu
tarıyordu. 18 üreticinin 17'si uyuyordu, yani ihlal görünmüyordu — tesadüfen yakalandı.

Tesadüfe bırakılmaz. Bu kapı üreticileri **koşu dizinleri erişilemez durumdayken**
çalıştırır: `results/unified_students/` veya `results/teacher_logs/` altında bir şey
açmaya çalışan her betik `LEVEL1-VIOLATION` ile düşer ve adıyla raporlanır.

NEDEN ÇALIŞMA ZAMANI, STATİK TARAMA DEĞİL. Statik tarama (`grep unified_students`) yorum
satırlarında yanlış pozitif, dolaylı erişimde (bir yardımcı modül üzerinden) yanlış
negatif verir. Çalıştırmak asıl soruyu sorar: **bu betik o dizinler olmadan işini
bitirebiliyor mu?**

KAPSAM İHRAÇ LİSTESİNDEN TÜRETİLİR. Hangi betiğin yayımlanan bir artefakt ürettiği
`export_to_drive.EXPORTS`'ta zaten beyanlı; buraya elle ikinci bir liste yazmak o beyanla
ayrışırdı. Yalnız `diagnostics/*.py` üreticileri sınanır (elle yazılan dosyaların ve
figür ikililerinin üreticisi yoktur).

MEŞRU İSTİSNALAR açıkça beyan edilir (`ALLOWED`): ölçüm/defter betikleri koşu dizinlerini
okumak ZORUNDA -- işleri o. Onlar Level 3'tür ve README'de öyle etiketlidir.

HATA SINIFI BOŞ DEĞİLKEN GEÇTİ RAPORLANMAZ (9 Ağu 2026 kuralı, Fatih). Bu kapı 8 Ağu'da
"İHLAL 0" dedi ve DOĞRUYDU -- ama `başka hata` sütununda 9 betik duruyordu ve o sütun "ihlal
yok" demek DEĞİL, **"soru sorulamadı"** demekti. Beş harness arızası (glob sarmalayıcısı,
`parse_args`, kendini koşturma, konsol kodlaması, `sys.path`) düzeltilip sütun 0'a indiğinde
arkasından ÜÇ gerçek ihlal çıktı. Ders: kapının kapsamı da bir kapı ister.

Kural artık kodda: `İHLAL == 0` yetmez. `başka hata` / `zaman aşımı` / `yok` sınıflarındaki
her kalem ya sıfır olacak ya `DECLARED_ERRORS` içinde gerekçeli duracak; yoksa SONUÇ satırı
GEÇTİ yazmaz ve çıkış kodu 1 olur.

Kullanım: python diagnostics/level1_gate.py [--timeout 600]
Çıktı -> diagnostics/reports/level1_gate.md (+ .json); ihlal varsa çıkış kodu 1.
"""
import argparse
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

OUT_MD = ROOT / "diagnostics" / "reports" / "level1_gate.md"
OUT_JSON = ROOT / "diagnostics" / "reports" / "level1_gate.json"

# Koşu dizinlerini okumak İŞİ olan betikler. Level 3, README'de öyle etiketli.
ALLOWED = {
    "diagnostics/build_runs_ledger.py",        # defteri koşu dizinlerinden kurar
    "diagnostics/publish_student_logits.py",   # 42 logit önbelleğini koşu dizinlerinden YAYIMLAR
    "diagnostics/publish_epoch_curves.py",     # epok-başına val eğrilerini YAYIMLAR
    "diagnostics/selection_audit_table.py",    # checkpoint'leri ölçer
    "diagnostics/ferplus_selection_audit.py",
    "diagnostics/mark_abandoned_runs.py",      # yarım koşuları işaretler
    "diagnostics/build_replicate_queue.py",    # referans run_args'tan kuyruk üretir
    "diagnostics/export_to_drive.py",          # bant; koşu dizinlerini ihraç ETMEZ ama tarar
    "diagnostics/control_grid_refinement.py",  # ad->parametre kapısı run_args okur
    "diagnostics/latency_benchmark.py",        # checkpoint yükler
    "diagnostics/calibration_cache_audit.py",
    # 20 Agu 2026 (N19b): §4.8'in manifest sayimi. Sayilan sey KOSU DIZINLERINDEKI
    # manifest.json'lardir; kosu agaci olmadan sorulacak bir soru degil, isi tam olarak o.
    # Ciktisi (sayimlar + pencere etiketi) Level-1 temiz bir artefakt olarak yayimlanir.
    "diagnostics/run_manifest_census.py",
    # 23 AGU 2026 (bant bosluk turu) -- ALTI OLCUM BETIGI. Bunlar bu kapiya BUGUN girdi:
    # kapinin kapsami `export_to_drive.EXPORTS`ten turer ve artefaktlari bugune kadar bantta
    # DEGILDI, yani Level-1 sorusu onlara hic sorulmamisti. Soru sorulunca altisi da koSU
    # AGACINA dokundugu icin dustu. BU BIR BEYANDIR, ONARIM DEGIL: her biri checkpoint ya da
    # ornek-basina logit okumak zorunda -- olctukleri sey orada. Artefaktlari (yayimlanan
    # JSON'lar) Level-1 temiz: makaledeki sayi ham kosu agaci olmadan DOGRULANABILIR, ama
    # bugun YENIDEN URETILEMEZ.
    # ONARIM DESENI BELLI VE ACIK IS OLARAK YAZILI: `ferplus_student_jsd.py --from-runs`
    # ornegindeki ayrim -- varsayilan yol yayimlanmis onbellekten okur, kosu agacini taramak
    # AYRI bir eylemdir. Ozellikle `reliability_diagram.py` ve `perclass_calibration.py`
    # zaten `student_logit_cache` uzerinden gidiyor ve o onbellegin yayimlayicisi
    # (`publish_student_logits.py`) depoda duruyor; ikisi icin onarim kucuk gorunuyor.
    # Gonderim arifesinde alti betigi birden degistirmedim -- beyan ettim, olctum, yazdim.
    "diagnostics/reliability_diagram.py",       # ornek-basina ogrenci logitleri (guvenilirlik)
    "diagnostics/perclass_calibration.py",      # ayni onbellek, sinif basina kirilim
    "diagnostics/rafdb_signal_quality_table.py",  # OGRETMEN checkpoint'i yukler (mu/logvar)
    "diagnostics/vich_isolation_verdict.py",    # ogrenci checkpoint'lerini yukleyip skorlar
    "diagnostics/adaptive_t_headroom_table.py",  # ayni: checkpoint yukler, logit degerlendirir
    "diagnostics/p5_efficiency_frontier.py",    # kosu dizinlerindeki metrics_best/run_args
}

# HATA SINIFI BEYANLARI. `başka hata` / `zaman aşımı` / `yok` sınıfına düşen bir betik BURADA
# gerekçesiyle yazılı olmak zorunda; yoksa kapı GEÇTİ demez. Liste bilerek BOŞ: 9 Ağu'da dokuz
# kalem de gerçek arızaydı ve dokuzu da düzeltildi. Bir kalem buraya yazılacaksa gerekçesi
# "neden bu betiğe Level-1 sorusunu sormak MÜMKÜN DEĞİL" olmalı -- "şimdilik bakamadım"
# değil. Boş kalması hedeftir, esneklik değil.
DECLARED_ERRORS = {}

ERROR_CLASSES = ("başka hata", "zaman aşımı", "yok")

GUARD = textwrap.dedent('''
    import builtins, io, os, pathlib, runpy, sys
    BAD = ("unified_students", "teacher_logs")
    def _bad(p):
        try: s = str(p)
        except Exception: return False
        return any(b in s.replace("\\\\", "/") for b in BAD)
    def _boom(p):
        raise RuntimeError("LEVEL1-VIOLATION: " + str(p))
    _po, _bo = pathlib.Path.open, builtins.open
    pathlib.Path.open = lambda self, *a, **k: (_boom(self) if _bad(self) else _po(self, *a, **k))
    builtins.open = lambda f, *a, **k: (_boom(f) if _bad(f) else _bo(f, *a, **k))
    for mod, fn in ((os, "listdir"), (os, "scandir")):
        _orig = getattr(mod, fn)
        setattr(mod, fn, (lambda o: lambda p=".", *a, **k: (_boom(p) if _bad(p) else o(p, *a, **k)))(_orig))
    _it = pathlib.Path.iterdir
    pathlib.Path.iterdir = lambda self: (_boom(self) if _bad(self) else _it(self))
    # **kw SART (9 Agu duzeltmesi). Sarmalayici `lambda self, pat` idi; Python 3.13'te
    # `Path.rglob` icten `glob`u `case_sensitive=` / `recurse_symlinks=` anahtar
    # argumanlariyla cagiriyor ve sarmalayici TypeError atiyordu. Sonuc: rglob kullanan her
    # betik "baska hata" diye siniflaniyor ve LEVEL-1 SORUSU HIC SORULMUYORDU -- kapinin var
    # olma sebebinin tam tersi. `abs_path_gate.py` eklenince ortaya cikti.
    _gl = pathlib.Path.glob
    pathlib.Path.glob = lambda self, pat, **kw: (_boom(self) if _bad(self)
                                                 else _gl(self, pat, **kw))
    import glob as _g
    _gg = _g.glob
    _g.glob = lambda p, *a, **k: (_boom(p) if _bad(p) else _gg(p, *a, **k))
    runpy.run_path(sys.argv[1], run_name="__main__")
''').strip()


def producers():
    """İhraç listesinden `diagnostics/*.py` üreticileri -- tekil, sıralı."""
    import export_to_drive as ex
    out = []
    for entry in ex.EXPORTS:
        prod = entry[2] if len(entry) > 2 else ""
        for part in str(prod).split(" + "):
            part = part.strip()
            if part.startswith("diagnostics/") and part.endswith(".py") and part not in out:
                out.append(part)
    return sorted(out)


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def worktree_dirty():
    """`git status --porcelain` -> {yol}. Sabit ofset YOK (bkz. producer_freshness_gate:
    `git()` ciktiyi strip ettigi icin ilk satirin bas boslugu kayboluyor ve `ln[3:]` bir
    karakter yiyor)."""
    paths = set()
    for ln in git("status", "--porcelain").splitlines():
        t = ln.strip()
        if not t:
            continue
        parts = t.split(None, 1)
        if len(parts) < 2:
            continue
        p = parts[1]
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        p = p.strip().strip('"')
        if p:
            paths.add(p)
    return paths


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    # BEYANLI DUSUS (23 Agu 2026). Senkron/bant modulu yoksa (public depo) kapi GECTI demez;
    # ne yapamadigini SOYLER ve cikis 2 verir -- 'denetlenemedi' ile 'ihlal yok' ayni sey degil.
    try:
        producers()
    except ModuleNotFoundError as e:   # pragma: no cover -- yalniz public depoda
        print(f"DENETLENEMEDI: ihrac beyani bu depoda yok ({e}). Level-1 kapsami "
              "`export_to_drive.EXPORTS`ten turer; o beyan olmadan hangi betigin "
              "sinanacagi BILINEMEZ ve bos bir liste 'IHLAL 0' gibi gorunurdu. Cikis 2.")
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    rows = []
    # BU KAPI DA URETICI KOSTURUYOR (23 Agu 2026'da olculdu). Level-1 sorusu ancak betigi
    # CALISTIRARAK sorulabiliyor -- ve calisan betik CIKTISINI YAZIYOR. Tazelik kapisinin
    # yan-cikti sozlesmesi burada YOKTU: `selection_distribution_figure.py` her kosuda
    # `paper/figures/selection_distribution.pdf`i yeniden yaziyor, matplotlib PDF'i bayt
    # kararli olmadigi icin dosya kirli kaliyor ve bir sonraki `git add -A` onu sessizce
    # commit'e sokuyordu. Uc kez oldu; ucuncusunde MAKALE FIGURU iki depoya birden girdi.
    # Kural artik burada da ayni: kosudan ONCE temiz olan dosyalar geri yazilir, koSUDAN
    # once zaten kirli olanlara DOKUNULMAZ (kullanicinin isi silinmez).
    dirty0 = worktree_dirty()
    restored = []
    SELF = "diagnostics/level1_gate.py"
    for rel in producers():
        # KENDİNİ KOŞTURMA. Bu betik kendi raporunun üreticisi olduğu için `EXPORTS`'tan
        # türeyen listede kendisi de var. Kendini `runpy` ile çağırmak iç içe TAM bir kapı
        # koşusu başlatır (50 alt süreç, her biri yine 50...). 9 Ağu'ya kadar bu tesadüfen
        # olmuyordu: `parse_args` argv'yi tanımayıp SystemExit atıyordu ve satır "başka hata"
        # görünüyordu. Kardeş betiklerdeki aynı arıza düzeltilirken bu koruma ARIZAYA değil
        # BEYANA bağlandı -- yoksa düzeltme özyinelemeyi açardı.
        if rel == SELF:
            rows.append({"script": rel, "status": "muaf",
                         "note": "kapının kendisi — kendini koşturmak özyineleme olur"})
            continue
        if rel in ALLOWED:
            rows.append({"script": rel, "status": "muaf", "note": "Level 3 — koşu dizini okumak işi"})
            continue
        if not (ROOT / rel).exists():
            rows.append({"script": rel, "status": "yok", "note": "dosya bulunamadı"})
            continue
        try:
            # IHRAC KANCASI KAPATILIR. Boru hatti kancasi betigin SONUNDA calisiyor ve
            # status_heartbeat canli kosuyu ararken results/ altina bakiyor -- bu, betigin
            # KENDI isiyle ilgisi olmayan bir erisim. Kapatilmazsa 15 betik yanlislikla
            # ihlal gorunuyordu (ilk kosuda tam olarak bu oldu).
            env = {**os.environ, "REPO_EXPORT_SKIP": "1"}
            r = subprocess.run([sys.executable, "-c", GUARD, str(ROOT / rel)],
                               cwd=ROOT, capture_output=True, text=True, env=env,
                               timeout=args.timeout, encoding="utf-8", errors="replace")
            err = (r.stderr or "") + (r.stdout or "")
            if "LEVEL1-VIOLATION" in err:
                # Yolu tasiyan satiri sec (traceback'in "raise ..." satirini degil).
                cands = [l.strip() for l in err.splitlines()
                         if "LEVEL1-VIOLATION" in l and "raise " not in l]
                note = (cands[-1] if cands else
                        next(l.strip() for l in err.splitlines() if "LEVEL1-VIOLATION" in l))
                rows.append({"script": rel, "status": "İHLAL", "note": note[:160]})
            elif r.returncode != 0:
                tail = [l for l in err.strip().splitlines() if l.strip()][-1:] or [""]
                rows.append({"script": rel, "status": "başka hata", "note": tail[0][:160]})
            else:
                rows.append({"script": rel, "status": "GEÇTİ", "note": ""})
            for _rel in sorted((worktree_dirty() - dirty0)):
                git("checkout", "--", _rel)      # kapi olcer, calisma agacini birakmaz
                restored.append(_rel)
        except subprocess.TimeoutExpired:
            rows.append({"script": rel, "status": "zaman aşımı", "note": f"> {args.timeout}s"})
        print(f"  {rows[-1]['status']:12s} {rel}")

    bad = [r for r in rows if r["status"] == "İHLAL"]
    # HATA SINIFI KAPISI: beyanlı olmayan her "sorulamadı" kalemi kapıyı düşürür.
    undeclared_err = [r for r in rows if r["status"] in ERROR_CLASSES
                      and r["script"] not in DECLARED_ERRORS]
    write(rows, bad, undeclared_err)
    n = {k: sum(1 for r in rows if r["status"] == k) for k in
         ("GEÇTİ", "İHLAL", "muaf", "başka hata", "zaman aşımı", "yok")}
    print(f"\n  geçti {n['GEÇTİ']} · İHLAL {n['İHLAL']} · muaf {n['muaf']} · "
          f"başka hata {n['başka hata']} · zaman aşımı {n['zaman aşımı']}")
    if restored:
        print(f"  ureticilerin yazdigi {len(restored)} dosya geri yazildi: "
              + ", ".join(sorted(set(restored))[:6]))
    if undeclared_err:
        print(f"\n  !! SORULAMADI: {len(undeclared_err)} betiğe Level-1 sorusu hiç sorulmadı ve "
              f"hiçbiri beyanlı değil. Kapı GEÇTİ RAPORLAMAZ.")
        for r in undeclared_err:
            print(f"       {r['status']:11s} {r['script']}  — {r['note'][:80]}")
    print(f"\n  SONUÇ: {'GEÇTİ' if not (bad or undeclared_err) else 'DÜŞTÜ'}"
          f"  (İHLAL {n['İHLAL']} · beyansız sorulamadı {len(undeclared_err)})")
    return 1 if (bad or undeclared_err) else 0


def write(rows, bad, undeclared_err=()):
    L = ["# Level-1 kapısı — üreticiler koşu dizinleri olmadan çalışıyor mu", "",
         "> **Değişmez:** makaledeki her sayı, `results/` altındaki ham koşu dizinleri "
         "olmadan türetilebilmeli. Koşu dizinleri boyut yüzünden yayımlanmıyor; bu özellik "
         "olmadan public depo Level 1 vaadini tutamaz.", "",
         "> **Neden kapı, uyanıklık değil.** 7 Ağu'da yazılan tek bir betik bu değişmezi "
         "sessizce bozdu (`tstar_provenance.py`, koşu dizinlerini tarıyordu). 18 üreticinin "
         "17'si uyuyordu — ihlal görünmüyordu ve tesadüfen yakalandı.", "",
         "> **HATA SINIFI BOŞ DEĞİLKEN GEÇTİ RAPORLANMAZ** (9 Ağu 2026 kuralı). 8 Ağu'da bu "
         "kapı \"İHLAL 0\" dedi ve doğruydu — ama `başka hata` sütununda 9 betik duruyordu ve "
         "o sütun \"ihlal yok\" demek değil, **\"soru sorulamadı\"** demekti. Arızalar "
         "düzeltilip sütun 0'a indiğinde arkasından üç gerçek ihlal çıktı. Artık "
         "`İHLAL == 0` yetmiyor: hata sınıfındaki her kalem ya sıfır olacak ya "
         "`DECLARED_ERRORS` içinde gerekçeli olacak.", "",
         f"**SONUÇ: {'DÜŞTÜ' if (bad or undeclared_err) else 'GEÇTİ'}** — "
         f"İHLAL {len(bad)} · beyansız \"sorulamadı\" {len(undeclared_err)}", "",
         "Kapsam `export_to_drive.EXPORTS`'tan türetilir (hangi betiğin yayımlanan artefakt "
         "ürettiği orada beyanlı); elle ikinci bir liste tutulmaz.", "",
         "| betik | durum | not |", "|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["status"] != "İHLAL", r["script"])):
        L.append(f"| `{r['script']}` | {r['status']} | {r['note'] or '—'} |")
    L += ["", "**Muaf betikler** koşu dizinlerini okumak ZORUNDA — işleri o (defter kurma, "
              "checkpoint ölçme, canlı koşu bulma). Level 3'türler ve README'de öyle "
              "etiketlidirler; muafiyet burada **beyan** olarak durur, çıkarım olarak değil.", "",
          "> \"başka hata\" ihlal değildir ama **temiz de değildir**: betik koşu dizinlerine "
          "dokunmadan düştü (eksik girdi, eksik bağımlılık, argparse, konsol kodlaması), "
          "yani Level-1 sorusu **sorulamadı**. Ayrı sütunda tutuluyor ki Level-1 sorusu başka "
          "arızalarla karışmasın — ama sütun boş değilken kapı GEÇTİ demez.", ""]
    if undeclared_err:
        L += ["### Beyansız \"sorulamadı\" kalemleri — kapının düşme sebebi", "",
              "| betik | sınıf | not |", "|---|---|---|"]
        L += [f"| `{r['script']}` | {r['status']} | {r['note'] or '—'} |"
              for r in undeclared_err]
        L += ["", "Her kalem ya düzeltilecek ya `level1_gate.DECLARED_ERRORS` içinde "
                  "gerekçelendirilecek. Gerekçe \"neden bu betiğe soru sormak MÜMKÜN DEĞİL\" "
                  "olmalı; \"şimdilik bakılmadı\" gerekçe değildir.", ""]
    L += [
          "---", "", "Üretici: `diagnostics/level1_gate.py`", ""]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"rows": rows, "violations": bad}, indent=2,
                                   ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
