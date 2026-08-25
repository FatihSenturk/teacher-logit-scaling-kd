"""G3.3 — Holm ailesi tablosu ve ailenin NE ZAMAN sabitlendiği.

İTİRAZ (Round-2 panel): §4 eşleştirilmiş t + Holm düzeltmesi bildiriyor; okuyucu ailenin
hangi kontrastlardan oluştuğunu ve — daha önemlisi — bu listenin ne zaman sabitlendiğini
göremiyor. Aile üyeliği sonuçlar görüldükten sonra genişletilip daraltılabilen bir şeydir;
düzeltilmiş p değerleri doğrudan aile boyutuna bağlı olduğu için bu, sessiz bir serbestlik
derecesidir.

BU DOSYA HESAP YAPMAZ. Altı kontrastın sayıları `inferential_tests.py`'nin ürettiği
`paper_tables/inferential_tests.json`'dan OKUNUR; burada yalnız (a) Holm sıralaması açıkça
gösterilir ve (b) ailenin provenance'ı git kaydından belirlenip yazılır. Böylece sayı tek
yerde üretilir, iki dosya arasında sürüklenemez.

PROVENANCE BULGUSU (git'ten, 6 Ağu 2026'da okundu):
  · Aile `f381704` (2026-08-01 14:48) commit'inde tanımlandı ve o hâliyle DEĞİŞMEDİ.
  · Dosyaya dokunan tek diğer commit `a0a07c4` (2026-08-03), yalnız çıktı metnini
    İngilizceye çevirdi; kontrast tanımlarına dokunmadı.
  · Aile ÖN-BEYANLI DEĞİL: 1 Ağu'da, altı kontrastın sonuçları çoktan diskteyken, bir panel
    itirazına ("§4 Holm vaat ediyor, §5 raporlamıyor") cevaben derlendi.
  · Ama aile SONRADAN OYNANMADI: aynı altı satır, tek revizyon yok. "Aile alışverişi"
    (düzeltilmiş p'yi hareket ettirmek için üye ekleyip çıkarma) git'ten yanlışlanabilir
    ve yanlışlanıyor.
İkisi ayrı iddialardır ve ayrı yazılır: ön-kayıtlı olmamak bir zayıflık, sabit kalmak bir
güvence. Biri diğerinin yerine geçmez.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/holm_family.{md,json}
Kullanım: python diagnostics/holm_family.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION  # noqa: E402

SRC = ROOT / "diagnostics" / "paper_tables" / "inferential_tests.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

HONESTY = (
    "> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel "
    "report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is "
    "unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts."
)

PROVENANCE = {
    "family_defined_in_commit": "f381704",
    "family_defined_at": "2026-08-01 14:48",
    "only_other_commit_touching_file": "a0a07c4",
    "only_other_commit_at": "2026-08-03 13:06",
    "only_other_commit_scope": "output prose translated to English; contrast definitions untouched",
    "pre_registered": False,
    "revised_since_definition": False,
}


def fmt_p(p):
    if p is None:
        return "—"
    return f"{p:.2e}" if p < 1e-4 else f"{p:.4f}"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = d["results"]
    m = len(rows)

    # Holm sıralaması: ham p'ye göre artan. adj = max_{j<=i} (m-j) * p_(j), 1'de kırpılır.
    order = sorted(range(m), key=lambda i: rows[i]["p_raw"])
    rank = {idx: k + 1 for k, idx in enumerate(order)}

    L = ["# G3.3 — The Holm family: its members, and when the membership was fixed", "",
         HONESTY, "",
         f"Producer: `diagnostics/holm_family.py` · numbers read from "
         f"`paper_tables/inferential_tests.json` (not recomputed) · @{d['checkpoint']} · "
         f"{SD_CONVENTION} · axis: {d['axis']}", "",
         f"Family size m = **{m}**. All contrasts are within-seed paired, n = 3, df = 2. "
         "Holm step-down: contrasts are ranked by raw p, and the k-th smallest is compared "
         f"against α/(m−k+1); the adjusted p reported here is the standard monotone "
         "transformation of that procedure.", "",
         "| Holm rank | contrast | ΔECE mean ± sd | t | df | p (raw) | p (Holm) |",
         "|---|---|---|---|---|---|---|"]
    for idx in order:
        r = rows[idx]
        L.append(f"| {rank[idx]} | {r['name']} | {r['mean']:+.4f} ± {r['sd']:.4f} | "
                 f"{r['t']:+.2f} | {r['df']} | {fmt_p(r['p_raw'])} | {fmt_p(r['p_holm'])} |")

    n_sig = sum(1 for r in rows if r["p_holm"] < 0.05)
    L += ["",
          f"**{n_sig}/{m}** contrasts survive Holm at α = 0.05. With n = 3 and df = 2 the "
          "procedure has very little power; this table is reported because §4 promises it, not "
          "as a strength claim.", ""]

    # ---- provenance: asıl sorulan
    L += ["## When was the family membership fixed?", "",
          "This is the part a reader cannot check from the paper, so it is answered from the "
          "repository's own history rather than asserted.", "",
          "| question | answer |", "|---|---|",
          f"| defined in | commit `{PROVENANCE['family_defined_in_commit']}`, "
          f"{PROVENANCE['family_defined_at']} |",
          f"| revised since? | **no** — the only other commit touching the file "
          f"(`{PROVENANCE['only_other_commit_touching_file']}`, "
          f"{PROVENANCE['only_other_commit_at']}) "
          f"{PROVENANCE['only_other_commit_scope']} |",
          "| pre-registered? | **no** |", "",
          "**The two facts are separate and are stated separately.**", "",
          "*Not pre-registered.* The family was assembled on 1 Aug 2026 in response to an "
          "earlier panel objection (\"§4 promises paired t and a Holm correction; §5 reports "
          "neither\"). All six contrasts' results were already on disk when the list was "
          "written. So this is not a pre-declared family, and the paper will not call it one.", "",
          "*But not shopped either.* Family membership is the silent degree of freedom here — "
          "adjusted p-values depend directly on m, so adding or dropping members after seeing "
          "the numbers would move them. That did not happen: the same six rows have stood since "
          "the file was created, with no revision. Unlike the previous point, this one is "
          "**falsifiable from git** — and it survives the check.", "",
          "A pre-registered family would have been better. A fixed one is what exists, and the "
          "difference between the two is exactly what this block records.", ""]

    if d.get("not_computable"):
        L += ["## Contrasts that were requested but cannot be supplied", ""]
        nc = d["not_computable"]
        L += [f"- {x}" for x in nc] if isinstance(nc, list) else [str(nc), ""]
        L += [""]

    L += ["Source: `diagnostics/inferential_tests.py` (family definition and all statistics); "
          "this file only re-presents them with the Holm ranking made explicit and adds the "
          "provenance determination.", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "holm_family.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "holm_family.json").write_text(json.dumps(
        {"note": "review-responsive, not pre-declared", "family_size": m,
         "provenance": PROVENANCE,
         "rows": [{"holm_rank": rank[i], **rows[i]} for i in order],
         "n_surviving_holm_005": n_sig}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"aile m={m}, Holm'u gecen (a=0.05): {n_sig}/{m}")
    for idx in order:
        r = rows[idx]
        print(f"  {rank[idx]}. {r['name'][:52]:54s} p_raw {fmt_p(r['p_raw']):>9s} "
              f"p_holm {fmt_p(r['p_holm']):>9s}")
    print(f"\nWrote {OUT_DIR / 'holm_family.md'}")


if __name__ == "__main__":
    main()
