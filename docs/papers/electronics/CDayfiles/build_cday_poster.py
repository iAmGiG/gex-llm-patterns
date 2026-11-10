#!/usr/bin/env python
"""Build the C-Day poster of the Electronics extension (gex-llm-patterns #261) from Dr. Xie's template.

The template is the 48 x 36 in KSU poster "ThresholdGatedRL_Poster 2.pptx" that Dr. Xie supplied (another student's
finished poster, so it stays out of the repository: .gitignore lists it; put the file in this folder to rebuild): three columns of
section cards, a results band with four stat callouts, three figures and three native bar charts. This script
keeps every shape, colour and position of the template and replaces only the content: text (run formatting is
copied from the template paragraph named for each new paragraph), the data of the four native charts, the
table, the five pictures and the QR code.

Every number comes from docs/papers/electronics/results/ (stats.yaml, bridge_agreement.csv,
post_publication_2026_summary.csv) or from the manuscript text that cites it (04_02, 04_05 to 04_08, 04_11,
04_12); the Llama 3.1 8B and Qwen3-8B numbers are those of Section 4.12 and results/missing_answer_bounds.csv (D-30,
D-32). The charts show the five labelers of the Llama draft; Qwen3-8B appears in the agreement box and the conclusions.

Run with an environment that has python-pptx, Pillow and qrcode (on this machine the gamma-sieve env; never
install into AutoGex):

    ~/miniconda3/envs/gamma-sieve/bin/python docs/papers/electronics/CDayfiles/build_cday_poster.py

Output: docs/papers/electronics/CDayfiles/Regan_Xie_CDay_Poster.pptx.  Its PDF, Regan_Xie_CDay_Poster.pdf, is a
LibreOffice export (Liberation Sans for Arial, metric-compatible), made on this machine with the Docker image
cregan1/lo-render:1:
    docker run --rm -u $(id -u):$(id -g) -e HOME=/tmp/home -v $PWD/docs/papers/electronics/CDayfiles:/work cregan1/lo-render:1 \
        bash -c "mkdir -p /tmp/home && soffice -env:UserInstallation=file:///tmp/home/lo --headless --convert-to pdf \
        --outdir /work /work/Regan_Xie_CDay_Poster.pptx"
A PDF exported from PowerPoint (File > Export > PDF) keeps the original fonts.
"""
from __future__ import annotations

import re
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import qrcode
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
TEMPLATE = HERE / "ThresholdGatedRL_Poster 2.pptx"
OUTPUT = HERE / "Regan_Xie_CDay_Poster.pptx"
FIGURES = PAPER / "figures" / "output"
REPO_URL = "https://github.com/iAmGiG/gex-llm-patterns"

GOLD, BLACK, GREY_D, GREY_M, GREY_L, RED = "FFC629", "141414", "5A5A5A", "8C8C8C", "C8C8C8", "C2412D"

# --------------------------------------------------------------------------------------------------------------
# Content.  A paragraph is (template paragraph index, text) or (index, text, options); **...** marks bold runs.
# --------------------------------------------------------------------------------------------------------------
TITLE = [(0, "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation:"),
         (1, "A Re-Run on Complete Inputs with a Controlled LLM Re-Test")]
AUTHORS = [(0, "Christopher Regan  ·  Ying Xie"),
           (1, "College of Computing and Software Engineering  ·  Kennesaw State University, Marietta, GA")]

ABSTRACT = [(0, "Temporal obfuscation tests whether a large language model (LLM) **reasons about numbers or recalls "
                "market history**: dates and tickers are removed from 30-day windows of daily dealer gamma exposure "
                "(GEX). Our earlier work reported a persistent regime in **every SPY window of 2024–2025**. "
                "We re-run the test on the complete data, because the published 2024–2025 inputs **lacked the put "
                "leg**. On the complete series the deterministic rule detects **12.0%** of those windows and "
                "gpt-6-luna 12.5%. The model follows the rule in 99.7% of 4,691 windows, dates change 1 of 223 "
                "verdicts, and an open-weights model run locally gives the same rates.")]

INTRO = [(0, "**Dealer gamma exposure (GEX)** sums the gamma of open options, with the dealer side imputed by a "
             "sign convention; a sign that holds for weeks marks a **regime**."),
         (1, "**Obfuscation** removes dates and tickers: the model has only the values and the criteria, not its "
             "memory of the period."),
         (2, "A re-run needs the **same inputs** and a **model that still answers**: o4-mini is retired and the "
             "daily GEX table was rebuilt in 2026, so we recovered the published inputs from the stored batch file.")]

RQS = [[(0, "Which **daily series** were the published inputs, and how do the rule’s labels change on the "
            "**complete series**?")],
       [(0, "Does a current model reproduce the **published answers**, and does its call follow the **numbers**, "
            "not the **dates**?")],
       [(0, "Do the answers hold without **0DTE**, in other years and assets, and with **open-weights models** "
            "run locally?")]]

# template paragraphs of the Materials and Methods box: 0 heading, 1 plain text, 3 bullet
METHODS = [(0, "Data"),
           (1, "Daily net GEX of SPY, QQQ and IWM, 2008–2026, from stored option chains, in six series: the "
               "published inputs, the call leg only, the pre-rebuild archive, the complete series with and without "
               "same-day expiries (0DTE), and an intraday snapshot."),
           (0, "Windows and rule"),
           (3, "30 trading days, stride 1, labeled **Day T−29 … T+0**; no dates, no tickers; 38,592 windows."),
           (3, "**Rule:** ≥ 70% of days of one sign, mean |GEX| ≥ $5B, ≤ 5 sign flips."),
           (0, "Models"),
           (3, "**o4-mini:** the published answers (January 2026), now retired."),
           (3, "**gpt-6-luna:** OpenAI Batch API; all its runs cost USD 10.02."),
           (3, "**gpt-oss-20b, Llama\u00a03.1\u00a08B, Qwen3-8B:** open weights at fixed revisions, vLLM on local A100 GPUs."),
           (0, "Statistics"),
           (1, "Cohen’s κ for agreement; Wilson and quarter-block bootstrap intervals, since the windows overlap. "
               "Every input, prompt and answer is stored.")]

APPROACH_TITLE = "Approach: Same Rule, Same Prompt, Different Inputs"
APPROACH_CAPTION = "Window ending 2024-03-15 in four series (paper Fig. 2)."
RULE_HEADING = [(0, "**The rule**  (each 30-day window)")]
CARDS = [("Mean |GEX| < $5B", "→ Not detected: below the magnitude floor"),
         ("< 70% of one sign  or  > 5 sign flips", "→ Not detected: the sign does not persist"),
         ("All three criteria hold  ✓", "→ Regime detected, positive or negative")]
RULE_NOTE = [(0, "The model gets the 30 values and these criteria only: **no dates, no tickers**.")]
SERIES_HEADING = [(0, "**Same rule, five daily series:** share of the 2024–2025 windows that the rule detects")]
SERIES_NOTE = [(0, "The published 2024–25 inputs carry the **call leg only**, so every day is positive and large."),
               (1, "The **rule** then detects every window."),
               (2, "Both legs: 12.0%. Without 0DTE: 14.7%.")]
# stats.yaml rates, classifier, period 2024-2025: jan2026_phase4a 501/501, call_only 502/502, old_bs 501/501,
# new_full 60/502, new_ex0dte 74/502
SERIES_CHART = (["Published inputs", "Call leg only", "Pre-rebuild archive", "Complete, 0DTE incl.", "Complete, ex-0DTE"],
                [100.0, 100.0, 100.0, 60 / 502 * 100, 74 / 502 * 100],
                [GREY_M, GREY_L, GREY_L, GOLD, GOLD])

CALLOUTS = [("12.0%", "2024–25 windows detected", "published inputs gave 100%"),
            ("99.6%", "o4-mini = gpt-6-luna", "1,412 published windows"),
            ("99.7%", "gpt-6-luna = rule", "4,691 complete windows"),
            ("1 of 223", "verdicts changed by dates", "2024 baseline, gpt-6-luna")]
RESULT_FIGURES = [("fig04_classifier_replay.png",
                   [(0, "**Rule by year:** 100% in 2024–25 on the published inputs, 10.3% and 13.6% on the complete series.")]),
                  ("fig06_bridge_agreement.png",
                   [(0, "**Bridge:** gpt-6-luna gives the o4-mini verdict on 1,407 of 1,412 published windows.")]),
                  ("fig12_threshold_sensitivity.png",
                   [(0, "**Thresholds:** over 45 threshold sets the published inputs stay 70.7–96.0 points higher.")])]
LABELERS_HEADING = [(0, "**Five labelers compared**  (o4-mini is retired, so it has no answers on the complete series)")]
LABELERS = ["Rule", "o4-mini", "gpt-6-luna", "gpt-oss-20b", "Llama 3.1 8B"]
LABELER_COLORS = [GOLD, GREY_M, GREY_L, GREY_L, RED]
# stats.yaml (and the D-30 report for Llama) rates 2024-2025: jan2026_phase4a classifier 501/501, r1_o4mini 486/486,
# bridge_jan 501/501, oss_bridge_jan 501/501, llama_bridge_jan 501/501; new_full classifier 60/502, full_spy 63/502,
# oss_full_spy 62/502, llama_full_spy 502/502; baselines (dated): p3_2024_dated 181/223 and p4_2020_dated 27/223 for
# the rule, o4-mini and gpt-6-luna, oss 183/223 and 27/223, llama 223/223 and 223/223 (04_11, 04_12)
LABELER_CHARTS = [
    ([(0, "Published inputs, 2024–25"), (1, "% of windows detected")],
     [100.0, 100.0, 100.0, 100.0, 100.0], (0, 118)),
    ([(0, "Complete series, 2024–25"), (1, "% of windows detected")],
     [60 / 502 * 100, None, 63 / 502 * 100, 62 / 502 * 100, 100.0], (0, 118)),
    ([(0, "2024 minus 2020 baseline"), (1, "percentage points, prompts with dates")],
     [154 / 223 * 100, 154 / 223 * 100, 154 / 223 * 100, 156 / 223 * 100, 0.0], (0, 86)),
]

SIDE_TITLE = "Does It Hold Elsewhere?"
SIDE_INTRO = [(0, "Share of windows detected on the complete series:")]
# 04_05 (502 windows, 74 and 77), post_publication_2026_summary.csv (ends_in_2026 new_full SPY 22 of 194 for both),
# 04_06 (no window before 2014 detected by the rule or gpt-6-luna; 1,482 windows of new_full end 2008-2013),
# 04_07 (QQQ 0 of 3,878 and IWM 0 of 4,691 for the rule and gpt-6-luna)
SIDE_TABLE = [["Check", "Windows", "Rule", "gpt-6-luna"],
              ["Without 0DTE, 2024–25", "502", "14.7%", "15.3%"],
              ["2026, after publication", "194", "11.3%", "11.3%"],
              ["SPY 2008–2013", "1,482", "0.0%", "0.0%"],
              ["QQQ and IWM", "8,569", "0.0%", "0.0%"]]
SIDE_COL_WIDTHS = [5.0, 2.0, 1.9, 2.5]
SIDE_NOTE = [(0, "Same-day expiries carry **41–46% of |net GEX|** in 2024–26, yet dropping them gives 14.7%, not 100%. "
                 "Before 2014 and for QQQ and IWM **no window reaches $5B**.")]

AGREEMENT_TITLE = "Agreement (Cohen’s κ)"
# detection_by_year.csv scope=all, against the rule on the complete series: oss_full_spy kappa 0.987793,
# qwen_full_spy kappa 0.948367 (4,206 answered of 4,691 windows = 89.7%), llama arms kappa 0.000 (04_12); the o4-mini
# vs gpt-6-luna bridge (99.6%) is the second callout
AGREEMENT = [("κ = 0.988", "gpt-oss-20b vs rule"), ("κ = 0.948", "Qwen3-8B vs rule*"), ("κ = 0.000", "Llama 3.1 8B vs rule")]
AGREEMENT_NOTE = [(0, "*Windows it answered (90%). Bootstrap, rule 2024–25: **12.0% [5.1, 19.6]**")]

CONCLUSIONS = [(0, "**RQ1 ✓** Published 2024–25 inputs: call leg only. Complete series: 12.0%, and no rise after 2023."),
               (1, "**RQ2 ✓** gpt-6-luna matches o4-mini (99.6%) and the rule (99.7%); dates change 1 of 223 verdicts."),
               (2, "**RQ3 ✓** Without 0DTE 14.7%, 2026 11.3%, gpt-oss-20b 12.4%, Qwen3-8B 14.5–35.1%. Llama\u00a03.1\u00a08B: “detected” almost always."),
               (3, "**Next:** thresholds scaled by symbol and price, intraday open interest, more model families.")]
TAKE_HOME = [(0, "**Take-home:** a detection rate is only as sound as its input series; version the data and test a "
                 "contrast, not a level.")]
ACK = [(0, "KSU CCSE for computing resources; Alpha Vantage for options data.")]
CONTACT = [(0, "**Christopher Regan**  cregan1@students.kennesaw.edu"),
           (1, "**Ying Xie**  yxie2@kennesaw.edu"),
           (2, "Code: github.com/iAmGiG/gex-llm-patterns"),
           (3, "Repository: scan the QR code")]
REFS_SZ = {"sz": 1600}  # 17 pt in the template; three two-line references need 16 pt to fit the box
REFERENCES = [(0, "1. Regan C., Xie Y. Validating LLM structural reasoning: detecting persistent market regimes through "
                  "temporal obfuscation. AIAI 2026, IFIP AICT, 127–140.", REFS_SZ),
              (1, "2. Regan C., Xie Y. Inferring latent market forces: evaluating LLM detection of gamma exposure "
                  "patterns via obfuscation testing. LLM-Finance, IEEE BigData 2025; arXiv:2512.17923.", REFS_SZ),
              (2, "3. Regan C., Xie Y. Temporal obfuscation testing for LLM structural reasoning. J. Risk Financial "
                  "Manag. 2026, 19, 382.", REFS_SZ)]


# --------------------------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------------------------
def shape(slide, shape_id: int):
    for sh in slide.shapes:
        if sh.shape_id == shape_id:
            return sh
    raise KeyError(f"no shape with id {shape_id}")


def run_templates(p_el):
    """(plain rPr, bold rPr) of a template paragraph.  A paragraph whose runs are all bold (a heading) keeps plain
    text bold; a paragraph without bold runs gets bold by setting b on a copy of its plain run."""
    rprs = [r.find(qn("a:rPr")) for r in p_el.iter(qn("a:r")) if r.find(qn("a:rPr")) is not None]
    if not rprs:
        raise ValueError("template paragraph without runs")
    normal = next((r for r in rprs if r.get("b") != "1" and r.get("baseline") is None), None)
    bold = next((r for r in rprs if r.get("b") == "1" and r.get("baseline") is None), None)
    if normal is None:
        normal = bold
    if bold is None:
        bold = deepcopy(normal)
        bold.set("b", "1")
    return deepcopy(normal), deepcopy(bold)


def segments(text: str):
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, False) for p in parts if p]


def set_paragraphs(sh, paras) -> None:
    """Replace the paragraphs of a text shape; each new paragraph copies pPr and run styles of a template paragraph."""
    body = sh.text_frame._txBody
    old = body.findall(qn("a:p"))
    styles = [(p.find(qn("a:pPr")),) + run_templates(p) if list(p.iter(qn("a:r"))) else None for p in old]
    for p in old:
        body.remove(p)
    for spec in paras:
        idx, text = spec[0], spec[1]
        opts = spec[2] if len(spec) > 2 else {}
        pPr, normal, bold = styles[idx]
        p = etree.SubElement(body, qn("a:p"))
        if pPr is not None:
            p.append(deepcopy(pPr))
        for seg, is_bold in segments(text):
            r = etree.SubElement(p, qn("a:r"))
            rPr = deepcopy(bold if is_bold else normal)
            if "sz" in opts:
                rPr.set("sz", str(opts["sz"]))
            if "color" in opts:
                clr = rPr.find(".//" + qn("a:srgbClr"))
                if clr is not None:
                    clr.set("val", opts["color"])
            r.append(rPr)
            etree.SubElement(r, qn("a:t")).text = seg


def set_text(sh, text: str) -> None:
    """One paragraph in the style of the template's first run (headings, callouts, labels)."""
    body = sh.text_frame._txBody
    paras = body.findall(qn("a:p"))
    for p in paras[1:]:
        body.remove(p)
    runs = paras[0].findall(qn("a:r"))
    for r in runs[1:]:
        paras[0].remove(r)
    runs[0].find(qn("a:t")).text = text


def replace_picture(slide, old, image: Path, descr: str, box=None) -> None:
    """Put `image` in the place of picture `old`, fitted into box (x, y, w, h in inches; default: old's frame)."""
    w_px, h_px = Image.open(image).size
    bx, by, bw, bh = box or (old.left / 914400, old.top / 914400, old.width / 914400, old.height / 914400)
    scale = min(bw / w_px, bh / h_px)
    w, h = w_px * scale, h_px * scale
    pic = slide.shapes.add_picture(str(image), Inches(bx + (bw - w) / 2), Inches(by + (bh - h) / 2), Inches(w), Inches(h))
    old_ln = old._element.spPr.find(qn("a:ln"))
    if old_ln is not None:
        pic._element.spPr.append(deepcopy(old_ln))
    pic._element.nvPicPr.cNvPr.set("descr", descr)
    pic.name = old.name
    old_rid = old._element.blipFill.find(qn("a:blip")).get(qn("r:embed"))
    old._element.addprevious(pic._element)
    old._element.getparent().remove(old._element)
    slide.part.drop_rel(old_rid)


def set_chart(chart_shape, name, categories, values, colors, axis, number_format="0.0", outline_first=True) -> None:
    """New data for a one-series bar chart of the template, with one colour per bar and fixed value-axis limits."""
    chart = chart_shape.chart
    ser = chart._chartSpace.find(".//" + qn("c:ser"))
    protos = ser.findall(qn("c:dPt"))
    outlined = next((d for d in protos if d.find(".//" + qn("a:ln")) is not None), protos[0])
    plain = next((d for d in protos if d.find(".//" + qn("a:ln")) is None), protos[-1])
    data = CategoryChartData(number_format="General")
    data.categories = categories
    data.add_series(name, values)
    chart.replace_data(data)
    ser = chart._chartSpace.find(".//" + qn("c:ser"))
    for d in ser.findall(qn("c:dPt")):
        ser.remove(d)
    anchor = ser.find(qn("c:invertIfNegative"))
    for i, color in reversed(list(enumerate(colors))):
        d = deepcopy(outlined if (i == 0 and outline_first) else plain)
        d.find(qn("c:idx")).set("val", str(i))
        for ext in d.findall(qn("c:extLst")):
            d.remove(ext)
        d.find(".//" + qn("a:srgbClr")).set("val", color)
        anchor.addnext(d)
    fmt = ser.find(qn("c:dLbls") + "/" + qn("c:numFmt"))
    if fmt is not None:
        fmt.set("formatCode", number_format)
    scaling = chart._chartSpace.find(".//" + qn("c:valAx") + "/" + qn("c:scaling"))
    for tag in ("c:max", "c:min"):
        el = scaling.find(qn(tag))
        if el is not None:
            scaling.remove(el)
    orientation = scaling.find(qn("c:orientation"))
    mx = etree.Element(qn("c:max"))
    mx.set("val", str(axis[1]))
    mn = etree.Element(qn("c:min"))
    mn.set("val", str(axis[0]))
    orientation.addnext(mx)
    mx.addnext(mn)


def set_table(table_shape, rows, col_widths) -> None:
    tbl = table_shape.table
    for j, w in enumerate(col_widths):
        tbl.columns[j].width = Inches(w)
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            cell = tbl.cell(i, j)
            p = cell._tc.find(qn("a:txBody")).find(qn("a:p"))
            runs = p.findall(qn("a:r"))
            for r in runs[1:]:
                p.remove(r)
            runs[0].find(qn("a:t")).text = value
            if j == 0:
                p.find(qn("a:pPr")).set("algn", "l")


def nudge(slide, ids, dy: float = 0.0, dh: float = 0.0) -> None:
    """Move shapes (ids, or names for pictures that replace_picture re-created) by dy and grow them by dh inches."""
    for key in ids:
        sh = next(x for x in slide.shapes if (x.name == key if isinstance(key, str) else x.shape_id == key))
        sh.top = Emu(sh.top + Inches(dy))
        sh.height = Emu(sh.height + Inches(dh))


def qr_png(url: str, path: Path) -> Path:
    img = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=20, border=1)
    img.add_data(url)
    img.make(fit=True)
    img.make_image(fill_color="black", back_color="white").save(path)
    return path


# --------------------------------------------------------------------------------------------------------------
def main() -> int:
    prs = Presentation(str(TEMPLATE))
    slide = prs.slides[0]
    S = lambda i: shape(slide, i)  # noqa: E731

    # header
    set_paragraphs(S(14), TITLE)
    set_paragraphs(S(15), AUTHORS)

    # left column
    set_paragraphs(S(21), ABSTRACT)
    set_paragraphs(S(27), INTRO)
    for sid, paras in zip((35, 38, 41), RQS):
        set_paragraphs(S(sid), paras)
    set_paragraphs(S(47), METHODS)

    # approach
    set_text(S(52), APPROACH_TITLE)
    replace_picture(slide, S(53), FIGURES / "fig02_convention_window.png",
                    "Net GEX of SPY over the 30 trading days ending 2024-03-15 in four series, with the rule verdict of each.")
    set_text(S(54), APPROACH_CAPTION)
    set_paragraphs(S(55), RULE_HEADING)
    for (title_id, body_id), (title, body) in zip(((58, 59), (62, 63), (66, 67)), CARDS):
        set_text(S(title_id), title)
        set_text(S(body_id), body)
    set_paragraphs(S(68), RULE_NOTE)
    set_paragraphs(S(69), SERIES_HEADING)
    cats, vals, colors = SERIES_CHART
    set_chart(S(70), "2024–2025 windows detected by the rule (%)", cats, vals, colors, (0, 118),
              number_format='0.0"%"', outline_first=False)
    set_paragraphs(S(72), SERIES_NOTE)

    # results
    for (big, label, sub), ids in zip(CALLOUTS, ((79, 80, 81), (83, 84, 85), (87, 88, 89), (91, 92, 93))):
        for text, sid in zip((big, label, sub), ids):
            set_text(S(sid), text)
    boxes = [(14.30, 22.45, 6.27, 4.70), (20.87, 22.45, 6.27, 4.70), (27.43, 22.45, 6.27, 4.70)]
    for (fname, caption), pic_id, cap_id, box in zip(RESULT_FIGURES, (94, 95, 96), (97, 98, 99), boxes):
        replace_picture(slide, S(pic_id), FIGURES / fname, caption[0][1].replace("**", ""), box=box)
        set_paragraphs(S(cap_id), caption)
    set_paragraphs(S(101), LABELERS_HEADING)
    for (heading, values, axis), head_id, chart_id in zip(LABELER_CHARTS, (102, 104, 106), (103, 105, 107)):
        set_paragraphs(S(head_id), heading)
        set_chart(S(chart_id), f"{heading[0][1]} · {heading[1][1]}", LABELERS, values, LABELER_COLORS, axis)

    # right column
    set_text(S(112), SIDE_TITLE)
    set_paragraphs(S(113), SIDE_INTRO)
    set_table(S(114), SIDE_TABLE, SIDE_COL_WIDTHS)
    set_paragraphs(S(115), SIDE_NOTE)
    set_text(S(120), AGREEMENT_TITLE)
    for (value, label), (v_id, l_id) in zip(AGREEMENT, ((121, 122), (123, 124), (125, 126))):
        set_text(S(v_id), value)
        set_text(S(l_id), label)
    set_paragraphs(S(127), AGREEMENT_NOTE)
    set_paragraphs(S(133), CONCLUSIONS)
    set_paragraphs(S(135), TAKE_HOME)
    set_paragraphs(S(141), ACK)
    set_paragraphs(S(148), CONTACT)
    set_paragraphs(S(154), REFERENCES)
    with tempfile.TemporaryDirectory() as tmp:
        replace_picture(slide, S(147), qr_png(REPO_URL, Path(tmp) / "qr.png"), f"QR code: {REPO_URL}")
    # the Conclusions card has room to spare and the References card has none: shorten the one, lift the three cards
    # below it and give References the difference
    lift = 0.35
    nudge(slide, (128, 129), dh=-lift)                                     # Conclusions card (shadow, body)
    nudge(slide, (134, 135), dy=-lift)                                     # take-home box and text
    nudge(slide, (136, 137, 138, 139, 140, 141), dy=-lift)                 # Acknowledgments
    nudge(slide, (142, 143, 144, 145, 146, 148, "Picture 146"), dy=-lift)  # Contact Information and QR code
    nudge(slide, (151, 152, 153), dy=-lift)                                # References header, rule, title
    nudge(slide, (149, 150, 154), dy=-lift, dh=lift)                       # References card and text
    prs.core_properties.title = "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation (C-Day poster)"
    prs.core_properties.author = "Christopher Regan; Ying Xie"
    prs.core_properties.last_modified_by = "Christopher Regan"
    # the template's docProps/thumbnail.jpeg is a picture of the template poster; drop it (PowerPoint writes a new one)
    package_rels = prs.part.package._rels
    for rid in [rid for rid, rel in package_rels.items() if rel.reltype == RT.THUMBNAIL]:
        package_rels.pop(rid)
    prs.save(str(OUTPUT))
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
