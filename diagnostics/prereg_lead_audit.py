"""S11 lead sütununun üreticisi — beyan→fırlatma aralığı, donmuş kayıttan.

NEDEN VAR (21 Ağu 2026, jeton final turu). S11'in Lead sütunu bugüne kadar tamamen
MUAFTI ve gerekçesi "yapılandırılmış artefaktı yok" idi. Ama artefakt aslında var:
`diagnostics/PREREGISTRATIONS.md` her kalem için **donduruldu** (beyan artefaktının
o günkü mtime'ı) ve **ilk koşu başladı** (koşu dizininin adındaki fırlatma damgası)
alanlarını TARİHLİ kayıt olarak taşıyor. Bu betik o kaydı AYRIŞTIRIR, aralığı
hesaplar ve alan olarak yazar — makale tarafı artık sayıya değil alana bağlanır.

KAYNAK TARİHLİ BEYAN KAYDIDIR, DOKUNULMAZ: bu betik PREREGISTRATIONS.md'yi yalnız
okur. Zaman damgalarını yeniden ÖLÇMEZ (dosya mtime'ları git işlemleriyle çürür;
kayıt, ölçümün yapıldığı günün gerçeğidir ve sağlaması commit geçmişidir).

YUVARLAMA ÜRETİCİDE YAPILMAZ (N19b kuralı: yazım anında yuvarlama = üretici tarafı
çift yuvarlama). Alanlar ham saniye/saat taşır; makale tarafının "12 h" / "8 h"
değerleri defterde `int_floor` kipiyle bağlanır — Lead bir "en geç şu kadar önce
donduruldu" iddiasıdır, alt sınır gibi AŞAĞI yuvarlanır. Ölçüldü: A8 = 12sa57dk
(12.954 sa) → floor 12; yarı-yukarı 13 verirdi ve 20 Ağu'ya kadar basılı değer
tam da oydu. A2 = 8sa43dk (8.724 sa) → floor 8 (yarı-yukarı 9 verirdi; basılı 8
baştan beri taban kipiyle tutarlıydı).

İKİ SAĞLAMA:
  1. Kayıttaki el yazısı açıklama ("+20 saniye", "+8 sa 43 dk") hesaplanan aralıkla
     dakika hassasiyetinde karşılaştırılır (kayıt dakikaya kırpar).
  2. runs.csv'de `preregistration_block` o bloğu gösteren EN ERKEN koşunun damgası,
     kayıttaki "ilk koşu başladı" ile birebir karşılaştırılır. FERPlus blokları
     (A3, A4) RAF-DB koşu defterinde yoktur; oralarda bu sağlama "yok" yazar,
     uydurulmaz.

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/prereg_lead_audit.{json,md}
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "diagnostics" / "PREREGISTRATIONS.md"
RUNS = ROOT / "runs.csv"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

HEAD = re.compile(r"^### (A\d+) · (.+)$", re.M)
FROZEN = re.compile(r"\|\s*\*\*(?:beyan )?donduruldu\*\*\s*\|\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?)")
LAUNCH = re.compile(r"\|\s*\*\*ilk koşu başladı\*\*\s*\|\s*`?(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})`?")
ANNOT = re.compile(r"\*\*ilk koşu başladı\*\*[^\n]*\(\*\*\+([^*]+)\*\*\)")

# S11'de Lead taşıyan altı kalem (tablo satırı <-> blok eşlemesi bir BEYANDIR, çıkarım değil;
# satır adları tab:app_predecl'dekiyle aynı sırada durur ki fark gözle görülsün).
LEAD_BEARING = {
    "A1": "Control teacher, flat response",
    "A2": "Miscalibration pilot kill-switch",
    "A3": "Second-dataset replication",
    "A4": "Human-alignment arm",
    "A7": "Logit standardisation, three seeds",
    "A8": "Oracle-gate extension",
}


def parse_annot(txt):
    """'20 saniye' -> 20 s · '8 sa 43 dk' -> 31380 s. Anlaşılmazsa None (tahmin yok)."""
    m = re.fullmatch(r"(\d+)\s*saniye", txt.strip())
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"(\d+)\s*sa(?:\s*(\d+)\s*dk)?", txt.strip())
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2) or 0) * 60
    return None


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    text = SRC.read_text(encoding="utf-8")
    heads = list(HEAD.finditer(text))
    earliest = {}
    for r in csv.DictReader(open(RUNS, encoding="utf-8")):
        b = r.get("preregistration_block", "")
        if b and (b not in earliest or r["timestamp"] < earliest[b]):
            earliest[b] = r["timestamp"]

    items = {}
    for i, h in enumerate(heads):
        block = h.group(1)
        chunk = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        # `####` alt bölümleri (örn. A8-tamamlama/P5) KENDİ donma/fırlatma kayıtlarını taşır;
        # kalem alanları yalnız alt bölüm başlamadan önceki bölümden okunur. İlk sürüm bunu
        # yapmıyordu ve A8'in açıklama sağlaması P5'in "+29 saniye"sini yakalayıp DURDU —
        # koruma doğru çalıştı, ayrıştırıcı dardı.
        sub = chunk.find("\n#### ")
        chunk = chunk if sub < 0 else chunk[:sub]
        fm, lm = FROZEN.search(chunk), LAUNCH.search(chunk)
        am = None
        if lm:  # açıklama, fırlatma satırının KENDİSİNDE aranır; komşu kayıttan alınmaz
            eol = chunk.find("\n", lm.start())
            am = ANNOT.search(chunk[chunk.rfind("\n", 0, lm.start()) + 1:
                                    eol if eol >= 0 else len(chunk)])
        rec = {"title": h.group(2).strip(), "frozen": fm.group(1) if fm else None,
               "first_run": lm.group(1) if lm else None,
               "lead_seconds": None, "lead_hours": None,
               "recorded_annotation": am.group(1).strip() if am else None,
               "annotation_match": None, "runs_csv_first": earliest.get(block),
               "runs_csv_match": None}
        if fm and lm:
            f = fm.group(1)
            fro = datetime.strptime(f, "%Y-%m-%d %H:%M:%S" if f.count(":") == 2
                                    else "%Y-%m-%d %H:%M")
            lau = datetime.strptime(lm.group(1), "%Y-%m-%d-%H-%M-%S")
            sec = (lau - fro).total_seconds()
            rec["lead_seconds"] = sec
            rec["lead_hours"] = sec / 3600.0
            if rec["recorded_annotation"] is not None:
                want = parse_annot(rec["recorded_annotation"])
                # Kayıt dakikaya kırpar; 60 sn tolerans o kırpmanın kendisidir.
                rec["annotation_match"] = (want is not None and 0 <= sec - want < 60)
            if rec["runs_csv_first"] is not None:
                rec["runs_csv_match"] = (rec["runs_csv_first"] == rec["first_run"])
        items[block] = rec

    missing = [b for b in LEAD_BEARING if items.get(b, {}).get("lead_seconds") is None]
    if missing:
        raise SystemExit(f"DUR: Lead taşıyan kalemlerin kaydı çözülemedi: {missing}")
    bad = [b for b, r in items.items()
           if r["annotation_match"] is False or r["runs_csv_match"] is False]
    if bad:
        raise SystemExit(f"DUR: sağlama uyuşmadı: {bad} — kayıt ile hesap/koşu defteri ayrışıyor.")

    leads = {b: items[b]["lead_seconds"] for b in LEAD_BEARING}
    out = {
        "source": "diagnostics/PREREGISTRATIONS.md (tarihli beyan kaydı; yalnız okunur)",
        "note": "lead_seconds/lead_hours HAM değerdir; makale tarafı defterde int_floor "
                "kipiyle bağlanır (Lead bir üst-sınır-öncesi iddiasıdır, aşağı yuvarlanır). "
                "runs_csv_match yalnız RAF-DB koşu defterindeki bloklar için mümkündür; "
                "A3/A4 (FERPlus) için 'yok' doğru cevaptır, tahmin yazılmaz.",
        "lead_bearing_rows": LEAD_BEARING,
        "items": items,
        "summary": {
            "min_lead_seconds": min(leads.values()),
            "max_lead_seconds": max(leads.values()),
            "min_lead_block": min(leads, key=leads.get),
            "max_lead_block": max(leads, key=leads.get),
            "n_lead_bearing": len(LEAD_BEARING),
            "n_annotation_checked": sum(1 for r in items.values()
                                        if r["annotation_match"] is True),
            "n_runs_csv_checked": sum(1 for r in items.values()
                                      if r["runs_csv_match"] is True),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "prereg_lead_audit.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    L = ["# S11 Lead sütunu — beyan→fırlatma aralıkları, donmuş kayıttan", "",
         "Kaynak: `diagnostics/PREREGISTRATIONS.md` · üretici: `diagnostics/prereg_lead_audit.py`", "",
         "| blok | donduruldu | ilk koşu | lead | not sağlaması | koşu defteri |",
         "|---|---|---|---|---|---|"]
    for b, r in sorted(items.items(), key=lambda kv: int(kv[0][1:])):
        if r["lead_seconds"] is None:
            lead = "—"
        elif r["lead_seconds"] < 3600:
            lead = f"{r['lead_seconds']:.0f} s"
        else:
            lead = f"{r['lead_hours']:.4f} sa"
        ann = {True: "✓", False: "✗", None: "—"}[r["annotation_match"]]
        rcs = {True: "✓", False: "✗", None: "yok"}[r["runs_csv_match"]]
        L.append(f"| {b} | {r['frozen'] or '—'} | {r['first_run'] or '—'} | {lead} | {ann} | {rcs} |")
    L += ["", f"Lead taşıyan {len(LEAD_BEARING)} kalem: en kısa "
          f"{out['summary']['min_lead_seconds']:.0f} s ({out['summary']['min_lead_block']}), "
          f"en uzun {out['summary']['max_lead_seconds']/3600:.4f} sa "
          f"({out['summary']['max_lead_block']})."]
    (OUT_DIR / "prereg_lead_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    for b in LEAD_BEARING:
        r = items[b]
        print(f"{b}: lead {r['lead_seconds']:.0f} s = {r['lead_hours']:.4f} sa · "
              f"not {r['annotation_match']} · runs.csv {r['runs_csv_match']}")
    print(f"-> {OUT_DIR / 'prereg_lead_audit.json'}")


if __name__ == "__main__":
    main()
