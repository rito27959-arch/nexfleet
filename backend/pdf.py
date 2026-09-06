# -*- coding: utf-8 -*-
"""Génération de PDF professionnels — fiches de contrôle et rapport de parc."""

import io
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from reportlab.graphics.barcode import code128
    HAS_BARCODE = True
except Exception:  # pragma: no cover
    HAS_BARCODE = False
from reportlab.graphics.shapes import Drawing

# ---------------------------------------------------------------- palette
INK = colors.HexColor("#0B1220")
ACCENT = colors.HexColor("#6366F1")
ACCENT_2 = colors.HexColor("#22D3EE")
GOOD = colors.HexColor("#10B981")
WARN = colors.HexColor("#F59E0B")
BAD = colors.HexColor("#EF4444")
LIGHT = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#E2E8F0")
MID = colors.HexColor("#64748B")
WHITE = colors.white


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AppTitle", fontName="Helvetica-Bold", fontSize=19, leading=23,
        textColor=WHITE, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="AppSub", fontName="Helvetica", fontSize=9.5, leading=13,
        textColor=colors.HexColor("#C7D2FE"), alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="Section", fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=INK, spaceBefore=6, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SubSection", fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=MID, spaceBefore=4, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Cell", fontName="Helvetica", fontSize=9.5, leading=12, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="CellB", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=INK,
    ))
    styles.add(ParagraphStyle(
        name="HeaderCell", fontName="Helvetica-Bold", fontSize=9.5, leading=12,
        textColor=WHITE,
    ))
    styles.add(ParagraphStyle(
        name="Label", fontName="Helvetica-Bold", fontSize=8, leading=11,
        textColor=MID, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="Value", fontName="Helvetica", fontSize=10, leading=13, textColor=INK,
    ))
    return styles


def _fmt(v, empty="—"):
    return (str(v).strip() if v is not None and str(v).strip() != "" else empty)


def _barcode(value):
    if not HAS_BARCODE or not value:
        return None
    try:
        bc = code128.Code128(str(value), barHeight=10 * mm, barWidth=0.55)
        d = Drawing(70 * mm, 14 * mm)
        d.add(bc)
        return d
    except Exception:
        return None


def _header(st, title, subtitle):
    """Bandeau supérieur dégradé (dégradé simulé par une table)."""
    header = Table([[Paragraph(title, st.AppTitle),
                     Paragraph(subtitle, st.AppSub)]],
                   colWidths=[95 * mm, 85 * mm])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#121A30")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return header


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, 14 * mm, A4[0] - 14 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MID)
    canvas.drawString(14 * mm, 9.5 * mm, "NexFleet — Gestion de parc automobile")
    canvas.drawRightString(A4[0] - 14 * mm, 9.5 * mm,
                           f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} — page {doc.page}")
    canvas.restoreState()


def _info_block(rows, label_style, value_style):
    data = []
    for k, v in rows:
        data.append([Paragraph(f"<b>{k.upper()}</b>", label_style), Paragraph(_fmt(v), value_style)])
    t = Table(data, colWidths=[42 * mm, 138 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 0.6, BORDER),
    ]))
    return t


CHECKLIST = [
    ("Carrosserie et état extérieur", "peinture, corrosion, pare-chocs"),
    ("Pneumatiques et pression", "usure, pression, profondeur de gomme"),
    ("Freins et plaquettes", "circuit, plaquettes, efficacité"),
    ("Éclairage et signalisation", "phares, feux, clignotants, klaxon"),
    ("Niveaux (huile, refroidissement)", "niveaux moteur et liquides"),
    ("Batterie et démarrage", "charge, démarrage, connectique"),
    ("Essuie-glaces et lave-glace", "balais, réservoir, jets"),
    ("Suspension et direction", "amortisseurs, jeu, géométrie"),
    ("Documents de bord", "assurance, vignette, contrôle technique"),
    ("Sécurité (triangle, trousse)", "équipement obligatoire"),
    ("Climatisation / chauffage", "fonctionnement global"),
    ("Roue de secours / kit", "présence et état"),
]


def control_pdf(vehicle, driver, items, resultat, notes, type_controle):
    """Fiche de contrôle véhicule (PDF, bytes)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=15 * mm, bottomMargin=18 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            title=f"Fiche de contrôle — {vehicle['immatriculation']}",
                            author="NexFleet")
    st = _base_styles()
    story = []

    # ---- en-tête
    story.append(_header(st, "FICHE DE CONTRÔLE VÉHICULE", "NexFleet • Gestion de parc automobile"))
    story.append(Spacer(1, 6 * mm))

    # ---- identité véhicule
    story.append(Paragraph("IDENTITÉ DU VÉHICULE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    imat = vehicle.get("immatriculation", "")
    story.append(_info_block([
        ("Immatriculation", imat),
        ("Véhicule", f"{vehicle['marque']} {vehicle['modele']}"),
        ("Type / usage", f"{vehicle.get('type','—')} • {vehicle.get('carburant','—')}"),
        ("Année / kilométrage", f"{_fmt(vehicle.get('annee'))} • {_fmt(vehicle.get('kilometrage'))} km"),
        ("Direction", _fmt(vehicle.get("direction"))),
        ("Affectation", _fmt(vehicle.get("affectation"))),
        ("Vignette / assurance / CT", f"{_fmt(vehicle.get('vignette_exp'))} / {_fmt(vehicle.get('assurance_exp'))} / {_fmt(vehicle.get('ctrl_tech_exp'))}"),
        ("N° Châssis (VIN)", _fmt(vehicle.get("num_chassis"))),
        ("N° Moteur", _fmt(vehicle.get("num_moteur"))),
        ("N° Carte grise", _fmt(vehicle.get("carte_grise"))),
        ("Exp. carte grise", _fmt(vehicle.get("carte_grise_exp"))),
        ("Chevaux (CV)", _fmt(vehicle.get("cv"))),
        ("GPS", f"{_fmt(vehicle.get('lat'))}, {_fmt(vehicle.get('lng'))}" if vehicle.get("lat") else "—"),
        ("Conducteur", _fmt(driver) if driver else "Non affecté"),
    ], st.Label, st.Value))
    story.append(Spacer(1, 4 * mm))

    # ---- infos contrôle
    story.append(Paragraph("INFORMATIONS DU CONTRÔLE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    story.append(_info_block([
        ("Date", _fmt(datetime.now().strftime("%d/%m/%Y %H:%M"))),
        ("Type de contrôle", _fmt(type_controle, "Contrôle technique")),
        ("Résultat", resultat if resultat else "En cours"),
        ("Référence", f"CT-{date.today().strftime('%Y%m%d')}-{vehicle['id']:04d}"),
    ], st.Label, st.Value))
    story.append(Spacer(1, 4 * mm))

    # ---- checklist
    story.append(Paragraph("POINTS DE CONTRÔLE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))

    def _state_cell(val):
        val = (val or "").strip().lower()
        color = MID
        label = "Non contrôlé"
        if val in ("conforme", "conforme.", "ok", "bon"):
            color = GOOD
            label = "CONFORME"
        elif val in ("non conforme", "non conforme.", "defectueux", "hs", "refus"):
            color = BAD
            label = "NON CONFORME"
        elif val in ("a surveiller", "a suivre", "attention", "usure"):
            color = WARN
            label = "À SURVEILLER"
        return Paragraph(f'<font color="{color.hexval() if hasattr(color,"hexval") else "#333333"}">'
                         f'<b>{label}</b></font>', st.Cell)

    checklist_rows = [[Paragraph(f"<b>{name}</b><br/><font size=8 color='#64748B'>{desc}</font>", st.Cell),
                       _state_cell(items.get(name, ""))] for name, desc in CHECKLIST]
    ct = Table(checklist_rows, colWidths=[120 * mm, 60 * mm])
    ct.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    story.append(ct)
    story.append(Spacer(1, 4 * mm))

    # ---- observations
    if notes and str(notes).strip():
        story.append(Paragraph("OBSERVATIONS", st.Section))
        story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
        obs = Table([[Paragraph(_fmt(notes), st.Value)]], colWidths=[180 * mm])
        obs.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#FDBA74")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(obs)
        story.append(Spacer(1, 4 * mm))

    # ---- signature + barcode
    sig_rows = [[Paragraph("<b>Réalisé par</b><br/><br/><br/>______________________", st.Value),
                 Paragraph("<b>Responsable de parc</b><br/><br/><br/>______________________", st.Value)]]
    sig = Table(sig_rows, colWidths=[90 * mm, 90 * mm])
    sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    story.append(sig)
    story.append(Spacer(1, 5 * mm))

    bc = _barcode(imat)
    if bc is not None:
        story.append(Spacer(1, 2 * mm))
        story.append(bc)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def parc_report(vehicles, stats, controls_by_month,
                maintenance=None, maintenance_by_vehicle=None, maintenance_total=0,
                vidanges=None, vidanges_by_vehicle=None, vidanges_total=0):
    """Rapport de l'état du parc (PDF, bytes)."""
    maintenance = maintenance or []
    maintenance_by_vehicle = maintenance_by_vehicle or []
    maintenance_total = maintenance_total or 0
    vidanges = vidanges or []
    vidanges_by_vehicle = vidanges_by_vehicle or []
    vidanges_total = vidanges_total or 0
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=15 * mm, bottomMargin=18 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            title="Rapport du parc automobile",
                            author="NexFleet")
    st = _base_styles()
    story = []

    story.append(_header(st, "RAPPORT DU PARC AUTOMOBILE",
                         f"NexFleet • État au {datetime.now().strftime('%d/%m/%Y')}"))
    story.append(Spacer(1, 6 * mm))

    # ---- synthèse
    story.append(Paragraph("SYNTHÈSE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    stat_rows = [[Paragraph(f"<font color='#6366F1' size=16><b>{stats.get('total',0)}</b></font>", st.Cell),
                  Paragraph(f"<font color='#10B981' size=16><b>{stats.get('en_service',0)}</b></font>", st.Cell),
                  Paragraph(f"<font color='#F59E0B' size=16><b>{stats.get('en_maintenance',0)}</b></font>", st.Cell),
                  Paragraph(f"<font color='#EF4444' size=16><b>{stats.get('en_panne',0)}</b></font>", st.Cell),
                  Paragraph(f"<font color='#64748B' size=16><b>{stats.get('drivers',0)}</b></font>", st.Cell)],
                 [Paragraph("<b>Véhicules</b>", st.Cell),
                  Paragraph("<b>En service</b>", st.Cell),
                  Paragraph("<b>En maintenance</b>", st.Cell),
                  Paragraph("<b>En panne</b>", st.Cell),
                  Paragraph("<b>Conducteurs</b>", st.Cell)]]
    stt = Table(stat_rows, colWidths=[36 * mm] * 5)
    stt.setStyle(TableStyle([
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(stt)
    story.append(Spacer(1, 5 * mm))

    # ---- véhicules par direction
    story.append(Paragraph("VÉHICULES PAR DIRECTION", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))

    def _status_p(v):
        s = (v.get("statut") or "").lower()
        color = "#10B981" if "service" in s else ("#F59E0B" if "maintenance" in s or "révision" in s else "#EF4444")
        return Paragraph(f'<font color="{color}"><b>{_fmt(v.get("statut"))}</b></font>', st.Cell)

    dirs = {}
    for v in vehicles:
        d = (v.get("direction") or "").strip() or "Non affecté"
        dirs.setdefault(d, []).append(v)

    for dir_name in sorted(dirs.keys()):
        dir_vehicles = dirs[dir_name]
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(f"{dir_name} ({len(dir_vehicles)} véhicule{'s' if len(dir_vehicles) > 1 else ''})", st.SubSection))

        head = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
                ["Immatriculation", "Véhicule", "Affectation", "Année", "Carburant", "Km", "Statut"]]

        rows = [head]
        for v in dir_vehicles:
            rows.append([
                Paragraph(f"<b>{_fmt(v.get('immatriculation'))}</b>", st.Cell),
                Paragraph(f"{_fmt(v.get('marque'))} {_fmt(v.get('modele'))}", st.Cell),
                Paragraph(_fmt(v.get("affectation")) or "—", st.Cell),
                Paragraph(_fmt(v.get("annee")), st.Cell),
                Paragraph(_fmt(v.get("carburant")), st.Cell),
                Paragraph(f"{_fmt(v.get('kilometrage'))}", st.Cell),
                _status_p(v),
            ])
        vt = Table(rows, colWidths=[28 * mm, 34 * mm, 34 * mm, 14 * mm, 20 * mm, 24 * mm, 28 * mm],
                   repeatRows=1)
        vt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(vt)
    story.append(Spacer(1, 6 * mm))

    # ---- coûts de maintenance
    story.append(Paragraph("MAINTENANCE — COÛTS ET INTERVENTIONS", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))

    summary_rows = [[Paragraph("<b>Coût total de maintenance</b>", st.Cell),
                     Paragraph(f"<b>{_fmt_fcfa(maintenance_total)}</b>", st.Cell),
                     Paragraph("<b>Interventions enregistrées</b>", st.Cell),
                     Paragraph(f"<b>{len(maintenance)}</b>", st.Cell)]]
    st_sum = Table(summary_rows, colWidths=[52 * mm, 39 * mm, 52 * mm, 39 * mm])
    st_sum.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(st_sum)
    story.append(Spacer(1, 4 * mm))

    if maintenance_by_vehicle:
        story.append(Paragraph("Coût cumulé par véhicule", st.SubSection))
        bhead = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
                 ["Immatriculation", "Véhicule", "Interventions", "Coût total"]]
        brows = [bhead]
        for b in maintenance_by_vehicle:
            brows.append([
                Paragraph(f"<b>{_fmt(b.get('immatriculation'))}</b>", st.Cell),
                Paragraph(f"{_fmt(b.get('marque'))} {_fmt(b.get('modele'))}", st.Cell),
                Paragraph(str(b.get("count", 0)), st.Cell),
                Paragraph(f"<b>{_fmt_fcfa(b.get('cout', 0))}</b>", st.Cell),
            ])
        bt = Table(brows, colWidths=[38 * mm, 52 * mm, 34 * mm, 58 * mm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(bt)
        story.append(Spacer(1, 5 * mm))

    if maintenance:
        story.append(Paragraph("Dernières interventions de maintenance", st.SubSection))
        mhead = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
                 ["Date", "Véhicule", "Intervention", "Coût", "Garage"]]
        mrows2 = [mhead]
        for m in maintenance[:40]:
            mrows2.append([
                Paragraph(_fmt(m.get("date")), st.Cell),
                Paragraph(f"{_fmt(m.get('marque'))} {_fmt(m.get('modele'))} · {_fmt(m.get('immatriculation'))}", st.Cell),
                Paragraph(_fmt(m.get("type")), st.Cell),
                Paragraph(f"<b>{_fmt_fcfa(m.get('cout', 0))}</b>", st.Cell),
                Paragraph(_fmt(m.get("garage")), st.Cell),
            ])
        mt2 = Table(mrows2, colWidths=[26 * mm, 50 * mm, 36 * mm, 34 * mm, 36 * mm], repeatRows=1)
        mt2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(mt2)
        story.append(Spacer(1, 6 * mm))

    # ---- vidanges
    story.append(Paragraph("VIDANGES — COÛTS ET SUIVI", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))

    vg_summary = [[Paragraph("<b>Coût total des vidanges</b>", st.Cell),
                   Paragraph(f"<b>{_fmt_fcfa(vidanges_total)}</b>", st.Cell),
                   Paragraph("<b>Vidanges enregistrées</b>", st.Cell),
                   Paragraph(f"<b>{len(vidanges)}</b>", st.Cell)]]
    vg_st = Table(vg_summary, colWidths=[52 * mm, 39 * mm, 52 * mm, 39 * mm])
    vg_st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(vg_st)
    story.append(Spacer(1, 4 * mm))

    if vidanges_by_vehicle:
        story.append(Paragraph("Coût cumulé par véhicule", st.SubSection))
        vbhead = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
                  ["Immatriculation", "Véhicule", "Vidanges", "Coût total"]]
        vbrows = [vbhead]
        for b in vidanges_by_vehicle:
            vbrows.append([
                Paragraph(f"<b>{_fmt(b.get('immatriculation'))}</b>", st.Cell),
                Paragraph(f"{_fmt(b.get('marque'))} {_fmt(b.get('modele'))}", st.Cell),
                Paragraph(str(b.get("count", 0)), st.Cell),
                Paragraph(f"<b>{_fmt_fcfa(b.get('cout', 0))}</b>", st.Cell),
            ])
        vbt = Table(vbrows, colWidths=[38 * mm, 52 * mm, 34 * mm, 58 * mm], repeatRows=1)
        vbt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(vbt)
        story.append(Spacer(1, 5 * mm))

    if vidanges:
        story.append(Paragraph("Dernières vidanges", st.SubSection))
        vhead = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
                 ["Date", "Véhicule", "Km compteur", "Km de la vidange",
                  "Prochaine", "Restant", "Consommables", "Coût"]]
        vrows2 = [vhead]
        for g in vidanges[:40]:
            vrows2.append([
                Paragraph(_fmt(g.get("date")), st.Cell),
                Paragraph(f"{_fmt(g.get('marque'))} {_fmt(g.get('modele'))} · {_fmt(g.get('immatriculation'))}", st.Cell),
                Paragraph(f"{_fmt(g.get('km'))}", st.Cell),
                Paragraph(f"{_fmt(g.get('km_interval'))}", st.Cell),
                Paragraph(f"{_fmt(g.get('prochaine_km'))}", st.Cell),
                _vg_restant(g, st),
                Paragraph(_vg_consommables(g), st.Cell),
                Paragraph(f"<b>{_fmt_fcfa(g.get('cout', 0))}</b>", st.Cell),
            ])
        vgt = Table(vrows2, colWidths=[17 * mm, 38 * mm, 17 * mm, 22 * mm, 18 * mm, 18 * mm, 34 * mm, 18 * mm],
                    repeatRows=1)
        vgt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(vgt)
        story.append(Spacer(1, 6 * mm))

    # ---- contrôles par mois
    story.append(Paragraph("CONTRÔLES PAR MOIS (6 derniers mois)", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    mrows = [[Paragraph(m, st.Cell) for m in [c["month"] for c in controls_by_month]]]
    mrows.append([Paragraph(f"<b>{c['count']}</b>", st.Cell) for c in controls_by_month])
    mt = Table(mrows, colWidths=[180 * mm / max(len(controls_by_month), 1)] * max(len(controls_by_month), 1))
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(mt)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _fmt_fcfa(v):
    try:
        return f"{round(float(v)):,}".replace(",", " ") + " FCFA"
    except (ValueError, TypeError):
        return "0 FCFA"


def _vg_consommables(g):
    """Consommables d'une vidange : huile, filtres et liquides remplacés."""
    parts = []
    specs = []
    if g.get("huile"):
        specs.append(_fmt(g["huile"]))
    if g.get("filtre_huile") or g.get("filtre"):
        specs.append("filtre huile")
    if g.get("filtre_gasoil"):
        specs.append("filtre gazoil")
    if g.get("huile_transmission"):
        specs.append("huile transmission")
    if specs:
        parts.append(", ".join(specs))
    liq = []
    if g.get("liquide_refroidissement"):
        liq.append("liquide refroid.")
    if g.get("liquide_laveglace"):
        liq.append("lave-glace")
    if liq:
        parts.append(", ".join(liq))
    return "<br/>".join(parts) if parts else "—"


def _vg_restant(g, st):
    """Kilomètres restants avant la prochaine vidange, colorés par urgence."""
    prochaine = int(g.get("prochaine_km") or 0)
    km_now = int(g.get("kilometrage") or 0)
    if not prochaine:
        return Paragraph("—", st.Cell)
    left = prochaine - km_now
    if left <= 0:
        color, label = "#EF4444", "Dépassée"
    elif left <= 500:
        color, label = "#F59E0B", f"{left} km"
    else:
        color, label = "#10B981", f"{left} km"
    return Paragraph(f'<font color="{color}"><b>{label}</b></font>', st.Cell)


def vidanges_report(vidanges, total_cost, by_vehicle, year_count):
    """Rapport des vidanges (PDF, bytes)."""
    vidanges = vidanges or []
    by_vehicle = by_vehicle or []
    total_cost = total_cost or 0
    year_count = year_count or 0
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=15 * mm, bottomMargin=18 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            title="Rapport des vidanges",
                            author="NexFleet")
    st = _base_styles()
    story = []

    story.append(_header(st, "RAPPORT DES VIDANGES",
                         f"NexFleet • État au {datetime.now().strftime('%d/%m/%Y')}"))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("SYNTHÈSE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    summary_rows = [[Paragraph("<b>Vidanges enregistrées</b>", st.Cell),
                     Paragraph(f"<b>{len(vidanges)}</b>", st.Cell),
                     Paragraph("<b>Coût total</b>", st.Cell),
                     Paragraph(f"<b>{_fmt_fcfa(total_cost)}</b>", st.Cell),
                     Paragraph(f"<b>Cette année ({date.today().year})</b>", st.Cell),
                     Paragraph(f"<b>{year_count}</b>", st.Cell)]]
    stt = Table(summary_rows, colWidths=[46 * mm, 24 * mm, 32 * mm, 38 * mm, 34 * mm, 22 * mm])
    stt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stt)
    story.append(Spacer(1, 5 * mm))

    if by_vehicle:
        story.append(Paragraph("COÛT PAR VÉHICULE", st.Section))
        story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
        bhead = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
                 ["Immatriculation", "Véhicule", "Vidanges", "Coût total"]]
        brows = [bhead]
        for b in by_vehicle:
            brows.append([
                Paragraph(f"<b>{_fmt(b.get('immatriculation'))}</b>", st.Cell),
                Paragraph(f"{_fmt(b.get('marque'))} {_fmt(b.get('modele'))}", st.Cell),
                Paragraph(str(b.get("count", 0)), st.Cell),
                Paragraph(f"<b>{_fmt_fcfa(b.get('cout', 0))}</b>", st.Cell),
            ])
        bt = Table(brows, colWidths=[38 * mm, 52 * mm, 34 * mm, 58 * mm], repeatRows=1)
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(bt)
        story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("DÉTAIL DES VIDANGES", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    head = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
            ["Date", "Véhicule", "Km compteur", "Km de la vidange",
             "Prochaine", "Restant", "Consommables", "Coût"]]
    rows = [head]
    for g in vidanges:
        rows.append([
            Paragraph(_fmt(g.get("date")), st.Cell),
            Paragraph(f"{_fmt(g.get('marque'))} {_fmt(g.get('modele'))} · {_fmt(g.get('immatriculation'))}", st.Cell),
            Paragraph(f"{_fmt(g.get('km'))}", st.Cell),
            Paragraph(f"{_fmt(g.get('km_interval'))}", st.Cell),
            Paragraph(f"{_fmt(g.get('prochaine_km'))}", st.Cell),
            _vg_restant(g, st),
            Paragraph(_vg_consommables(g), st.Cell),
            Paragraph(f"<b>{_fmt_fcfa(g.get('cout', 0))}</b>", st.Cell),
        ])
    vt = Table(rows, colWidths=[17 * mm, 38 * mm, 17 * mm, 22 * mm, 18 * mm, 18 * mm, 34 * mm, 18 * mm],
               repeatRows=1)
    vt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(vt)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def budget_report(summary):
    """Rapport Budget vs Réalisé (PDF, bytes) — comparaison du plan de
    maintenance préventive importé avec les dépenses réellement enregistrées."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=15 * mm, bottomMargin=18 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            title="Rapport Budget Maintenance", author="NexFleet")
    st = _base_styles()
    story = []
    annee = summary.get("annee", date.today().year)

    story.append(_header(st, "BUDGET MAINTENANCE — PRÉVU vs RÉALISÉ",
                         f"NexFleet • Exercice {annee} • Édité le {datetime.now().strftime('%d/%m/%Y')}"))
    story.append(Spacer(1, 6 * mm))

    if not summary.get("has_plan"):
        story.append(Paragraph(
            "Aucun plan budgétaire n'a encore été importé pour cet exercice. "
            "Importez le fichier « Plan d'achat annuel » depuis la page Budget.", st.Cell))
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buf.getvalue()

    story.append(Paragraph("SYNTHÈSE GLOBALE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    sum_rows = [[Paragraph("<b>Budget prévu</b>", st.Cell), Paragraph(f"<b>{_fmt_fcfa(summary['total_prevu'])}</b>", st.Cell),
                Paragraph("<b>Réalisé</b>", st.Cell), Paragraph(f"<b>{_fmt_fcfa(summary['total_realise'])}</b>", st.Cell),
                Paragraph("<b>Taux de consommation</b>", st.Cell),
                Paragraph(f"<b>{summary['taux_global']}%</b>", st.Cell)]]
    stt = Table(sum_rows, colWidths=[26 * mm, 40 * mm, 20 * mm, 40 * mm, 36 * mm, 34 * mm])
    stt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stt)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("DÉTAIL PAR CATÉGORIE", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
    head = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
            ["Catégorie", "Prévu", "Réalisé", "Écart", "Taux", "État"]]
    rows = [head]
    for c in summary["categories"]:
        if c["prevu"] == 0 and c["realise"] == 0:
            continue
        color_hex = "#EF4444" if c["level"] == "danger" else ("#F59E0B" if c["level"] == "warning" else "#10B981")
        label = {"danger": "Dépassé", "warning": "À surveiller", "ok": "OK"}[c["level"]]
        rows.append([
            Paragraph(f"<b>{_fmt(c['categorie'])}</b>", st.Cell),
            Paragraph(_fmt_fcfa(c["prevu"]), st.Cell),
            Paragraph(_fmt_fcfa(c["realise"]), st.Cell),
            Paragraph(_fmt_fcfa(c["ecart"]), st.Cell),
            Paragraph(f"{c['taux']}%", st.Cell),
            Paragraph(f'<font color="{color_hex}"><b>{label}</b></font>', st.Cell),
        ])
    bt = Table(rows, colWidths=[38 * mm, 32 * mm, 32 * mm, 32 * mm, 20 * mm, 26 * mm], repeatRows=1)
    bt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(bt)

    if summary.get("alerts"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("ALERTES BUDGÉTAIRES", st.Section))
        story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))
        for a in summary["alerts"]:
            msg = (f"<b>{_fmt(a['categorie'])}</b> — réalisé {_fmt_fcfa(a['realise'])} pour un budget de "
                  f"{_fmt_fcfa(a['prevu'])} ({a['taux']}% consommé)")
            story.append(Paragraph(msg, st.Cell))
            story.append(Spacer(1, 1.5 * mm))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def monthly_report(months):
    """Rapport comparatif mensuel (PDF, bytes) — 12 derniers mois."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=15 * mm, bottomMargin=18 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            title="Rapport comparatif mensuel",
                            author="NexFleet")
    st = _base_styles()
    story = []

    story.append(_header(st, "RAPPORT COMPARATIF MENSUEL",
                         f"NexFleet • 12 derniers mois — {datetime.now().strftime('%d/%m/%Y')}"))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("SYNTHÈSE DES 12 MOIS", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))

    total_new = sum(m["vehicles_new"] for m in months)
    total_ctrl = sum(m["controls"] for m in months)
    total_cost = sum(m["maintenance_cost"] for m in months)
    months_lbl = [m["month"] for m in months]
    costs = [m["maintenance_cost"] for m in months]
    avg_cost = total_cost / max(len(costs), 1)
    max_cost = max(costs) if costs else 0
    best_month = months_lbl[costs.index(max_cost)] if costs else "—"

    summary_rows = [
        [Paragraph("<b>Total véhicules ajoutés</b>", st.Cell), Paragraph(f"<b>{total_new}</b>", st.Cell),
         Paragraph("<b>Total contrôles</b>", st.Cell), Paragraph(f"<b>{total_ctrl}</b>", st.Cell)],
        [Paragraph("<b>Coût maintenance cumulé</b>", st.Cell), Paragraph(f"<b>{_fmt_fcfa(total_cost)}</b>", st.Cell),
         Paragraph("<b>Coût moyen mensuel</b>", st.Cell), Paragraph(f"<b>{_fmt_fcfa(avg_cost)}</b>", st.Cell)],
        [Paragraph("<b>Pic de coût</b>", st.Cell), Paragraph(f"<b>{best_month}</b>", st.Cell),
         Paragraph("<b>Coût du pic</b>", st.Cell), Paragraph(f"<b>{_fmt_fcfa(max_cost)}</b>", st.Cell)],
    ]
    stt = Table(summary_rows, colWidths=[47 * mm, 43 * mm, 47 * mm, 43 * mm])
    stt.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stt)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("DÉTAIL PAR MOIS", st.Section))
    story.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=4))

    head = [Paragraph(f"<b>{h}</b>", st.HeaderCell) for h in
            ["Mois", "Véhicules ajoutés", "Contrôles", "Coût maintenance", "Variation coût"]]
    rows = [head]
    prev = None
    for m in months:
        cost = m["maintenance_cost"]
        if prev is not None:
            if prev > 0:
                pct = (cost - prev) / prev * 100
                var = f"{'+' if pct >= 0 else ''}{pct:.1f} %"
            else:
                var = "—"
        else:
            var = "—"
        prev = cost
        rows.append([
            Paragraph(f"<b>{m['month']}</b>", st.Cell),
            Paragraph(str(m["vehicles_new"]), st.Cell),
            Paragraph(str(m["controls"]), st.Cell),
            Paragraph(_fmt_fcfa(cost), st.Cell),
            Paragraph(var, st.Cell),
        ])
    tt = Table(rows, colWidths=[30 * mm, 42 * mm, 36 * mm, 42 * mm, 30 * mm], repeatRows=1)
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#121A30")),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(tt)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
