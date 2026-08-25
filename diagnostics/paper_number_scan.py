"""Makale kaynagindan SAYI ENVANTERI — number_ledger ve check_numbers'in ORTAK tarayicisi.

NEDEN AYRI DOSYA. Defteri kuran betik ile defteri denetleyen betik ayni tarayiciyi kullanmak
ZORUNDA: farkli tarayicilar kullanirlarsa "deftere kayitsiz sayi" kontrolu anlamsizlasir --
denetci, defterin gormedigi bir jetonu gorup ihlal sayar ya da tersi. Tek tarayici, iki tuketici.

NE YAPAR. LaTeX'i ayristirmaya calismaz; SAYI JETONU cikarir ve her jetona kararli bir kimlik
verir. Kimlik satir numarasina DEGIL, satir etiketine + satir icindeki jeton sirasina baglidir:
makale duzenlendiginde satirlar kayar, etiketler kaymaz.

YERLESIM JETONLARI ATILIR ve sayilir (`dropped`): `0.95\\linewidth`, `6pt`, `\\multicolumn{5}`,
`\\cmidrule(lr){2-3}`, `p{0.075\\textwidth}`, float yerlesimi `[tp]`, `\\setstretch{1}` ... Bu
liste BEYANDIR (`LAYOUT_PATTERNS`): fazla eleme gercek bir sayiyi gizler, o yuzden atilan her
jeton gerekce siniflariyla birlikte raporlanir ve artefakta yazilir.

Kullanim (dogrudan): python diagnostics/paper_number_scan.py --paper-root <yol> [--file tab_x]
"""
import argparse
import hashlib
from collections import defaultdict
import re
import sys
from pathlib import Path

# --- kapsamdaki dosyalar. supplementary yalniz S8-S11 bloklariyla girer (bkz. SUPP_BLOCKS).
TABLE_FILES = ["tables/tab_capacity.tex", "tables/tab_collapse.tex",
               "tables/tab_dose_response.tex", "tables/tab_efficiency.tex",
               "tables/tab_holm.tex", "tables/tab_human.tex",
               "tables/tab_mechanisms.tex", "tables/tab_pooled.tex",
               "tables/tab_selection.tex", "tables/tab_selection_audit.tex",
               # 22 Agu 2026 (defter final2): S12 artik URETILMIS dosya (paper_tables.py
               # basar, supplementary \input ile alir) -- blok olarak degil dosya olarak
               # taranir. KEY_COLS=3: teacher/mechanism/cw etiket sutunlari.
               "tables/tab_app_paired_sd.tex"]

# S8-S11: supplementary.tex icinde YERINDE yazili dort tablo. Blok, `\label{tab:...}`'dan
# geriye dogru `\begin{table` ve ileriye dogru `\end{table` aranarak BULUNUR -- satir araligi
# elle yazilmaz, cunku makale duzenlenince kayar.
# FIGUR ALTYAZILARI (21 Agu 2026, jeton final). Simdilik tek dosya: fig_perclass'in
# altyazisi bir OLCUM iddiasi tasiyor ("signal-to-noise ... at least 10.5") ve F5 bulgusu
# tam orada cikti. Diger figur altyazilari sayi tasimadikca kapsama alinmaz.
FIG_FILES = ["figures/fig_perclass.tex"]

SUPP_BLOCKS = ["tab:app_sd", "tab:app_mde", "tab:app_seeds", "tab:app_predecl",
               # S2 (18 Agu 2026, N16): headroom hukmu supplementary'ye islendi, artik
               # baglanabilir. Uc tablo da `\begin{table}[H]` icinde, blok bulucu aynen calisir.
               "tab:app_argmin", "tab:app_tstar", "tab:app_jsd"]

# S1-S3 DUZYAZISI (18 Agu 2026, N16). Tablolar blok olarak taraniyordu ama bolum METNI hic
# taranmiyordu -- oysa 15 Agustos'taki celiskiyi ureten sayilarin (headroom noktasi ve GA'si)
# tamami S2 duzyazisinda. Bolum, `\section{...}` satirindan bir SONRAKI `\section` satirina
# kadar; tablo/figur ortamlarinin ICI DUSULUR, yoksa ayni jeton iki kez sayilir.
# DIKKAT: bu capalar SUPP_BLOCKS'a KONULAMAZ. `find_block` bolum etiketini gorunce geriye dogru
# `\begin{table` arar, bulamazsa 0'a duser ve sessizce onsozden itibaren her seyi tarar --
# hata vermez, YANLIS tarar. O yuzden ayri bir bulucu.
SUPP_SECTIONS = ["app:specs", "app:robust", "app:tables"]
SUPP_FILE = "supplementary.tex"

# --- ANA GOVDE DUZYAZISI (20 Agu 2026, N19). Kapsam ERTELENMISTI ve gerekcesi yaziliydi:
# "hareket eden hedefi baglamak curuk bag uretir". Bastan sona okuma 20 Agu'da bitti ve duzyazi
# sabitlendi; erteleme sartinin kendisi ortadan kalkti, kapsam aciliyor.
# Liste GLOB DEGIL, BEYAN: `sections/*.tex` desenine guvenmek, yeni bir dosya eklendiginde
# kapsamin SESSIZCE degismesi demek olurdu. Yeni bolum yazilirsa adi buraya yazilir.
# Her dosya BUTUNUYLE taranir; icindeki table/figure ortamlarinin satirlari dusulur (govdede
# yerinde yazilmis figur/tablo varsa iki kez sayilmasin diye) -- SUPP_SECTIONS ile ayni kural.
SECTION_FILES = ["sections/01_introduction.tex", "sections/02_related_work.tex",
                 "sections/03_methodology.tex", "sections/04_experiments.tex",
                 "sections/05_results_discussion.tex", "sections/06_conclusion.tex"]

# Ozet: manset sayilar. Blok `\begin{abstract}` .. `\end{abstract}`.
ABSTRACT_FILE = "main_elsarticle.tex"

# ANAHTAR SUTUN SAYISI (beyan). Bir tablonun bastaki kac sutunu ANAHTARdir -- yani deger degil
# satir kimligi. Varsayilan 1. `app_sd`/`app_mde` ucer anahtar sutunla yaziliyor
# (checkpoint | teacher | cw) ve bunlarin ikisi YAPISKANDIR: satir bos gecilirse ustteki gecerli.
# Bu sayilar LaTeX'in kendi yapisindan okunamaz; tablo tasarimidir, o yuzden burada beyan edilir.
KEY_COLS = {"app_sd": 3, "app_mde": 3, "app_predecl": 1, "tab_app_paired_sd": 3,
            "tab_holm": 2, "tab_selection_audit": 2}
DEFAULT_KEY_COLS = 1

# Bolum basligi: `&` icermeyen, `\multicolumn{n}{...}{\emph{...}}` bicimli satir. Bolum indisi
# jetonun kimliginin PARCASIDIR, cunku ayni satir etiketi ("1.00") uc ayri blokta geciyor
# (`tab_dose_response`) -- bolum olmadan kimlikler cakisirdi.
SECTION = re.compile(r"\\multicolumn\{\d+\}\{(?:[^{}]|\{[^{}]*\})*\}\{[^\n]*\\emph\{")

LAYOUT_PATTERNS = [
    # (ad, desen) -- desen TAMAMEN silinir. Sira onemli: en ozelden genele.
    ("float_placement", r"\\begin\{(?:table|figure|table\*|figure\*)\}\s*\[[^\]]*\]"),
    ("tabular_colspec", r"\\begin\{tabular\}\s*(?:\[[^\]]*\])?\{[^\n]*"),
    ("multicolumn_head", r"\\multicolumn\{\d+\}\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"),
    ("cmidrule", r"\\cmidrule(?:\([a-z]*\))?\{[\d-]+\}"),
    ("setlength", r"\\setlength\{[^{}]*\}\{[^{}]*\}"),
    ("setstretch", r"\\setstretch\{[^{}]*\}"),
    ("colspec_p", r">?\{[^{}]*\\arraybackslash[^{}]*\}|p\{[^{}]*\}"),
    ("colspec_star", r"\*\{\d+\}"),
    ("label_ref", r"\\(?:label|ref|eqref|cite|autoref|input|include)\{[^{}]*\}"),
    ("dimension", r"[-+]?\d*\.?\d+\s*(?:pt|em|ex|bp|cm|mm|in)\b"),
    ("dimension_rel", r"[-+]?\d*\.?\d+\s*\\(?:textwidth|linewidth|columnwidth|baselineskip)"),
    ("counter", r"\\arabic\{[^{}]*\}|\\thetable"),
    ("spacing", r"\\(?:hspace|vspace|addvspace)\*?\{[^{}]*\}"),
]

# Isaret, bir basamaktan HEMEN SONRA gelirse isaret degil cikarma islemidir: `90.2760-89.7545`
# iki jetondur, biri negatif degil. (`tab_selection`in dipnotu tam bu bicimde yaziyor.)
NUM = re.compile(r"(?<![\d.])[-+]?\d+(?:\.\d+)?")
COMMENT = re.compile(r"(?<!\\)%.*$")


# BINLIK AYRACI (20 Agu 2026, N19). LaTeX'te binlik ayraci `$15{,}339$` diye yazilir; jeton
# ayiklayici `{,}`yi gorunce sayiyi IKIYE boluyordu ("15" ve "339"). Govde duzyazisi kapsama
# girince bu tek bir yerde on jeton uretti ve hepsi §4'un veri kumesi buyuklukleriydi -- yani
# TAM DA bu turda `split_identity`ye baglanabilir hale gelen sayilar, tarayici yuzunden
# baglanamiyordu. Ayrac SAYININ PARCASI; jetonlastirmadan once kaldiriliyor.
THOUSANDS = re.compile(r"(?<=\d)\{,\}(?=\d)")

# ISARET SUSU (20 Agu 2026, N19b). Ayni sinif: `$\Delta\mathrm{ECE}{=}{-}0.0041$` yaziminda
# `{-}` bir DIZGI susudur (LaTeX'te eksiyi ikili degil tekli isaret olarak dizmek icin), ama
# jeton ayiklayici suslu parantezi bosluga cevirince sayi ISARETINI KAYBEDIYORDU: basili
# deger -0.0041 iken jeton "0.0041" olarak cikiyor ve alanla (negatif) asla eslesmiyordu.
# Makalede tek gecisi var; yine de kalip olarak duzeltiliyor cunku bir dahaki yazimda sessiz
# kalirdi. Isaret SAYININ PARCASI.
SIGNBRACE = re.compile(r"\{-\}(?=\d|\.\d)")

# BOS GRUP (22 Agu 2026, defter final3). Basili PDF'te `[--+]` deseni IKI degil TEK isaret
# gorunuyordu: cm-super T1 daktilo fontu bitisik iki tireyi en-tire ligaturune baglar. Duzeltme
# araya BOS GRUP koyuyor -- `[-{}-+]` -- ve basilan karakterler ayni kalirken KAYNAK METIN
# degisiyor. Capa metnin kendisi oldugu icin (satir oneki) bu, deger hic degismeden 10 capayi
# birden dusururdu. Bos grup LaTeX'te HICBIR SEY basmaz; jetonlastirmadan once dusuruluyor,
# boylece defterdeki capalar basili bicime gore sabit kalir ve bundan sonraki her ligatur
# duzeltmesi de kendiliginden kapsanir. Yalniz BOS grup dusurulur: `{-}`/`{,}` (isaret susu,
# binlik ayraci) kendi desenlerine ait ve isaretler DOKUNULMADAN kalir.
EMPTYGROUP = re.compile(r"\{\}")

# ISARET DESENI (22 Agu 2026, defter final3). `tab_mechanisms` her hucrenin yaninda tohum
# basina ECE farkinin isaret dizisini basiyor (`[++-]`) ve §5 duzyazisi bunlara adiyla atif
# veriyor (`\texttt{+--} ... Stage1's \texttt{---}`). Bunlar SAYI JETONU DEGIL -- rakam
# tasimadiklari icin NUM onlari hic gormez -- ama VERI IDDIASI: her biri artefaktin
# `d_ece_signs` alaninin birebir kopyasi. Bu tura kadar hicbir kapi onlara bakmiyordu; ligatur
# duzeltmesi tam bu desenlere dokununca olculdu ve acik kapatildi (bkz. number_ledger.SIGNS).
# Ayiklayici `\texttt{...}` icinde YALNIZ isaretten olusan (>=2) dizileri alir; kose parantez
# istege bagli (tabloda var, duzyazida yok).
SIGNPAT = re.compile(r"\\texttt\{\[?([-+]{2,})\]?\}")


def strip_layout(line):
    """(temiz_satir, atilan_jetonlar) -- atilanlar sinif adiyla birlikte."""
    dropped = []
    out = EMPTYGROUP.sub("", SIGNBRACE.sub("-", THOUSANDS.sub("", line)))
    for name, pat in LAYOUT_PATTERNS:
        def _rec(m):
            for t in NUM.findall(m.group(0)):
                dropped.append((name, t))
            return " "
        out = re.sub(pat, _rec, out)
    return out, dropped


def row_label(cleaned):
    """Satir etiketi: ilk `&`den onceki metin, LaTeX susu soyulmus."""
    head = cleaned.split("&")[0]
    head = re.sub(r"\\(?:textbf|mathbf|emph|texttt|text|mathrm)\{([^{}]*)\}", r"\1", head)
    head = re.sub(r"\\[A-Za-z]+\*?", " ", head)
    head = head.replace("$", " ").replace("{", " ").replace("}", " ")
    head = re.sub(r"[~\\!,]", " ", head)
    return re.sub(r"\s+", " ", head).strip(" &")


def find_section(lines, anchor):
    """`\\section{...}\\label{<capa>}` -> (ilk_satir, son_satir, atlanacak_satir_kumesi).

    Bolum bir SONRAKI `\\section` satirinda biter (yoksa dosya sonunda). Icindeki her
    `table`/`figure` ortaminin satirlari `skip` kumesine girer: o bloklar SUPP_BLOCKS
    tarafindan ZATEN taraniyor ve iki kez sayilan bir jeton hem toplami hem "kayitsiz"
    sayimini bozardi.
    """
    hit = next((i for i, ln in enumerate(lines) if f"\\label{{{anchor}}}" in ln), None)
    if hit is None:
        return None
    start = next((i for i in range(hit, -1, -1) if lines[i].lstrip().startswith("\\section")),
                 None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].lstrip().startswith("\\section")), len(lines)) - 1
    skip, depth = set(), 0
    for i in range(start, end + 1):
        if re.search(r"\\begin\{(?:table|figure)\*?\}", lines[i]):
            depth += 1
        if depth:
            skip.add(i)
        if re.search(r"\\end\{(?:table|figure)\*?\}", lines[i]):
            depth = max(0, depth - 1)
    return start, end, skip


def env_skip(lines):
    """Dosyanin TAMAMINDA `table`/`figure` ortamlarinin satir kumesi.

    `find_section` ayni mantigi bir BOLUM araligi icin uyguluyor; govde dosyalarinda aralik
    dosyanin kendisi. Ayri fonksiyon, cunku bolum bulucu bir `\\section` capasi bekliyor ve bir
    govde dosyasi birden cok `\\section` tasiyabiliyor.
    """
    skip, depth = set(), 0
    for i, ln in enumerate(lines):
        if re.search(r"\\begin\{(?:table|figure)\*?\}", ln):
            depth += 1
        if depth:
            skip.add(i)
        if re.search(r"\\end\{(?:table|figure)\*?\}", ln):
            depth = max(0, depth - 1)
    return skip


def find_block(lines, anchor):
    """`\\label{anchor}` iceren tablo/figur blogunun (bas, son) satir indisleri (0-tabanli)."""
    hit = next((i for i, ln in enumerate(lines) if f"\\label{{{anchor}}}" in ln), None)
    if hit is None:
        return None
    start = next((i for i in range(hit, -1, -1)
                  if re.search(r"\\begin\{(?:table|figure)\*?\}", lines[i])), 0)
    end = next((i for i in range(hit, len(lines))
                if re.search(r"\\end\{(?:table|figure)\*?\}", lines[i])), len(lines) - 1)
    return start, end


def find_env(lines, name):
    a = next((i for i, ln in enumerate(lines) if f"\\begin{{{name}}}" in ln), None)
    b = next((i for i, ln in enumerate(lines) if f"\\end{{{name}}}" in ln), None)
    return (a, b) if a is not None and b is not None else None


def scan_lines(lines, rel, lo=0, hi=None, unit=None):
    """Jeton listesi: her jeton bir sozluk. `unit` blok adi (S8, abstract, dosya adi ...).

    MANTIKSAL SATIR. `tabular` icinde bir satir `\\` ile biter ama BIRDEN FAZLA fiziksel
    satira yayilabilir (`tab_mechanisms` her satiri uce boluyor, devam satirlari `&` ile
    basliyor). Bu yuzden tabular icinde satirlar `\\`e kadar BIRIKTIRILIR ve tek mantiksal
    satir olarak islenir; disinda (caption) satir satir gidilir.

    SATIR ETIKETI SAYI DEGILDIR. Mantiksal satirda `&` varsa bastaki `KEY_COLS` hucre
    ANAHTARdir: taranmaz, cunku ya metindir (`Stage1`, `VAE9182`) ya hiperparametredir (`0.85`,
    `alpha=0.1`). Anahtar sutunlari YAPISKANDIR: bos gecilirse ustteki satirin degeri gecerlidir
    (`app_sd`/`app_mde` boyle yaziliyor). `&` hic yoksa (caption, dipnot, bolum basligi) satirin
    tamami taranir -- oradaki sayilar gercek olcumlerdir.
    """
    hi = len(lines) - 1 if hi is None else hi
    unit = unit or rel
    nkey = KEY_COLS.get(unit, DEFAULT_KEY_COLS)
    toks, dropped, sections, signs = [], [], [], []
    seen_key = defaultdict(int)          # ayni kimligin kacinci gecisi (bkz. emit icindeki not)
    seen_sign = defaultdict(int)
    carried = [""] * nkey
    sec = -1
    in_tab = False
    buf, buf_line = [], None

    def emit(raw, first_line):
        nonlocal sec
        cleaned, drops = strip_layout(raw)
        for c, t in drops:
            dropped.append({"line": first_line, "class": c, "token": t})
        if SECTION.search(raw):
            sec += 1
            sections.append({"unit": unit, "index": sec, "line": first_line,
                             "text": row_label(cleaned)[:120]})
            lab, body = "§header", cleaned
        elif "&" in cleaned:
            cells = cleaned.split("&")
            for j in range(min(nkey, len(cells))):
                v = row_label(cells[j])
                if v:
                    carried[j] = v
            lab = " ".join(x for x in carried if x)
            body = "&".join(cells[nkey:])
            for t in NUM.findall(" ".join(cells[:nkey])):
                dropped.append({"line": first_line, "class": "row_label", "token": t})
        else:
            lab, body = row_label(cleaned), cleaned
        for k, t in enumerate(NUM.findall(body)):
            # KIMLIK CAKISMASI (20 Agu 2026, N19). Kimlik satir NUMARASINA baglanmaz -- makale
            # duzenlenince numaralar kayar, etiketler kaymaz; bu bilincli bir karar. Ama AYNI
            # etiket iki kez gecebilir: §3'te ayni denklem parcasi (`\;+\; (1-\alpha)\,\tau^2`)
            # 47. ve 119. satirlarda birebir tekrar ediyor ve iki jeton ayni kimligi aliyordu.
            # Sonuc sessizdi ama gercekti: jeton muhasebesi (bound+derived+exempt+unbound)
            # 1677 yerine 1675 topluyordu ve o rowa yazilan her beyan IKI jetonu birden
            # sahipleniyordu. Cozum satir numarasi degil, AYNI ETIKETIN KACINCI GECISI oldugu:
            # metin kaysa da tekrar SIRASI kalir.
            base = f"{unit}|s{sec}|{lab}|{k}"
            n = seen_key[base]
            seen_key[base] += 1
            toks.append({"unit": unit, "file": rel, "line": first_line,
                         "section": sec, "row": lab, "idx": k, "printed": t,
                         "occurrence": n,
                         "key": base if n == 0 else f"{base}#{n}"})
        # ISARET DESENLERI ayri listede: sayi jetonu degiller (rakam yok), kimlikleri ayni
        # semayi kullanir (birim | bolum | satir etiketi | satir ici sira).
        for k, t in enumerate(SIGNPAT.findall(body)):
            base = f"sign|{unit}|s{sec}|{lab}|{k}"
            n = seen_sign[base]
            seen_sign[base] += 1
            signs.append({"unit": unit, "file": rel, "line": first_line,
                          "section": sec, "row": lab, "idx": k, "printed": t,
                          "occurrence": n,
                          "key": base if n == 0 else f"{base}#{n}"})

    for i in range(lo, hi + 1):
        raw = COMMENT.sub("", lines[i])
        if not raw.strip():
            continue
        if r"\begin{tabular}" in raw:
            in_tab = True
        if in_tab:
            if buf_line is None:
                buf_line = i + 1
            buf.append(raw)
            if raw.rstrip().endswith(r"\\") or r"\end{tabular}" in raw:
                emit(" ".join(buf), buf_line)
                buf, buf_line = [], None
            if r"\end{tabular}" in raw:
                in_tab = False
        else:
            emit(raw, i + 1)
    if buf:
        emit(" ".join(buf), buf_line)
    return toks, dropped, sections, signs


def scan_paper(paper_root):
    """Kapsamdaki her birimi tara. (jetonlar, atilanlar, dosya_ozetleri)"""
    paper_root = Path(paper_root)
    toks, dropped, files, secs, signs = [], [], {}, [], []

    def read(rel):
        p = paper_root / rel
        if not p.exists():
            raise FileNotFoundError(f"kapsamdaki dosya yok: {p}")
        b = p.read_bytes()
        files[rel] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
        return b.decode("utf-8", "replace").splitlines()

    def take(quad):
        t, d, s, g = quad
        toks.extend(t)
        dropped.extend(d)
        secs.extend(s)
        signs.extend(g)

    for rel in TABLE_FILES:
        lines = read(rel)
        take(scan_lines(lines, rel, unit=Path(rel).stem))

    for rel in FIG_FILES:
        lines = read(rel)
        take(scan_lines(lines, rel, unit=Path(rel).stem))

    lines = read(SUPP_FILE)
    for anchor in SUPP_BLOCKS:
        blk = find_block(lines, anchor)
        if blk is None:
            raise RuntimeError(f"{SUPP_FILE} icinde {anchor} blogu bulunamadi")
        take(scan_lines(lines, SUPP_FILE, blk[0], blk[1], unit=anchor.split(":")[1]))
    for anchor in SUPP_SECTIONS:
        sec = find_section(lines, anchor)
        if sec is None:
            raise RuntimeError(f"{SUPP_FILE} icinde {anchor} bolumu bulunamadi")
        lo, hi, skip = sec
        prose = [("" if i in skip else ln) for i, ln in enumerate(lines)]
        take(scan_lines(prose, SUPP_FILE, lo, hi, unit=anchor.split(":")[1]))

    for rel in SECTION_FILES:
        lines = read(rel)
        skip = env_skip(lines)
        prose = [("" if i in skip else ln) for i, ln in enumerate(lines)]
        take(scan_lines(prose, rel, unit=Path(rel).stem))

    lines = read(ABSTRACT_FILE)
    env = find_env(lines, "abstract")
    if env is None:
        raise RuntimeError("abstract blogu bulunamadi")
    take(scan_lines(lines, ABSTRACT_FILE, env[0], env[1], unit="abstract"))
    return toks, dropped, files, secs, signs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-root", required=True)
    ap.add_argument("--file", default=None, help="yalniz bu birimi bas")
    args, _unknown = ap.parse_known_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    toks, dropped, files, secs, signs = scan_paper(args.paper_root)
    cur = None
    for t in toks:
        if args.file and args.file not in t["unit"]:
            continue
        if t["unit"] != cur:
            cur = t["unit"]
            print(f"\n##### {cur}")
        print(f"  L{t['line']:<4d} s{t['section']} [{t['idx']}] {t['printed']:>10s}   "
              f"row={t['row'][:52]!r}")
    for g in signs:
        if args.file and args.file not in g["unit"]:
            continue
        print(f"  ISARET L{g['line']:<4d} s{g['section']} [{g['idx']}] {g['printed']:>6s}   "
              f"row={g['row'][:52]!r}")
    print(f"\n{len(toks)} jeton · {len(signs)} isaret deseni · {len(dropped)} yerlesim jetonu "
          f"atildi · {len(files)} dosya · {len(secs)} bolum")


if __name__ == "__main__":
    sys.exit(main())
