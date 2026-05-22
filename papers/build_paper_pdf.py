"""Generate the AURORA-Mono Rev 2.0 paper PDF.

Run from the papers/ directory or from anywhere -- output path is
relative to this script's location.
"""
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image,
)

HERE = Path(__file__).resolve().parent
SIM_DIR = HERE / "aurora-mono-simulations"
PLOTS_DIR = SIM_DIR / "plots"
IMAGES_DIR = HERE.parent / "images"
OUTPUT = HERE / "aurora-mono-wheel-build-spec.pdf"

styles = getSampleStyleSheet()

cover_title_style = ParagraphStyle(
    "covertitle", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=28, leading=34,
    alignment=TA_CENTER, spaceAfter=8,
)
cover_subtitle_style = ParagraphStyle(
    "coversubtitle", parent=styles["Normal"],
    fontName="Helvetica-Oblique", fontSize=14, leading=18,
    alignment=TA_CENTER, textColor=colors.HexColor("#444444"),
    spaceAfter=24,
)
cover_author_style = ParagraphStyle(
    "coverauthor", parent=styles["Normal"],
    fontName="Helvetica", fontSize=13, leading=16,
    alignment=TA_CENTER, spaceAfter=4,
)
cover_meta_style = ParagraphStyle(
    "covermeta", parent=styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=14,
    alignment=TA_CENTER, textColor=colors.HexColor("#666666"),
    spaceAfter=2,
)
abstract_label_style = ParagraphStyle(
    "abstractlabel", parent=styles["Normal"],
    fontName="Helvetica-Bold", fontSize=11, leading=13,
    alignment=TA_CENTER, textColor=colors.HexColor("#102a43"),
    spaceBefore=18, spaceAfter=8,
)
abstract_style = ParagraphStyle(
    "abstract", parent=styles["BodyText"],
    fontName="Helvetica", fontSize=10.5, leading=14.5,
    leftIndent=36, rightIndent=36, alignment=TA_JUSTIFY,
    spaceBefore=4, spaceAfter=16,
)
h1_style = ParagraphStyle(
    "h1", parent=styles["Heading1"],
    fontName="Helvetica-Bold", fontSize=15, leading=19,
    textColor=colors.HexColor("#102a43"),
    spaceBefore=14, spaceAfter=8,
)
h2_style = ParagraphStyle(
    "h2", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12, leading=15,
    textColor=colors.HexColor("#243b53"),
    spaceBefore=10, spaceAfter=4,
)
body_style = ParagraphStyle(
    "body", parent=styles["BodyText"],
    fontName="Helvetica", fontSize=10, leading=13.5,
    alignment=TA_JUSTIFY, spaceAfter=6,
)
bullet_style = ParagraphStyle(
    "bullet", parent=body_style, leftIndent=14, bulletIndent=2, spaceAfter=2,
)
sub_bullet_style = ParagraphStyle(
    "subbullet", parent=body_style, leftIndent=28, bulletIndent=16, spaceAfter=2,
    fontSize=9.5, leading=13,
)
caption_style = ParagraphStyle(
    "caption", parent=styles["Normal"],
    fontName="Helvetica-Oblique", fontSize=9, leading=11,
    alignment=TA_CENTER, textColor=colors.HexColor("#555555"),
    spaceBefore=4, spaceAfter=12,
)
note_style = ParagraphStyle(
    "note", parent=styles["BodyText"],
    fontName="Helvetica-Oblique", fontSize=9.5, leading=12.5,
    leftIndent=10, rightIndent=10, alignment=TA_JUSTIFY,
    textColor=colors.HexColor("#444444"), spaceAfter=8,
)


def bullets(items, style=bullet_style):
    flows = []
    for item in items:
        if isinstance(item, tuple):
            text, sub = item
            flows.append(Paragraph(f"&bull;&nbsp; {text}", style))
            for s in sub:
                flows.append(Paragraph(f"&ndash;&nbsp; {s}", sub_bullet_style))
        else:
            flows.append(Paragraph(f"&bull;&nbsp; {item}", style))
    return flows


def section(title):
    return Paragraph(title, h1_style)


def subsection(title):
    return Paragraph(title, h2_style)


def para(text):
    return Paragraph(text, body_style)


def spec_table(rows, col_widths=None):
    table = Table(rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102a43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f7fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bcccdc")),
    ]))
    return table


def figure(path, width_in=5.5, caption=None):
    flows = []
    img = Image(str(path), width=width_in * inch,
                height=width_in * inch * 0.6,
                kind="proportional")
    flows.append(img)
    if caption:
        flows.append(Paragraph(caption, caption_style))
    return flows


def add_page_decorations(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawString(0.75 * inch, 0.5 * inch,
                      "AURORA-Mono Rev 2.0 — Design & Validation")
    canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.5 * inch,
                           f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.setLineWidth(0.4)
    canvas.line(0.75 * inch, 0.65 * inch,
                LETTER[0] - 0.75 * inch, 0.65 * inch)
    canvas.restoreState()


story = []

# ============================================================
# Cover / front matter
# ============================================================
story.append(Spacer(1, 0.6 * inch))
story.append(Paragraph("AURORA-Mono", cover_title_style))
story.append(Paragraph("(One-Piece) Rover Wheel", cover_title_style))
story.append(Paragraph(
    "Design Specification &amp; Screening-Level Validation",
    cover_subtitle_style,
))
story.append(Spacer(1, 0.3 * inch))
story.append(Paragraph("William Duckworth", cover_author_style))
story.append(Paragraph("Revision 2.0 &middot; 2026", cover_meta_style))
story.append(Spacer(1, 0.3 * inch))

# Cover image
if (IMAGES_DIR / "aurora-mono-build-spec.png").exists():
    img = Image(str(IMAGES_DIR / "aurora-mono-build-spec.png"),
                width=6.2 * inch, height=6.2 * inch * 0.52,
                kind="proportional")
    story.append(img)
    story.append(Paragraph(
        "Build specification drawing AURORA-MONO-B-02. Side elevation, "
        "vertical cross-section B&ndash;B showing the sandwich wall with "
        "the &plusmn;35&deg; X-brace helical rib lattice, and the full "
        "materials / rim-wall / spoke / mass-target callouts.",
        caption_style,
    ))

story.append(Paragraph("Abstract", abstract_label_style))
story.append(Paragraph(
    "AURORA-Mono is a one-piece composite rover wheel engineered to the "
    "NASA MicroChariot interface envelope. This document specifies "
    "Revision&nbsp;2.0 of the design, which integrates four targeted "
    "improvements identified by a closed-form Python validation "
    "campaign: a 1.0&nbsp;mm unfilled-PEKK compliant interlayer "
    "between the SiC-PEKK tread and the PEKK-CNT/CF outer skin; a "
    "reformulated SiC-PEKK tread with reduced coefficient of thermal "
    "expansion (&alpha;<sub>tread</sub> = 20&nbsp;ppm/K); chamfered "
    "lug-base edge geometry; and Ti-6Al-4V hub bolts torqued to 50% of "
    "proof load. With these changes the wheel meets a safety factor "
    "&ge;&nbsp;2.0 on every analytically resolved failure mode and "
    "&ge;&nbsp;1.5 on the static-peel mode at the lug-skin bond under "
    "lunar diurnal thermal cycling. The complete validation campaign "
    "(13 reproducible Python screening models) is documented in the "
    "companion <i>aurora-mono-simulations</i> folder of the repository.",
    abstract_style,
))

story.append(Paragraph("Revision history", abstract_label_style))
rev_rows = [
    ["Rev", "Date", "Notes"],
    ["1.0", "2026-02-15",
     "Initial design specification."],
    ["2.0", "2026-05-22",
     "Updated baseline integrating four design changes from screening "
     "validation campaign. New validation campaign and open-work sections."],
]
story.append(spec_table(rev_rows, col_widths=[0.6 * inch, 1.2 * inch, 4.4 * inch]))

story.append(PageBreak())

# ============================================================
# Section 0: Envelope & interfaces
# ============================================================
story.append(section("1. Envelope &amp; Interfaces (MicroChariot Compliant)"))
story.extend(bullets([
    "Overall OD at lug tips: <b>18.000 in</b> (457.20 mm)",
    "Overall width: <b>8.000 in</b> (203.20 mm)",
    "Rim OD (outer structural skin, pre-tread): <b>16.800 in</b> (426.72 mm)",
    "Hub pilot: <b>&Oslash; 3.185 in</b> (80.899 mm)",
    "Bolt circle: <b>&Oslash; 4.000 in</b> (101.60 mm), 8&times; #10-32 UNF THRU, equally spaced (45&deg;)",
    "Jack bolts: 2&times; #10-32 UNF THRU on the same &Oslash; 4.000 in circle, 180&deg; apart",
    "Pin holes: 2&times; &Oslash; 0.2502 &plusmn;0.001 in (6.356 &plusmn;0.025 mm) on &Oslash; 4.000 in circle, 180&deg; apart",
    "Hub adapter plate thickness (composite): 6.0 mm with 12.0 mm diameter pad bosses at holes",
    "Keep-out zone: honors 4.000 in (W) &times; 1.750 in (H) box from NASA drawing; no intrusion",
]))

story.append(subsection("1.1 Tolerances (unless noted)"))
story.extend(bullets([
    "Hub pattern features: &plusmn;0.05 mm (&plusmn;0.002 in)",
    "Critical radii (OD, width): &plusmn;0.25 mm (&plusmn;0.010 in)",
    "All others: &plusmn;0.5 mm (&plusmn;0.020 in)",
]))

# ============================================================
# Section 2: Materials
# ============================================================
story.append(section("2. Materials"))
story.append(para(
    "Rev&nbsp;2.0 introduces a compliant interlayer and a reformulated tread "
    "to address the thermal-cycling static-peel concern identified by the "
    "validation campaign (see Section&nbsp;11). The full material stack "
    "from outer surface to hub:"
))
story.extend(bullets([
    "<b>Tread lugs (wear layer):</b> Reformulated Silicon-Carbide-filled "
    "PEKK (SiC-PEKK), ~50&nbsp;vol&percnt; SiC. "
    "&rho; &asymp; 1.80&nbsp;g/cc; "
    "<b>&alpha;<sub>tread</sub> &asymp; 20&nbsp;ppm/K</b> "
    "(reduced from 29&nbsp;ppm/K in Rev&nbsp;1.0).",
    "<b>Compliant interlayer (NEW in Rev 2.0):</b> Unfilled PEKK shim, "
    "1.0&nbsp;mm thick, "
    "between the SiC-PEKK tread and the PEKK-CNT/CF outer skin. "
    "Bonds chemically to both same-family PEKK surfaces. "
    "&rho; &asymp; 1.30&nbsp;g/cc; "
    "E &asymp; 4&nbsp;GPa; "
    "&alpha; &asymp; 45&nbsp;ppm/K.",
    "<b>Outer/inner structural skins &amp; helical ribs:</b> Carbon "
    "Nanotube-reinforced, Carbon Fiber-reinforced Polyetherketoneketone "
    "(PEKK-CNT/CF). &rho; &asymp; 1.45&nbsp;g/cc; E &asymp; 50&nbsp;GPa "
    "(in-plane); &alpha; &asymp; 10&nbsp;ppm/K (in-plane).",
    "<b>Hub bolts (UPDATED in Rev 2.0):</b> Ti-6Al-4V #10-32 UNF "
    "(replaces A286 stainless in Rev&nbsp;1.0). Torqued to "
    "<b>50&percnt;</b> of proof load.",
    "Hub hole sleeves (optional): Ti-6Al-4V, wall 0.5&nbsp;mm "
    "(press-fit) for metal interfaces.",
    "Antistatic top-coat (non-lug areas): graphene-based, 0.05&nbsp;mm "
    "(vacuum-compatible).",
]))

# ============================================================
# Section 3: Rim wall sandwich (UPDATED)
# ============================================================
story.append(section("3. Rim Wall &ldquo;Sandwich&rdquo; Cross-Section"))
story.append(para("All dimensions radial from wheel center."))
story.extend(bullets([
    "<b>Tread lug (SiC-PEKK):</b> 9.0 mm nominal lug height + 6.24 mm "
    "carcass base (see Section&nbsp;6).",
    "<b>Compliant interlayer (NEW):</b> 1.0 mm unfilled PEKK between "
    "the tread carcass and the outer structural skin.",
    "<b>Outer structural skin:</b> 1.20 mm thick, continuous and sealed.",
    "<b>Core height between skins:</b> 7.00 mm nominal.",
    "<b>Inner structural skin (toward hub):</b> 1.20 mm thick, continuous.",
    "<b>Wall total (interlayer + skin + core + skin):</b> "
    "<b>10.40 mm</b> (Rev&nbsp;1.0 was 9.40 mm; +1 mm for interlayer).",
    "Inner surface local relief under lugs (flex zone): reduce inner-"
    "skin-side wall to 0.70&ndash;0.90 mm within a 28 &times; 20 mm "
    "oval directly beneath each lug, machined/pocketed from inside.",
]))

story.append(subsection("3.1 Helical ribs (between skins)"))
story.extend(bullets([
    "Pattern: alternating &plusmn;35&deg; helix families (X-brace lattice). Unchanged from Rev&nbsp;1.0.",
    "Rib web thickness: <b>1.8 mm</b> at mid-span, <b>2.2 mm</b> at skin tie-in.",
    "Rib pitch (circumferential spacing of nodes): 20.0 mm between successive ties on each skin.",
    "Rib bay (axial spacing across width): 12.0 mm, yielding &asymp;17 bays across the 203.20 mm width.",
    "Count around circumference: <b>48 ribs total</b> (24 at +35&deg;, 24 at &minus;35&deg;), evenly distributed.",
    "Local neck-down beneath lug footprints: &minus;12&percnt; rib thickness over a 20.0 mm arc length (adds micro-compliance).",
]))

story.append(subsection("3.2 Inboard debris ports (NOT on tread face)"))
story.extend(bullets([
    "&Oslash; 10.0 mm, one every 35&deg; (&asymp;10 ports per wheel).",
    "Lip-baffled with a 2.0 mm deep overhang; no line-of-sight to the outer skin.",
]))

# ============================================================
# Section 4: Hub spokes (unchanged)
# ============================================================
story.append(section("4. Hub &ldquo;Spokes&rdquo; (Torque Web, Inside Cavity)"))
story.append(para(
    "Thin composite webs run from the hub adapter to the inner rim skin "
    "and are not visible in the tread wall. Unchanged from Rev&nbsp;1.0."
))
story.extend(bullets([
    "Count: <b>6 web-spokes</b>, equally spaced.",
    "Web thickness: 5.0 mm at hub boss tapering to 3.0 mm at rim inner skin; aero-tri profile with 5.0 mm fillets both ends.",
    "Lightening pockets: triangular cutouts leaving &ge;30.0 mm minimum shear path; web area open ratio &asymp;45&percnt;.",
    "Purpose: torque transfer and stiffness with minimal mass.",
]))

# ============================================================
# Section 5: Tread system (UPDATED)
# ============================================================
story.append(section("5. Tread System"))
story.append(para(
    "Integral tread, molded onto the sealed outer skin through the 1.0 mm "
    "compliant PEKK interlayer. Base (carcass) thickness to reach the "
    "18.000 in OD with 9.0 mm lugs is <i>t<sub>base</sub></i> = "
    "<b>6.24 mm</b> (from outer skin up to the lug root). The "
    "construction places a thin outer shell (~1.0 mm) over the lattice "
    "peaks; the remaining ~5.2 mm is mostly rib crests and void, "
    "yielding a 10&ndash;12&percnt; solid equivalent."
))

story.append(subsection("5.1 Lug geometry (two staggered rows, dirt-bike style)"))
story.extend(bullets([
    "Height: 9.0 mm nominal; alternating 8.0 mm / 10.0 mm every other lug within a row.",
    "Plan shape: chevron blocks; rake angle 60&deg; leading face, trailing chamfer 22&deg;.",
    "Block length (circumferential): 45.0 mm long / 35.0 mm short, alternating (&plusmn;5.0 mm).",
    "Block width (axial): 14.0 mm; row centers at &plusmn;30.0 mm from mid-plane.",
    "Row phase shift (helical wrap): &frac12;-pitch (&asymp;20.0 mm) between rows.",
    "Shoulder side-biters: every 3rd lug gets a 3.0 mm tall, 4.0 mm long buttress at the outer shoulder.",
    "Void ratio (contact patch): 75&ndash;80&percnt; (coverage 19&ndash;20&percnt;).",
    "Root fillets: 1.2 mm on all interior edges to avoid chipping.",
    "External corner radii: 0.6&ndash;0.8 mm.",
    "<b>Chamfered lug-base edge geometry (NEW in Rev 2.0):</b> 1.5 mm "
    "&times; 45&deg; chamfer at the perimeter of each lug footprint to "
    "spread the stress singularity at the lug-skin bond edge under "
    "thermal-cycle and cresting loads.",
]))

story.append(subsection("5.2 Lug-to-skin bond stack (UPDATED in Rev 2.0)"))
story.extend(bullets([
    "<b>Layer 1 (top):</b> SiC-PEKK tread lug.",
    "<b>Layer 2 (NEW):</b> 1.0 mm unfilled-PEKK compliant interlayer.",
    "<b>Layer 3:</b> PEKK-CNT/CF outer structural skin.",
    "Bonded via three-stage same-family chemical bond: tread / "
    "interlayer co-mold at 355&ndash;365&nbsp;&deg;C, 0.6&ndash;0.8&nbsp;MPa, "
    "dwell &ge;20&nbsp;min; interlayer / skin bond same process window.",
    "Anti-peel keys (retained from Rev 1.0): 3 concentric 0.6 mm deep "
    "&times; 1.8 mm wide shallow grooves in the outer skin surface "
    "under each lug; fill with interlayer PEKK during molding.",
]))

# ============================================================
# Section 6: Hub bolt joint (UPDATED)
# ============================================================
story.append(section("6. Hub Bolt Joint"))
story.append(para(
    "Eight #10-32 UNF mounting bolts plus 2 jack bolts and 2 alignment "
    "pins on the &Oslash; 4.000 in bolt circle. The bolt material and "
    "preload spec were updated in Rev 2.0 to recover SF &ge; 2.0 on "
    "both bolt yield and pad-boss compression; geometry is unchanged "
    "from Rev&nbsp;1.0."
))
story.extend(bullets([
    "<b>Bolt material (UPDATED):</b> Ti-6Al-4V (was A286 stainless in "
    "Rev 1.0). Standard aerospace fastener spec; ~40&percnt; lighter "
    "than A286.",
    "<b>Preload spec (UPDATED):</b> torque to <b>50&percnt; of proof "
    "load</b> (was 70&percnt; in Rev 1.0). Tighten with a calibrated "
    "torque wrench or use load-indicating washers.",
    "All other joint geometry (bolt size, bolt circle, pad-boss diameter, "
    "alignment pins, jack bolts) unchanged from Rev 1.0.",
]))

# ============================================================
# Section 7: Manufacturing sequence
# ============================================================
story.append(section("7. Manufacturing Sequence (UPDATED)"))
story.append(para(
    "Same overall flow as Rev 1.0, with one additional step (4) inserting "
    "the compliant interlayer between skin consolidation and tread "
    "compression molding."
))
import_steps = [
    "Print lattice core and hub web in PEKK-CNT/CF using high-temperature additive manufacturing.",
    "Lay inner/outer skins (PEKK-CNT/CF tape) and co-consolidate in an autoclave (&asymp;360 &deg;C, 0.7 MPa, 2&ndash;3 hours).",
    "Machine the hub pattern, debris ports, and inner-surface relief pockets under the lug locations.",
    "<b>(NEW)</b> Lay the 1.0 mm unfilled-PEKK compliant interlayer on the prepared outer skin; bond at 355&ndash;365 &deg;C, 0.6&ndash;0.8 MPa, dwell &ge;20 min.",
    "Compression-mold the reformulated SiC-PEKK tread onto the interlayer using the chevron cavity tool with chamfered lug-base detail (engaging the anti-peel keys).",
    "Apply the antistatic top-coat, avoiding lug faces.",
    "Install Ti-6Al-4V hub bolts to 50&percnt; proof load using a calibrated torque wrench.",
    "Final QC: dimensional validation, mass validation (target 2.30&ndash;2.40 kg), and non-destructive inspection (ultrasound / CT).",
]
from reportlab.platypus import ListFlowable, ListItem
story.append(ListFlowable(
    [ListItem(Paragraph(s, body_style)) for s in import_steps],
    bulletType="1", leftIndent=20,
))

# ============================================================
# Section 8: Critical dimensions
# ============================================================
story.append(section("8. Critical Dimensions Summary"))
crit_rows = [
    ["Feature", "Dimension"],
    ["OD at lug tips", "18.000 in (457.20 mm)"],
    ["Width", "8.000 in (203.20 mm)"],
    ["Rim OD (pre-tread)", "16.800 in (426.72 mm)"],
    ["Outer / inner skin", "1.20 mm each"],
    ["Compliant interlayer (Rev 2.0)", "1.00 mm unfilled PEKK"],
    ["Core height", "7.00 mm"],
    ["Wall total", "10.40 mm"],
    ["Helical rib web", "1.8 mm (mid-span), 2.2 mm (tie-in)"],
    ["Helix angle", "±35°"],
    ["Ribs (count)", "48 total (24 positive / 24 negative)"],
    ["Hub web spokes", "6 spokes, 3.0–5.0 mm thick"],
    ["Tread base (carcass)", "6.24 mm (10–12% solid equivalent)"],
    ["Tread formulation (Rev 2.0)", "SiC-PEKK, ~50 vol% SiC"],
    ["Lug height", "9.0 mm nominal (8.0 / 10.0 mm alternating)"],
    ["Lug width / length (pitch)", "14.0 mm / 35.0 / 45.0 mm alternating"],
    ["Lug-base chamfer (Rev 2.0)", "1.5 mm × 45°"],
    ["Row offset", "±30.0 mm from mid-plane"],
    ["Void ratio", "75–80% (coverage 19–20%)"],
    ["Anti-peel keys", "3 grooves, 0.6 mm × 1.8 mm"],
    ["Debris ports (inboard)", "Ø 10.0 mm, every 35°, baffled"],
    ["Hub bolts (Rev 2.0)", "8× Ti-6Al-4V #10-32 UNF, 50% proof preload"],
]
story.append(spec_table(crit_rows, col_widths=[2.6 * inch, 3.6 * inch]))
story.append(Paragraph("Table 1. Critical dimensions summary, Rev 2.0.",
                       caption_style))

# ============================================================
# Section 9: Mass target
# ============================================================
story.append(section("9. Mass Target (As-Built)"))
story.extend(bullets([
    "<b>Rev 2.0 specification:</b> 2.30&ndash;2.40 kg (5.07&ndash;5.29 lb). "
    "Rev 1.0 was 2.21&ndash;2.30 kg; the 1.0 mm unfilled-PEKK interlayer "
    "adds &asymp;60&ndash;90 g, partially offset by the lighter "
    "Ti-6Al-4V bolts (&asymp;5&ndash;10 g savings across 10 fasteners).",
    "Mass optimization margin: reduce total surface coverage down to "
    "19&percnt;, or implement hollow-web configurations within the lugs, "
    "saving 80&ndash;120 g while maintaining the identical external "
    "footprint.",
]))

# ============================================================
# Section 10: Validation campaign (NEW)
# ============================================================
story.append(section("10. Validation Campaign"))
story.append(para(
    "Rev 2.0 was shaped by a 13-check Python validation campaign that "
    "evaluated every identifiable failure mode at screening fidelity. "
    "All scripts are reproducible (fixed random seed), with CSV outputs "
    "and plots, and live in the companion "
    "<i>aurora-mono-simulations/</i> folder of the repository. Headline "
    "results:"
))

val_rows = [
    ["Check", "Mode", "Headline result (Rev 2.0)"],
    ["Strip stress",
     "Skin tensile under impact",
     "Min SF 3.14, 0 fracture flags"],
    ["Sensitivity sweep",
     "±50% on dominant params",
     "Min SF >2.1 in all sweeps"],
    ["Lug shear",
     "Bond shear under traction",
     "SF 13–27"],
    ["Lug peel (driving)",
     "Bond peel from eccentric load",
     "SF 6.1, ≥1.8 across sweep"],
    ["Fatigue (driving)",
     "Miner's-rule over 696k cycles",
     "D ≈ 0, life >7,000 km"],
    ["Helical rib lattice",
     "Per-rib stress, buckling, shear",
     "SF >3 worst-case"],
    ["Thermal cycling",
     "Static peel from diurnal swing",
     "Baseline 0.88 → Rev 2.0 SF 4.85"],
    ["Viscoelastic relax.",
     "Prony + TTS, not FEM",
     "Confirms static, not fatigue, mode"],
    ["Hub bolt joint",
     "Preload, shear, pad compression",
     "Baseline 1.38/1.82 → Rev 2.0 2.14/3.33"],
    ["Launch load",
     "QS 6g + Miles random vib",
     "Driving loads govern, not launch"],
    ["Static-peel iteration",
     "Recommended Rev 2.0 mitigations",
     "Stack identified, SF 4.85"],
    ["Bolt-joint iteration",
     "Recommended Rev 2.0 changes",
     "Stack identified, both SFs > 2"],
    ["Modal analysis",
     "Closed-form 6-mode estimate",
     "3 modes in 50–800 Hz band; FEM needed"],
]
story.append(spec_table(val_rows,
                        col_widths=[1.6 * inch, 2.1 * inch, 2.5 * inch]))
story.append(Paragraph(
    "Table 2. Validation campaign summary. All checks run against the "
    "Rev 2.0 design. See <i>aurora-mono-simulations/README.md</i> for "
    "the full method, sensitivity sweeps, and limitations of each check.",
    caption_style,
))

story.append(subsection("10.1 Selected validation plots"))

if (PLOTS_DIR / "wear_vs_distance.png").exists():
    story.extend(figure(
        PLOTS_DIR / "wear_vs_distance.png", width_in=5.5,
        caption=(
            "Figure 1. Cumulative tread wear vs distance over 1000 km of "
            "stochastic lunar driving (main screening model). Final wear "
            "9.0 mm against 9.0 mm nominal lug height."
        ),
    ))

if (PLOTS_DIR / "viscoelastic_stress_trace.png").exists():
    story.extend(figure(
        PLOTS_DIR / "viscoelastic_stress_trace.png", width_in=5.8,
        caption=(
            "Figure 2. Bond stress over three lunar diurnal cycles in the "
            "Rev 1.0 design (no interlayer). Peak peel ~11 MPa exceeds "
            "the bond's 10 MPa static allowable on first cool-down. "
            "Rev 2.0 incorporates the 1.0 mm compliant interlayer "
            "(plus reformulated tread and chamfered lug edges) that "
            "drops peak peel to ~2 MPa, SF 4.85."
        ),
    ))

if (PLOTS_DIR / "modal_on_launch_spectrum.png").exists():
    story.extend(figure(
        PLOTS_DIR / "modal_on_launch_spectrum.png", width_in=5.8,
        caption=(
            "Figure 3. Estimated wheel natural frequencies (closed-form, "
            "not 3D eigenanalysis) overlaid on a typical launch random-"
            "vib PSD envelope. Rim torsional, n=2, and n=3 modes sit "
            "inside the 50–800 Hz damaging band (red). Coupled-loads "
            "FEM is needed to convict or acquit launch survivability "
            "at this fidelity."
        ),
    ))

# ============================================================
# Section 11: Open work
# ============================================================
story.append(section("11. Open Work &amp; Next-Fidelity Steps"))
story.append(para(
    "The screening campaign documented in Section&nbsp;10 is the analytical "
    "envelope of what closed-form Python models can resolve for this "
    "design. The next-fidelity items below all require either real solver "
    "tooling, coupon test data, or physical hardware:"
))

story.append(subsection("11.1 FEM / coupled-loads"))
story.extend(bullets([
    "<b>3D viscoelastic FEM</b> of the lug-skin region under the diurnal cycle with measured Prony coefficients &mdash; validates the Rev 2.0 static-peel SF 4.85 from screening.",
    "<b>3D random-vibration FEM or coupled-loads analysis with the rover suspension</b> &mdash; three wheel modes sit inside the launch peak band per Section&nbsp;10; the Miles' SDOF approximation under-estimates cumulative response.",
    "<b>3D truss/solid FEM of the rib lattice</b> &mdash; the lattice check treats ribs as pin-ended struts; the real critical location is the rib-to-skin joint.",
    "<b>Fracture-mechanics peel analysis</b> using G<sub>c</sub> (Paris-law crack growth) for the actual co-mold bond, replacing the stress-based peel screening.",
    "<b>Bolt-joint creep + fatigue under thermal cycling</b> &mdash; the bolt screening is initial-condition only; PEKK pad-boss creep at +127&nbsp;&deg;C would relax preload over a long mission.",
]))

story.append(subsection("11.2 Coupon tests"))
story.extend(bullets([
    "CTE values for SiC-PEKK and PEKK-CNT/CF in the actual Rev 2.0 production formulations.",
    "Co-mold bond strength (shear, peel, G<sub>c</sub>, S-N) for the new three-layer stack (SiC-PEKK / unfilled-PEKK / PEKK-CNT/CF).",
    "Wear coefficient for the reformulated SiC-PEKK against JSC-1A lunar regolith simulant.",
    "Prony-series relaxation coefficients for the SiC-PEKK and unfilled-PEKK at +127&nbsp;&deg;C.",
]))

story.append(subsection("11.3 Operational scope not yet checked"))
story.extend(bullets([
    "Steering / scrub loads if the rover steers.",
    "Radiation environment (UV, GCR, SPE) degradation on PEKK over the mission life.",
    "A real thermal model (radiation balance + 1D conduction through the sandwich wall + regolith contact + sun/shadow cycling), replacing the prescribed temperature schedule used in the screening model.",
]))

story.append(subsection("11.4 Hardware"))
story.append(Paragraph(
    "Physical prototype build and bench test is out of scope for this "
    "study. Fabrication cost for a single qualified composite wheel of "
    "this geometry (PEKK feedstock, autoclave time, custom chevron "
    "compression mold, NDI) is estimated in the $15K&ndash;$50K range &mdash; "
    "not achievable on a hobby budget, and not the goal of a screening "
    "campaign. The next physical step would be coupon-level material "
    "qualification, not a full wheel.",
    note_style,
))

doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=LETTER,
    leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    topMargin=0.85 * inch, bottomMargin=0.85 * inch,
    title="AURORA-Mono Rev 2.0 — Design Specification and Validation",
    author="William Duckworth",
    subject="Rover wheel design specification and screening validation",
)

doc.build(story, onFirstPage=add_page_decorations,
          onLaterPages=add_page_decorations)
print(f"wrote {OUTPUT}")
