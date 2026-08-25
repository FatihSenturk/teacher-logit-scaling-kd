"""Koşu manifesti sayımı: "hangi 90?" sorusunun cevabı sayımın YANINDA dursun.

NEDEN VAR (20 Ağu 2026, N19b). §4.8 dört sayı basıyordu -- 90 / 26 / 62 / 2 -- ve dördü de
kayıtsızdı: hiçbir artefakt alanı yoktu, dolayısıyla "90 neyin 90'ı" sorusu ancak dosya sayarak
cevaplanabiliyordu. Bir sayıyı üreticiye bağlamak, sayının kendisini kaydetmekten ibaret değil;
POPÜLASYONU da kaydetmek. Bu yüzden pencere tanımı burada AÇIK bir alan olarak duruyor ve
sınırları elle yazılmıyor, sayılan manifestlerin kendi zaman damgalarından TÜRETİLİYOR --
yarın bir manifest daha yazılırsa pencere kendiliğinden kayar, sayı ile etiketi ayrışamaz.

ÖLÇÜLEN. `results/unified_students/<run_name>/<zaman-damgası>/manifest.json` dosyalarının
tamamı; her biri için `code_state_verified` üç durumdan birinde:
  True   -> manifest koşu KALKARKEN yazıldı, kod durumu doğrulandı
  False  -> manifest GERİYE DÖNÜK yeniden kuruldu ve öyle işaretlendi
  None   -> koşunun `metrics_best.json`ı yok (yarım kalmış ya da çökmüş koşu)
Üçü toplanınca manifest sayısını vermeli; vermezse `checksum_ok` False çıkar ve bu bir hatadır.

ÖLÇÜLMEYEN. Bu betik hangi koşunun makalede kullanıldığını sormaz -- o `runs.csv` ve
`selection_audit`in işi. Burada sayılan şey MANIFEST'tir, koşu değil; ikisi ancak her koşunun
tam bir manifesti varsa aynı sayıdır ve bu dosyanın ölçtüğü de tam olarak budur.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/run_manifest_census.{md,json}
Kullanım: python diagnostics/run_manifest_census.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDENTS = ROOT / "results" / "unified_students"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
STAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-\d{2}-\d{2}-\d{2}$")


def stamp_of(run_dir):
    """`<run>/<YYYY-MM-DD-hh-mm-ss>` dizin adından tarih. Ad desene uymuyorsa None."""
    m = STAMP.match(run_dir.name)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def window_label(lo, hi):
    """(2026,6,17),(2026,7,24) -> '17 June--24 July 2026'. Etiket ELLE YAZILMAZ; sayımın
    kendi uçlarından üretilir ki etiket ile sayı asla ayrışmasın."""
    if lo[0] == hi[0]:
        return f"{lo[2]} {MONTHS[lo[1] - 1]}--{hi[2]} {MONTHS[hi[1] - 1]} {hi[0]}"
    return (f"{lo[2]} {MONTHS[lo[1] - 1]} {lo[0]}--"
            f"{hi[2]} {MONTHS[hi[1] - 1]} {hi[0]}")


def census():
    rows, undated = [], []
    for m in sorted(STUDENTS.glob("*/*/manifest.json")):
        d = json.loads(m.read_text(encoding="utf-8"))
        st = stamp_of(m.parent)
        if st is None:
            undated.append(str(m.relative_to(ROOT)))
        rows.append({
            "run_name": m.parent.parent.name,
            "run_stamp": m.parent.name,
            "date": st,
            "code_state_verified": d.get("code_state_verified"),
            "retroactive": bool(d.get("retroactive")),
            "has_finished_utc": d.get("finished_utc") not in (None, "None", ""),
        })

    dated = [r["date"] for r in rows if r["date"]]
    lo, hi = (min(dated), max(dated)) if dated else (None, None)
    n_true = sum(1 for r in rows if r["code_state_verified"] is True)
    n_false = sum(1 for r in rows if r["code_state_verified"] is False)
    n_none = sum(1 for r in rows if r["code_state_verified"] is None)

    return {
        "population": ("results/unified_students/<run>/<stamp>/manifest.json -- HEPSI; "
                       "bir alt kume degil, bir suzgec degil"),
        "window": {
            "definition": ("sayilan manifestlerin kendi zaman damgalarinin ALT ve UST siniri; "
                           "elle yazilmis bir tarih araligi DEGIL"),
            "first_run_stamp": min((r["run_stamp"] for r in rows if r["date"]), default=None),
            "last_run_stamp": max((r["run_stamp"] for r in rows if r["date"]), default=None),
            "label": window_label(lo, hi) if dated else None,
            "n_undated_dirs": len(undated),
            "undated_dirs": undated,
        },
        "n_manifests": len(rows),
        "n_code_state_verified": n_true,
        "n_retroactive_unverified": n_false,
        "n_unfinished": n_none,
        "checksum_ok": (n_true + n_false + n_none) == len(rows),
        "cross_checks": {
            "retroactive_flag_true": sum(1 for r in rows if r["retroactive"]),
            "unverified_and_retroactive": sum(1 for r in rows
                                              if r["code_state_verified"] is False
                                              and r["retroactive"]),
            "unfinished_without_finished_utc": sum(1 for r in rows
                                                   if r["code_state_verified"] is None
                                                   and not r["has_finished_utc"]),
        },
        "rows": sorted(({"run_name": r["run_name"], "run_stamp": r["run_stamp"],
                         "code_state_verified": r["code_state_verified"],
                         "retroactive": r["retroactive"]} for r in rows),
                       key=lambda r: (r["run_stamp"], r["run_name"])),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    c = census()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "run_manifest_census.json").write_text(
        json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")

    w = c["window"]
    L = ["# Run-manifest census -- which 90?", "",
         "Producer: `diagnostics/run_manifest_census.py`. The window is **derived from the "
         "counted manifests' own timestamps**, not typed in; label and count cannot drift "
         "apart.", "",
         "| field | value |", "|---|---|",
         f"| population | `{c['population']}` |",
         f"| window | **{w['label']}** (`{w['first_run_stamp']}` … `{w['last_run_stamp']}`) |",
         f"| manifests | **{c['n_manifests']}** |",
         f"| written at launch, code state verified | **{c['n_code_state_verified']}** |",
         f"| reconstructed retroactively (`code_state_verified:false`) | "
         f"**{c['n_retroactive_unverified']}** |",
         f"| unfinished runs (`code_state_verified:null`) | **{c['n_unfinished']}** |",
         f"| three classes sum to the total | **{c['checksum_ok']}** |", "",
         "### Cross-checks", "",
         "| check | n |", "|---|---|",
         f"| manifests carrying `retroactive:true` | {c['cross_checks']['retroactive_flag_true']} |",
         f"| unverified **and** flagged retroactive | "
         f"{c['cross_checks']['unverified_and_retroactive']} |",
         f"| unfinished **and** without `finished_utc` | "
         f"{c['cross_checks']['unfinished_without_finished_utc']} |", ""]
    (OUT_DIR / "run_manifest_census.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"manifest {c['n_manifests']} · dogrulanmis {c['n_code_state_verified']} · "
          f"geriye donuk {c['n_retroactive_unverified']} · yarim {c['n_unfinished']} · "
          f"pencere {w['label']} · toplam tutuyor: {c['checksum_ok']}")
    return 0 if c["checksum_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
