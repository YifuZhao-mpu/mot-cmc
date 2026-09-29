"""
Build the Springer `sn-jnl` submission from the Markdown manuscript.

Markdown is the single source of truth: every number lives in `manuscript.md`,
which is itself checked against `04_experiments/`. This script converts the body
through pandoc, splices it into the sn-jnl preamble, and places the figures.
Anything this script cannot convert mechanically is listed at the end so it can
be fixed in the Markdown rather than patched in the .tex.

    python build_latex.py && tectonic -X compile 02_paper/latex/manuscript.tex
"""
from __future__ import annotations

import os
import re
import subprocess
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from rac.paths import p  # noqa: E402

from rac.paths import ROOT as _R
ROOT = str(_R)
MD = f"{ROOT}/02_paper/manuscript.md"
TEX_DIR = f"{ROOT}/02_paper/latex"
FIGS = f"{ROOT}/05_figures"

# figure placement: (anchor that must already be in the body, file, caption, label)
# Figures, in the order the text first cites them -- which is what the numbering
# follows, and which is not the order they were produced in: the signal-selection
# figure is cited in 4.4, before any other.
FIGURES = [
    ("F8", "F8_signal_selection",
     "Held-out AUC by reliability-signal subset size on real MOT17 data.", "fig:signals"),
    ("F1", "F1_value_axis",
     "MOT17 validation-half. Left: HOTA across the compensation-value axis, with and "
     "without the appearance channel. Right: identity switches. The oracle warp is worse "
     "than the deployable estimator on identity switches in both configurations.", "fig:axis"),
    ("F2", "F2_reliability",
     "Compensation-reliability distributions across the three image benchmarks.", "fig:reliability"),
    ("F3", "F3_spread_vs_depth",
     "KITTI: within-frame residual spread after the best possible \\emph{global} correction, "
     "against the frame's depth ratio (left) and as a function of threshold (right).", "fig:spread"),
    ("F4", "F4_warp_family",
     "Left: the fraction of KITTI moving frames whose targets need corrections differing by more "
     "than the threshold, for four global warps fitted to the static scene. Right: the same warps' "
     "median within-frame residual spread against the pedestrian HOTA they produce. A global "
     "homography with access to depth removes most of the spread; the deployed estimator has the "
     "most spread of the four.", "fig:family"),
    ("F5", "F5_forest",
     "Percentile bootstrap 95\\% confidence intervals over the 21 KITTI sequences, "
     "20{,}000 resamples, weighted by ground-truth detections.", "fig:forest"),
    ("F6", "F6_mechanism",
     "KITTI pedestrians: identity switches avoided by exposure quartile. All of the improvement "
     "is in the top quartile.", "fig:mechanism"),
    ("F7", "F7_depth_noise",
     "Tolerance of the pedestrian gain to depth error, with the real monocular model marked.",
     "fig:depth"),
]

# Author block. `\author*` marks the corresponding author in sn-jnl; ORCIDs use
# the class's own \orcid macro. Order follows the author-supplied list.
_A = [
    ("Yifu",     "Zhao", 1, "0009-0004-2363-9269", "p2523269@mpu.edu.mo", False),
    ("Xiaofan",  "Zou",  2, "0009-0005-5995-3150", "xiaofanz@shu.edu.cn",  False),
    ("Yanxiao",  "Li",   1, "0009-0008-3389-1619", "p2525981@mpu.edu.mo",  False),
    ("Junhao",   "Wei",  1, "0009-0006-0553-2032", "p2312195@mpu.edu.mo",  False),
    ("Sio-Kei",  "Im",   3, "0000-0002-5599-4300", "marcusim@mpu.edu.mo",  False),
    ("Yapeng",   "Wang", 1, "0000-0002-1085-5091", "yapengwang@mpu.edu.mo", True),
    ("Xu",       "Yang", 1, "0000-0002-7037-3609", "xuyang@mpu.edu.mo",    False),
]
AUTHORS = "\n".join(
    f"\\author{'*' if corr else ''}[{inst}]{{\\fnm{{{fn}}}\\sur{{{sn}}}"
    f"\\orcid{{https://orcid.org/{oid}}}}}\\email{{{mail}}}"
    for fn, sn, inst, oid, mail, corr in _A)
AFFILS = "\n".join([
    r"\affil*[1]{\orgdiv{Faculty of Applied Sciences}, \orgname{Macao Polytechnic "
    r"University}, \city{Macao}, \postcode{999078}, \country{China}}",
    r"\affil[2]{\orgdiv{School of Mechanical and Electrical Engineering and "
    r"Automation}, \orgname{Shanghai University}, \city{Shanghai}, "
    r"\postcode{200444}, \country{China}}",
    r"\affil[3]{\orgname{Macao Polytechnic University}, \city{Macao}, "
    r"\postcode{999078}, \country{China}}",
])


PREAMBLE = r"""\documentclass[sn-basic,iicol]{sn-jnl}
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{booktabs}
\usepackage{algorithm}
\usepackage{algorithmicx}
\usepackage[T1]{fontenc}
\usepackage{longtable}
\usepackage{array}
% Float placement. With LaTeX's defaults (topnumber 2, totalnumber 3,
% topfraction 0.7) and 28 full-width table floats competing for page tops, every
% one of the eight figures was deferred to the last two pages of the paper.
\setcounter{topnumber}{3}
\setcounter{bottomnumber}{2}
\setcounter{totalnumber}{5}
\setcounter{dbltopnumber}{3}
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.6}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.7}
\renewcommand{\dbltopfraction}{0.9}
\renewcommand{\dblfloatpagefraction}{0.7}
% verbatim in a two-column layout has one column to live in; the default
% \small is too wide for a 58-character line and ran 242 pt past the column.
\makeatletter\def\verbatim@font{\ttfamily\scriptsize}\makeatother
\usepackage{calc}
\usepackage{listings}
% T1/Latin Modern silently drops Greek and several maths symbols under XeTeX,
% which matters here because the reliability signals are named by Greek letters.
\usepackage{newunicodechar}
\newunicodechar{α}{\ensuremath{\alpha}}
\newunicodechar{ε}{\ensuremath{\varepsilon}}
\newunicodechar{θ}{\ensuremath{\theta}}
\newunicodechar{ρ}{\ensuremath{\rho}}
\newunicodechar{φ}{\ensuremath{\varphi}}
\newunicodechar{σ}{\ensuremath{\sigma}}
\newunicodechar{τ}{\ensuremath{\tau}}
\newunicodechar{κ}{\ensuremath{\kappa}}
\newunicodechar{Δ}{\ensuremath{\Delta}}
\newunicodechar{−}{\ensuremath{-}}
\newunicodechar{×}{\ensuremath{\times}}
\newunicodechar{±}{\ensuremath{\pm}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{→}{\ensuremath{\rightarrow}}
\newunicodechar{⟺}{\ensuremath{\Longleftrightarrow}}
\newunicodechar{⁻}{\ensuremath{^{-}}}
\newunicodechar{¹}{\ensuremath{^{1}}}
\newunicodechar{·}{\ensuremath{\cdot}}
\newunicodechar{§}{\S}
\newunicodechar{…}{\dots}
\lstset{basicstyle=\ttfamily\scriptsize,breaklines=true,frame=none,columns=fullflexible}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
% sn-jnl loads breakurl, which emits dvips PostScript specials and breaks under
% XeTeX/tectonic. Neutralise it; URLs still typeset, they just do not line-break.
\makeatletter
\providecommand\headerps@out[1]{}
\let\headerps@out\@gobble
% breakurl also replaces \url with a dvips-only implementation (\pdf@box);
% hyperref's \nolinkurl typesets the same text and works under XeTeX.
\AtBeginDocument{\let\url\nolinkurl}
\makeatother
% sn-jnl's \orcidlogo hard-codes Orcidlogo.eps, which XeTeX cannot read.
% Point it at the PDF shipped alongside; the mark renders identically.
\makeatletter
\def\orcidlogo{\raisebox{-0.5pt}{\includegraphics[height=7.5pt]{Orcidlogo-eps-converted-to.pdf}}}
\makeatother
\theoremstyle{thmstyleone}
\newtheorem{theorem}{Theorem}
"""


def pandoc_inline(md: str) -> str:
    """Convert one line of Markdown to LaTeX, stripped of the enclosing paragraph."""
    return pandoc(md).strip()


def _balanced(tex: str, i: int) -> tuple[str, int]:
    """Read the brace group starting at tex[i] == '{'; return (contents, index after)."""
    assert tex[i] == "{"
    d, j = 0, i
    while j < len(tex):
        if tex[j] == "{":
            d += 1
        elif tex[j] == "}":
            d -= 1
            if d == 0:
                return tex[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced brace")


CAPTION_PARA = re.compile(r"\n\\textbf\{Table (\d+)\}\s*(.*?)\n\s*\n", re.S)


PT_PER_CHAR = 4.5   # \footnotesize, calibrated from the compiler's overfull reports
TABCOLSEP_PT = 4.0  # tightened from the 6 pt default for these data tables
COL_PT = 230.0      # one column, with a little margin
FULL_PT = 480.0     # both columns, with a little margin


def _col_chars(inner: str, ncol: int) -> list[int]:
    """Widest plain-text cell in each column, in characters."""
    w = [0] * ncol
    for ln in inner.split("\n"):
        if "&" not in ln:
            continue
        # the header row begins with \toprule and the body rows with nothing;
        # skipping every line that starts with a control sequence would skip the
        # header, which is usually the widest row in the table.
        ln = re.sub(r"^\s*\\(?:top|mid|bottom)rule\s*", "", ln)
        cells = re.sub(r"\\\\\s*$", "", ln).split("&")
        for i, c in enumerate(cells[:ncol]):
            plain = re.sub(r"\\[a-zA-Z]+\s?|[{}$]", "", c).strip()
            w[i] = max(w[i], len(plain))
    return w


def _fit(inner: str, ncol: int) -> tuple[str, str]:
    """Choose the float environment and column specification for a table.

    Returns (environment, column spec). A table that fits one column stays in one;
    one that fits the full width spans both; one that fits neither spans both and
    gives its widest column the leftover space as a wrapping p-column, so the text
    breaks instead of the page.
    """
    w = _col_chars(inner, ncol)
    # \tabcolsep is inserted on both sides of every column and is not free: at
    # seven columns it is worth more than eighty points, which is a third of a
    # column. Ignoring it is what put a 37-character table past its column by 120.
    total = sum(w) * PT_PER_CHAR + 2 * TABCOLSEP_PT * ncol
    if total <= COL_PT:
        return "table", "@{}" + "l" * ncol + "@{}"
    if total <= FULL_PT:
        return "table*", "@{}" + "l" * ncol + "@{}"
    j = max(range(ncol), key=lambda i: w[i])
    # what is left for the wrapping column once the other columns and every
    # column separator have taken their share
    others = (sum(w) - w[j]) * PT_PER_CHAR + 2 * TABCOLSEP_PT * ncol
    cols = ["l"] * ncol
    cols[j] = (r">{\raggedright\arraybackslash}p{\dimexpr 0.98\textwidth - "
               rf"{others:.0f}pt\relax}}")
    return "table*", "@{}" + "".join(cols) + "@{}"


def _aspect(pdf: str) -> float:
    """Width over height of a PDF figure, from its MediaBox."""
    try:
        m = re.findall(rb"/MediaBox\s*\[([^]]*)\]", open(pdf, "rb").read())
        x0, y0, x1, y1 = (float(v) for v in m[0].split())
        return (x1 - x0) / (y1 - y0)
    except Exception:
        return 1.0


def place_figures(body: str, blocks: list[str]) -> str:
    """Put each figure float beside the paragraph that discusses it.

    The floats used to be concatenated after the whole body, so LaTeX had nowhere
    to put them but the end: all eight landed on the last three pages of a
    thirty-three page paper, twenty-odd pages after the text that refers to them.
    Each figure is mentioned once, as "Figure n"; the float is inserted after the
    paragraph containing that mention, and LaTeX floats it to the top of that page
    or the next. A figure nothing mentions stays at the end, where it is visible.
    """
    points = []
    for i, blk in enumerate(blocks, start=1):
        m = re.search(rf"\bFigure[~ ]{i}\b", body)
        if m is None:
            points.append((len(body), blk))
            continue
        end = body.find("\n\n", m.end())
        points.append((len(body) if end < 0 else end, blk))
    out = body
    # last first, so that earlier insertion points keep their offsets
    for pos, blk in sorted(points, key=lambda t: -t[0]):
        out = out[:pos] + "\n\n" + blk + out[pos:]
    return out


def detable(tex: str) -> str:
    """sn-jnl in two-column mode cannot use longtable; convert to table* floats.

    pandoc emits longtable for every pipe table. The repeated-header machinery
    (\\endfirsthead / \\endhead / \\endlastfoot) is dropped, pandoc's fixed-width
    \\real{} column spec is replaced by plain columns, and the bold "**Table n**"
    paragraph that preceded the table in Markdown becomes its caption.
    """
    out, pos = [], 0
    OPEN = "\\begin{longtable}[]"
    while True:
        i = tex.find(OPEN, pos)
        if i < 0:
            out.append(tex[pos:])
            break
        out.append(tex[pos:i])
        spec, j = _balanced(tex, i + len(OPEN))
        k = tex.index("\\end{longtable}", j)
        inner, pos = tex[j:k], k + len("\\end{longtable}")

        # the caption is the "**Table N** ..." paragraph immediately before the
        # table in the Markdown; unnumbered tables simply have none
        cap, num = "", None
        head = "".join(out)
        m2 = None
        for m2 in CAPTION_PARA.finditer(head):
            pass
        if m2 is not None and len(head) - m2.end() < 400:
            num, cap = m2.group(1), " ".join(m2.group(2).split())
            head = head[:m2.start()] + "\n\n" + head[m2.end():]
            out = [head]

        # column count from the header row: pandoc's spec uses one >{...} per
        # column, but a cell containing braces can perturb that count
        hdr = next((ln for ln in inner.split("\n") if "&" in ln), "")
        ncol = max(spec.count(">{"), hdr.count("&") + 1, 2)
        for junk in (r"\\endfirsthead", r"\\endhead", r"\\endlastfoot", r"\\endfoot"):
            inner = re.sub(junk, "", inner)
        inner = re.sub(r"\\noalign\{\}", "", inner)
        # pandoc wraps every header cell in a minipage of \linewidth. Inside a
        # tabular, \linewidth is the width of the enclosing column or page, not of
        # the cell, so an n-column header is set n times too wide -- up to 3,271 pt
        # past a 240 pt column before this was removed. The cells are short labels;
        # they want to be plain text.
        inner = re.sub(r"\\begin\{minipage\}\[[a-z]\]\{[^}]*\}(?:\\raggedright|\\raggedleft|\\centering)?\s*",
                       "", inner)
        inner = re.sub(r"\s*\\end\{minipage\}", "", inner)
        # pandoc repeats the header block for \endfirsthead and \endhead; keep one
        parts = inner.split("\\midrule")
        if len(parts) > 2:
            inner = parts[0] + "\\midrule" + parts[-1]
        inner = re.sub(r"\n{3,}", "\n\n", inner).strip()
        # How wide a table spans is decided by its CONTENT, not its column count.
        # Keying on the column count put every table with fewer than six columns
        # into a single column, and all 21 of them ran past it -- the widest by
        # 469 pt. Calibrated against the compiler's own overfull reports, a
        # character at \footnotesize is about 4.5 pt, a column about 240 pt and the
        # full width about 500 pt.
        env, spec = _fit(inner, ncol)
        out.append(f"\\begin{{{env}}}[t]\n\\centering\n"
                   + (f"\\caption{{{cap}}}\\label{{tab:{num}}}\n" if cap else "")
                   + "\\footnotesize\n\\setlength{\\tabcolsep}{4pt}\n"
                   + "\\begin{tabular}{" + spec + "}\n"
                   + inner + f"\n\\end{{tabular}}\n\\end{{{env}}}\n")
    return "".join(out)


def md_body(text: str) -> tuple[str, str, str]:
    """Split the Markdown into (abstract, body, references)."""
    a0 = text.index("## Abstract")
    a1 = text.index("## 1 Introduction")
    r0 = text.index("## References")
    abstract = text[a0:a1]
    abstract = abstract.split("**Keywords**")[0].replace("## Abstract", "").strip()
    keywords = re.search(r"\*\*Keywords\*\*\s*(.+)", text[a0:a1])
    return abstract, text[a1:r0], (keywords.group(1).strip() if keywords else "")


HRULE = re.compile(r"^---\s*$", re.M)


def pandoc(md: str) -> str:
    # pandoc 3.x mis-parses pipe tables that follow a thematic break: with the
    # "---" separators present only 6 of 22 tables survive, without them all 22
    # do. They are decoration in the Markdown and carry nothing into LaTeX.
    md = HRULE.sub("", md)
    # headings carry their own numbers for the §-style cross-references used in
    # the Markdown; LaTeX numbers them itself, so strip ours to avoid "3.3 3.3"
    md = re.sub(r"^(#{2,4})\s+\d+(?:\.\d+)*\s+", r"\1 ", md, flags=re.M)
    return subprocess.run(
        ["pandoc", "-f", "markdown+pipe_tables+tex_math_dollars-yaml_metadata_block", "-t", "latex",
         "--wrap=preserve", "--top-level-division=section", "--shift-heading-level-by=-1",
         "--syntax-highlighting=none"],
        input=md, capture_output=True, text=True, check=True).stdout


def main() -> None:
    text = open(MD).read()
    abstract, body, keywords = md_body(text)
    refs_md = text[text.index("## References"):].replace("## References", "").strip()

    body_tex = detable(pandoc(body))
    abs_tex = pandoc(abstract).strip()

    # figures: each float goes next to the paragraph that discusses it
    figs = []
    for _, f, cap, lab in FIGURES:
        # A panel plot wider than it is tall is illegible at 240 pt. Anything at
        # or past 1.8:1 spans both columns; the rest stay in one.
        env = "figure*" if _aspect(f"{FIGS}/{f}.pdf") >= 1.8 else "figure"
        where = "[tp]" if env == "figure*" else "[tbp]"
        figs.append(
            f"\\begin{{{env}}}{where}\n\\centering\n"
            f"\\includegraphics[width=\\linewidth]{{figs/{f}.pdf}}\n"
            f"\\caption{{{cap}}}\\label{{{lab}}}\n\\end{{{env}}}\n")

    # references as a manual thebibliography (author-year, already formatted)
    items = [r.strip() for r in refs_md.split("\n\n") if r.strip()]
    bib = ["\\begin{thebibliography}{99}"]
    for i, r in enumerate(items, 1):
        r = re.sub(r"\*(.+?)\*", r"\\emph{\1}", r)
        r = r.replace("&", "\\&").replace("_", "\\_")
        r = re.sub(r"https://doi\.org/(\S+)", r"\\url{https://doi.org/\1}", r)
        # natbib runs in author-year mode under sn-jnl and rejects a bare
        # \bibitem, so each entry carries its own (Author, Year) label
        lab = re.match(r"([^(]+?)\s*\((\d{4})\)", r)
        who = lab.group(1).rstrip(",. ") if lab else f"Ref{i}"
        who = who.split(",")[0] + (" et~al." if who.count(",") > 2 else "")
        yr = lab.group(2) if lab else "n.d."
        bib.append(f"\\bibitem[{who}({yr})]{{ref{i}}} {r}")
    bib.append("\\end{thebibliography}")

    out = "\n".join([
        PREAMBLE,
        "\\begin{document}",
        "\\title[Camera-Motion Compensation Is Not the Bottleneck]{Camera-Motion "
        "Compensation Is Not the Bottleneck: A Measurement Study of Shared Warps "
        "in Tracking-by-Detection}",
        AUTHORS,
        AFFILS,
        "\\abstract{" + abs_tex + "}",
        "\\keywords{" + keywords.replace(" · ", ", ") + "}",
        "\\maketitle",
        place_figures(body_tex, figs),
        "\n".join(bib),
        "\\end{document}",
    ])

    os.makedirs(f"{TEX_DIR}/figs", exist_ok=True)
    for _, f, _, _ in FIGURES:
        src = f"{FIGS}/{f}.pdf"
        if os.path.exists(src):
            subprocess.run(["cp", src, f"{TEX_DIR}/figs/{f}.pdf"], check=True)
    open(f"{TEX_DIR}/manuscript.tex", "w").write(out)

    print(f"-> {TEX_DIR}/manuscript.tex  ({len(out.splitlines())} lines, "
          f"{len(items)} references, {len(FIGURES)} figures)")
    leftovers = re.findall(r"^\s*(?:\\emph\{)?§", body_tex, flags=re.M)
    if leftovers:
        print(f"note: {len(leftovers)} section-sign cross-references kept as literal text")


if __name__ == "__main__":
    main()
