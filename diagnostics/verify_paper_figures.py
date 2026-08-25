"""Audit every PDF in paper/figures/ against the journal's requirements -- from the FILE, not
from the code that wrote it.

The exporters already set rcParams for vector output, TrueType fonts and a 7 pt type floor. That
is an intention, not evidence: bbox_inches="tight" changes the final size, a stray imshow turns
one panel into a bitmap, and mathtext can fall back to a Type 3 font regardless of pdf.fonttype.
This script opens the produced PDF and measures what a typesetter would measure.

FOUR CHECKS, each a hard fail:
  1. VECTOR      no embedded raster image XObjects, EXCEPT where a figure declares them in
                 EXPECT_RASTER below and the count matches exactly. One figure legitimately
                 shows photographs (FER2013 faces), which cannot be vector; declaring the exact
                 count keeps that from becoming a blanket exemption that would hide an
                 accidental imshow elsewhere. Declared rasters also have their pixel dimensions
                 printed, so a silent resample away from the source resolution is visible.
  2. FONTS       no Type 3 fonts, which numerous publishers reject outright and which no prepress
                 tool can edit. Note what "TrueType" looks like in a real matplotlib PDF: with
                 pdf.fonttype=42 the top-level font object is /Type0 with /Encoding Identity-H,
                 and the actual TrueType program hangs off it as a /CIDFontType2 descendant.
                 An earlier version of this check tested only the top-level subtype and failed
                 all six correct figures. So Type0 is accepted ONLY after its descendant is
                 read and confirmed to be CIDFontType2 (TrueType) or CIDFontType0 (CFF).
  3. TYPE SIZE   the smallest ACTUALLY RENDERED glyph size, read from the page's text spans, is
                 at or above the 7 pt floor at the PDF's true page width. This is the only form
                 of the check that survives bbox_inches="tight".
  4. NO TITLE    no text sits above the top of the highest drawing on the page other than a
                 panel letter -- titles belong to the LaTeX caption. Reported as a warning with
                 the offending string, since a legend can legitimately sit high.

Also prints the page width in mm so a figure that silently drifted off 190/90 mm is visible.

Usage:  python diagnostics/verify_paper_figures.py [--grey]   (--grey also writes greyscale PNGs)
"""
import argparse
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "paper" / "figures"
MIN_PT = 7.0
PANEL_LETTER = re.compile(r"^\(?[a-z]\)?$")

# figure -> exactly how many raster images it is allowed to embed, and why.
EXPECT_RASTER = {
    "vote_examples.pdf": 4,   # the four FER2013 48x48 example faces; everything else is vector
}


def descendant_subtype(doc, xref):
    """/Subtype of a Type0 font's descendant, i.e. the font program actually embedded."""
    m = re.search(r"/DescendantFonts\s*\[\s*(\d+)\s+0\s+R", doc.xref_object(xref))
    if not m:
        return None
    m2 = re.search(r"/Subtype\s*/(\w+)", doc.xref_object(int(m.group(1))))
    return m2.group(1) if m2 else None


def audit(path):
    doc = fitz.open(path)
    fails, warns = [], []
    if doc.page_count != 1:
        fails.append(f"{doc.page_count} pages (a figure is one page)")
    page = doc[0]

    imgs = page.get_images(full=True)
    allowed = EXPECT_RASTER.get(Path(path).name, 0)
    if len(imgs) != allowed:
        fails.append(f"{len(imgs)} raster image(s) embedded, expected {allowed}")
    elif imgs:
        dims = ", ".join(f"{im[2]}x{im[3]}" for im in imgs)
        warns.append(f"{len(imgs)} declared raster(s) at {dims} px "
                     f"(confirm these are the source resolutions, i.e. no resampling)")

    bad_fonts = []
    for xref, _ext, subtype, base, *_ in page.get_fonts(full=True):
        if subtype in ("TrueType", "Type1"):
            continue
        if subtype == "Type0":
            desc = descendant_subtype(doc, xref)
            if desc in ("CIDFontType2", "CIDFontType0"):
                continue
            bad_fonts.append(f"{base} (Type0 -> {desc or 'no descendant'})")
        else:
            bad_fonts.append(f"{base} ({subtype})")
    if bad_fonts:
        fails.append("font(s) not embedded as TrueType/Type1/CID: " + ", ".join(bad_fonts))

    sizes, spans = [], []
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for sp in line["spans"]:
                if sp["text"].strip():
                    sizes.append(sp["size"])
                    spans.append((round(sp["size"], 2), sp["bbox"], sp["text"].strip()))
    smallest = min(sizes) if sizes else None
    if smallest is not None and smallest < MIN_PT - 0.05:
        worst = [t for s, _, t in spans if s == round(smallest, 2)][:3]
        fails.append(f"type {smallest:.2f} pt < {MIN_PT} pt floor, e.g. {worst}")

    # A title would be text centred near the top with nothing drawn above it. Panel letters are
    # allowed there by design, so they are excluded by shape rather than by position.
    top = min((b[1] for _, b, _ in spans), default=0)
    high = [t for _, b, t in spans if b[1] <= top + 2 and not PANEL_LETTER.match(t)]
    if high:
        warns.append(f"text at the very top of the page (check it is not a title): {high[:3]}")

    w_mm = page.rect.width / 72 * 25.4
    h_mm = page.rect.height / 72 * 25.4
    doc.close()
    return {"w_mm": w_mm, "h_mm": h_mm, "smallest_pt": smallest,
            "fails": fails, "warns": warns, "n_spans": len(spans)}


def grey_png(path, out_dir, dpi=150):
    """Greyscale render: the colour-blind guarantee is that every series is still separable when
    colour is removed entirely, which is what print-to-mono does."""
    doc = fitz.open(path)
    pm = doc[0].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    out = out_dir / (path.stem + "_grey.png")
    pm.save(out)
    doc.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grey", action="store_true", help="also write greyscale PNGs for eyeballing")
    ap.add_argument("--grey-dir", default=None)
    args = ap.parse_args()

    pdfs = sorted(FIGS.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no PDFs in {FIGS}")
    grey_dir = Path(args.grey_dir) if args.grey_dir else FIGS / "_greyscale"
    if args.grey:
        grey_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'figure':<34}{'mm':>13}{'min pt':>8}{'text':>7}  status")
    n_fail = 0
    for p in pdfs:
        r = audit(p)
        ok = not r["fails"]
        n_fail += not ok
        size = f"{r['w_mm']:.0f}x{r['h_mm']:.0f}"
        sm = f"{r['smallest_pt']:.1f}" if r["smallest_pt"] else "-"
        print(f"{p.name:<34}{size:>13}{sm:>8}{r['n_spans']:>7}  {'OK' if ok else 'FAIL'}")
        for f in r["fails"]:
            print(f"    FAIL  {f}")
        for w in r["warns"]:
            print(f"    note  {w}")
        if args.grey:
            grey_png(p, grey_dir)

    print(f"\n{len(pdfs)} figures, {n_fail} failing. "
          f"Checks: vector-only, TrueType/Type1, >= {MIN_PT} pt rendered, single page.")
    if args.grey:
        print(f"Greyscale renders -> {grey_dir}")
        # Gri provalar ihraç kümesinde; yeniden üretildiklerinde Drive kopyası da tazelenir.
        # Kapı DÜŞTÜYSE ihraç edilmez: hatalı bir figürü makale kanalına göndermek, eski ama
        # geçerli bir kopyayı orada bırakmaktan kötüdür.
        if not n_fail:
            # Genel depoda bant altyapisi bulunmaz; yoklugu figur kapisini dusurmemeli.
            try:
                import export_to_drive
                export_to_drive.hook("verify_paper_figures.py --grey")
            except ImportError:
                pass
        else:
            print("[export_to_drive] figur kapisi DUSTU -> ihrac edilmedi.")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
