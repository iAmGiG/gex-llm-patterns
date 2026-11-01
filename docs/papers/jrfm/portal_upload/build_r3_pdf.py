"""Convert the Reviewer 3 point-by-point response Markdown into a LaTeX
document and compile to PDF using pdflatex (MiKTeX).

Why this script exists: the JRFM / MDPI portal accepts the Author's Notes
to Reviewer as either pasted text or uploaded PDF/Word. Reviewer 3's
response is long (~29 KB, many tables and bullet lists), so uploading a
PDF is cleaner than pasting raw text. Pandoc is not installed on this
machine, but pdflatex is, so we hand-roll a small Markdown -> LaTeX
converter tailored to the specific constructs used in the source file:

- Top-level (#) and sub (## / ###) headings
- Blockquotes (lines starting with "> ")
- Bold (**...**) and italics (*...*)
- Inline code (`...`)
- Unordered lists (- / *)
- Ordered lists (1.)
- Simple pipe tables (| ... | ...)
- Horizontal rules (---)

It is not a general-purpose converter; it only handles what
response_R3_pointbypoint.md contains.

Usage:
    python build_r3_pdf.py

Outputs:
    response_R3_pointbypoint.tex (intermediate)
    response_R3_pointbypoint.pdf (upload this to the portal)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_MD = HERE / "response_R3_pointbypoint.md"
OUT_TEX = HERE / "response_R3_pointbypoint.tex"
OUT_PDF = HERE / "response_R3_pointbypoint.pdf"


# ---------- LaTeX escaping and inline formatting ----------

LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Unicode characters that appear in the source and require LaTeX math-mode
# or special-command substitutes under the default T1/pdflatex setup.
UNICODE_MAP = {
    "κ": r"$\kappa$",
    "φ": r"$\varphi$",
    "χ": r"$\chi$",
    "²": r"$^{2}$",
    "³": r"$^{3}$",
    "×": r"$\times$",
    "→": r"$\rightarrow$",
    "≥": r"$\geq$",
    "≤": r"$\leq$",
    "≈": r"$\approx$",
    "≠": r"$\neq$",
    "—": "---",
    "–": "--",
    "…": r"\ldots{}",
    "•": r"\textbullet{}",
    "′": "'",
    "″": "''",
    "‘": "`",
    "’": "'",
    "“": "``",
    "”": "''",
    "∈": r"$\in$",
    "∞": r"$\infty$",
    "±": r"$\pm$",
    "°": r"$^\circ$",
    "μ": r"$\mu$",
    "σ": r"$\sigma$",
    "α": r"$\alpha$",
    "β": r"$\beta$",
    "Δ": r"$\Delta$",
    "Σ": r"$\Sigma$",
    "§": r"\S{}~",
    "−": "-",  # U+2212 unicode minus
    "‐": "-",  # U+2010 unicode hyphen
    "‑": "-",  # U+2011 non-breaking hyphen
    # Superscript digits (U+2070..U+2079 and U+207A..U+207F) -- common in
    # scientific p-values like 10^-48 written as 10⁻⁴⁸
    "⁰": r"$^{0}$",
    "¹": r"$^{1}$",
    "²": r"$^{2}$",
    "³": r"$^{3}$",
    "⁴": r"$^{4}$",
    "⁵": r"$^{5}$",
    "⁶": r"$^{6}$",
    "⁷": r"$^{7}$",
    "⁸": r"$^{8}$",
    "⁹": r"$^{9}$",
    "⁻": r"$^{-}$",
    "⁺": r"$^{+}$",
    # Subscript digits
    "₀": r"$_{0}$",
    "₁": r"$_{1}$",
    "₂": r"$_{2}$",
    "₃": r"$_{3}$",
    "₄": r"$_{4}$",
    "₅": r"$_{5}$",
    "₆": r"$_{6}$",
    "₇": r"$_{7}$",
    "₈": r"$_{8}$",
    "₉": r"$_{9}$",
    " ": "~",  # non-breaking space
}


def escape_latex(s: str) -> str:
    # Escape LaTeX specials FIRST (otherwise Unicode-map replacements like
    # ``$\times$`` would have their backslashes escaped and break).
    out = []
    for ch in s:
        if ch in LATEX_ESCAPES:
            out.append(LATEX_ESCAPES[ch])
        else:
            out.append(ch)
    s = "".join(out)
    # Now substitute Unicode characters into LaTeX commands in-place; the
    # replacements are already valid LaTeX and must not be re-escaped.
    for src, dst in UNICODE_MAP.items():
        s = s.replace(src, dst)
    return s


def apply_inline(s: str) -> str:
    """Apply inline markdown (bold, italic, code) after LaTeX-escaping.

    Order:
      1. protect inline code spans first (they should not be further
         processed)
      2. escape the rest
      3. apply bold and italic markers
      4. splice code spans back in
    """
    # Extract inline code spans
    code_spans = []

    def stash_code(m):
        code_spans.append(m.group(1))
        return f"\x00CODE{len(code_spans) - 1}\x00"

    s = re.sub(r"`([^`]+)`", stash_code, s)

    s = escape_latex(s)

    # Bold: **text** -> \textbf{text}
    s = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", s)
    # Italic: *text* -> \textit{text}
    s = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", s)

    # Restore code spans
    def restore_code(m):
        idx = int(m.group(1))
        return r"\texttt{" + escape_latex(code_spans[idx]) + "}"

    s = re.sub(r"\x00CODE(\d+)\x00", restore_code, s)

    return s


# ---------- Pre-processing: make inline-LaTeX snippets readable ----------


def preprocess_latex_snippets(md: str) -> str:
    """Rewrite inline-LaTeX snippets that appear in the Markdown source into
    plain-text readable forms.

    The response document cites the main manuscript's LaTeX source liberally
    (``\citep{dim2023odtes}``, ``\ref{sec:methodology}``). In a stand-alone
    response PDF without bibliography or label resolution these should read
    as plain prose rather than raw macros.
    """
    # \citep{key} and \citet{key} -> (key)
    md = re.sub(r"\\citep\{([^}]+)\}", r"(\1)", md)
    md = re.sub(r"\\citet\{([^}]+)\}", r"\1", md)
    # \citealp{a,b,c} -> a, b, c
    md = re.sub(r"\\citealp\{([^}]+)\}", r"\1", md)
    # \ref{sec:xxx} -> sec:xxx (plain-text label; reader can find it in manuscript)
    md = re.sub(r"\\ref\{([^}]+)\}", r"\1", md)
    # \S\ref{...} or \S~\ref{...} -> §(...)
    md = re.sub(r"\\S[~\s]*", "§", md)
    # \emph{text} -> *text* so downstream italic handling kicks in
    md = re.sub(r"\\emph\{([^}]+)\}", r"*\1*", md)
    # \textbf{text} -> **text**
    md = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", md)
    # \textit{text} -> *text*
    md = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", md)
    # \texttt{text} -> `text`
    md = re.sub(r"\\texttt\{([^}]+)\}", r"`\1`", md)
    # Remove stray \\ at end of line (line-break markers)
    md = re.sub(r"\\\\\s*$", "", md, flags=re.MULTILINE)
    return md


# ---------- List-continuation folder ----------


def fold_list_continuations(md: str) -> str:
    """Fold multi-line list items into single logical lines.

    In CommonMark, an ordered or unordered list item's prose can span
    multiple physical lines as long as the continuation lines are
    indented past the list marker. Our block converter treats each
    physical line independently, which fragments multi-line items into
    multiple single-item lists. This pre-pass joins continuation lines
    back onto their opening line so the block converter sees one
    item-per-line.
    """
    lines = md.splitlines()
    out: list[str] = []
    in_item = False  # are we inside a list item whose prose continues?
    for line in lines:
        stripped = line.strip()
        is_blank = stripped == ""
        starts_list = bool(re.match(r"^(\s*)([-*+]|\d+\.)\s+", line))
        is_indented_continuation = line.startswith((" ", "\t")) and not is_blank and not starts_list
        if in_item and is_indented_continuation:
            # Append (with a single space) to the previous output line.
            out[-1] = out[-1].rstrip() + " " + stripped
            continue
        if is_blank or starts_list is False:
            in_item = False
        if starts_list:
            in_item = True
        out.append(line)
    return "\n".join(out)


# ---------- Block-level conversion ----------


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_list = False
    list_type: str | None = None  # "itemize" or "enumerate"

    def close_list():
        nonlocal in_list, list_type
        if in_list:
            out.append(f"\\end{{{list_type}}}")
            in_list = False
            list_type = None

    while i < len(lines):
        line = lines[i].rstrip("\n")

        # Horizontal rule
        if re.match(r"^---\s*$", line):
            close_list()
            out.append(r"\bigskip\hrule\bigskip")
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_list()
            level, text = len(m.group(1)), apply_inline(m.group(2))
            sec_cmds = {
                1: r"\section*{%s}",
                2: r"\subsection*{%s}",
                3: r"\subsubsection*{%s}",
                4: r"\paragraph{%s}",
                5: r"\subparagraph{%s}",
                6: r"\paragraph{%s}",
            }
            out.append(sec_cmds[level] % text)
            i += 1
            continue

        # Blockquote
        if line.startswith(">"):
            close_list()
            quote_lines = []
            while i < len(lines) and lines[i].startswith(">"):
                quote_lines.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append(r"\begin{quote}")
            out.append(apply_inline(" ".join(quote_lines)))
            out.append(r"\end{quote}")
            continue

        # Table: contiguous lines starting with |
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|\s*[-:| ]+\|", lines[i + 1]):
            close_list()
            header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # skip separator row
            i += 2
            body_rows = []
            while i < len(lines) and lines[i].startswith("|"):
                row_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                body_rows.append(row_cells)
                i += 1
            ncols = len(header_cells)
            col_spec = "|".join(["l"] * ncols)
            out.append(r"\begin{table}[H]")
            out.append(r"\centering")
            out.append(r"\small")
            out.append(r"\begin{tabular}{|" + col_spec + "|}")
            out.append(r"\hline")
            out.append(" & ".join(r"\textbf{" + apply_inline(c) + "}" for c in header_cells) + r" \\ \hline")
            for row in body_rows:
                # Pad short rows
                row = row + [""] * (ncols - len(row))
                out.append(" & ".join(apply_inline(c) for c in row[:ncols]) + r" \\ \hline")
            out.append(r"\end{tabular}")
            out.append(r"\end{table}")
            continue

        # Ordered list
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if m:
            indent, _n, text = m.groups()
            if not in_list or list_type != "enumerate":
                close_list()
                out.append(r"\begin{enumerate}")
                in_list = True
                list_type = "enumerate"
            out.append(r"\item " + apply_inline(text))
            i += 1
            continue

        # Unordered list
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if m:
            indent, text = m.groups()
            if not in_list or list_type != "itemize":
                close_list()
                out.append(r"\begin{itemize}")
                in_list = True
                list_type = "itemize"
            out.append(r"\item " + apply_inline(text))
            i += 1
            continue

        # Blank line
        if line.strip() == "":
            close_list()
            out.append("")
            i += 1
            continue

        # Regular paragraph line
        close_list()
        out.append(apply_inline(line))
        i += 1

    close_list()
    return "\n".join(out)


# ---------- Preamble and driver ----------

PREAMBLE = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.4cm]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{parskip}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{array}
\usepackage{booktabs}
\usepackage{float}
\usepackage{textcomp}
\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}
\setcounter{secnumdepth}{0}

\title{Response to Reviewer 3 \\ \large JRFM Submission jrfm-4256551}
\author{Christopher Regan \and Ying Xie \\ Kennesaw State University}
\date{24 April 2026}

\begin{document}
\maketitle
"""

POSTAMBLE = r"""
\end{document}
"""


def main() -> int:
    if not SRC_MD.exists():
        print(f"ERROR: {SRC_MD} not found", file=sys.stderr)
        return 1

    md = SRC_MD.read_text(encoding="utf-8")
    md = preprocess_latex_snippets(md)
    md = fold_list_continuations(md)
    body = convert(md)
    tex = PREAMBLE + body + POSTAMBLE
    OUT_TEX.write_text(tex, encoding="utf-8")
    print(f"Wrote {OUT_TEX}")

    # Compile twice for cross-references (not strictly needed here, but safe).
    for pass_num in (1, 2):
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                OUT_TEX.name,
            ],
            cwd=HERE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            print(f"--- pdflatex stderr (pass {pass_num}) ---", file=sys.stderr)
            print(result.stdout[-2000:], file=sys.stderr)
            return 1
    # Clean aux/log after successful compile
    for ext in (".aux", ".log", ".out", ".toc"):
        p = OUT_TEX.with_suffix(ext)
        if p.exists():
            p.unlink()
    print(f"Wrote {OUT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
