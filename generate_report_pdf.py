#!/usr/bin/env python3
"""
generate_report_pdf.py -- Generates the comprehensive ME361 Digital Machining Twin Project Report (PDF).
"""
import os
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748b'))
        if self._pageNumber > 1:
            self.drawString(54, 750, 'ME361 Digital Machining Twin — Project Status & Validation Report')
            self.setStrokeColor(colors.HexColor('#cbd5e1'))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)
        page_text = f'Page {self._pageNumber} of {page_count}'
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, 'ME361 Manufacturing Processes — Digital Twin Lab Submission')
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)
        self.restoreState()

def build_pdf(filename="ME361_Digital_Machining_Twin_Report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0369a1'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=12,
        spaceAfter=3
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )
    table_cell_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    story = []

    # Title Banner
    story.append(Paragraph("ME361 DIGITAL MACHINING TWIN", title_style))
    story.append(Paragraph("Orthogonal Cutting Physics Engine, Empirical Calibration Pipeline & Real-Time Twin Dashboard", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=10))

    # Meta Info Table
    meta_data = [
        [
            Paragraph("<b>Author:</b> Kushagra Chandra", table_cell),
            Paragraph("<b>Course:</b> ME361 (Manufacturing Processes)", table_cell),
            Paragraph("<b>Phase:</b> External-Data & Prototype Release", table_cell)
        ],
        [
            Paragraph("<b>Repository:</b> kushagrachandra05/ME361_Digital_Machining_Twin", table_cell),
            Paragraph("<b>Status:</b> Fully Operational (Python + Web App)", table_cell),
            Paragraph("<b>Date:</b> October 2026", table_cell)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[180, 160, 164])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # 1. Executive Summary & Locked Scope
    story.append(Paragraph("1. Executive Summary & Locked Scope", h1_style))
    story.append(Paragraph(
        "This project delivers a complete Digital Machining Twin developed under strictly locked academic scope: "
        "<b>pure orthogonal cutting, single shear plane (Lecture-2 slides), and steady-state cutting</b>. "
        "The twin accepts user-specified cutting speed <i>V<sub>c</sub></i>, uncut chip thickness <i>t</i>, and workpiece shear/yield strength "
        "<i>&tau;<sub>s</sub></i> / <i>&sigma;<sub>y</sub></i>, alongside baseline tool assumptions (rake angle <i>&gamma;<sub>0</sub></i>, friction <i>&mu;</i>, "
        "and width of cut <i>w</i>). It outputs cutting force <i>P<sub>z</sub></i>, thrust force <i>P<sub>xy</sub></i>, resultant <i>R</i>, "
        "shear angle <i>&beta;</i>, chip thickness <i>t<sub>c</sub></i>, and specific cutting pressure <i>k<sub>c</sub></i>, accompanied by an interactive kinematic animation "
        "and real-time streaming telemetry feed with CSV export capabilities.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Strict Non-Extensions (By Locked Specification):</b> Built-up edge (BUE), thermal softening fields, tool flank wear contact, "
        "serrated chip segmentation, and within-run transients are rigorously excluded from the fundamental slide model. "
        "All parameters remain steady within each individual machining run.",
        body_style
    ))

    # 2. Mathematical Formulation
    story.append(Paragraph("2. Mathematical Formulation (Lecture 2 Single Shear Plane)", h1_style))
    story.append(Paragraph(
        "The core physics module (<font face='Courier'>orthocut.py</font>) directly translates the analytical formulation from Lecture 2:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Ernst-Merchant Shear Plane Angle:</b> &beta; = &pi;/4 + &gamma;<sub>0</sub>/2 &minus; &eta;/2, where &eta; = arctan(&mu;).", bullet_style))
    story.append(Paragraph("&bull; <b>Shear Area & Force:</b> A<sub>s</sub> = (w &middot; t) / sin &beta;, &nbsp;&nbsp; P<sub>s</sub> = &tau;<sub>s</sub> &middot; A<sub>s</sub> = (&tau;<sub>s</sub> &middot; w &middot; t) / sin &beta;.", bullet_style))
    story.append(Paragraph("&bull; <b>Resultant Cutting Force:</b> R = P<sub>s</sub> / cos(&beta; + &eta; &minus; &gamma;<sub>0</sub>).", bullet_style))
    story.append(Paragraph("&bull; <b>Component Projections:</b> P<sub>z</sub> = R cos(&eta; &minus; &gamma;<sub>0</sub>), &nbsp;&nbsp; P<sub>xy</sub> = R sin(&eta; &minus; &gamma;<sub>0</sub>) (with orthogonal transverse force = 0).", bullet_style))
    story.append(Paragraph("&bull; <b>Kinematics:</b> Chip ratio r = t / t<sub>c</sub> = sin &beta; / cos(&beta; &minus; &gamma;<sub>0</sub>), &nbsp; chip velocity V<sub>chip</sub> = r &middot; V<sub>c</sub>, &nbsp; shear velocity V<sub>s</sub> = V<sub>c</sub> cos &gamma;<sub>0</sub> / cos(&beta; &minus; &gamma;<sub>0</sub>).", bullet_style))
    story.append(Paragraph("&bull; <b>Material Fallback:</b> &tau;<sub>s</sub> = &sigma;<sub>y</sub> / &radic;3 (von Mises) or &sigma;<sub>y</sub> / 2 (Tresca).", bullet_style))

    # Visual Figure
    if os.path.exists("report_figures.png"):
        story.append(Spacer(1, 6))
        story.append(Image("report_figures.png", width=6.8*inch, height=2.85*inch))
        story.append(Paragraph("<b>Figure 1:</b> (Left) Force vs. uncut chip thickness showcasing linear slopes and positive edge ploughing intercepts across ETH Ck45 and Agmell 316L. (Right) Merchant circle vector decomposition implemented in the digital twin.", subtitle_style))
        story.append(Spacer(1, 6))

    # 3. External Experimental Datasets & Ingestion Pipeline
    story.append(Paragraph("3. External Experimental Datasets & Ingestion Pipeline", h1_style))
    story.append(Paragraph(
        "A critical milestone of this phase was validating the pure slide model against real experimental orthogonal datasets:",
        body_style
    ))
    story.append(Paragraph(
        "<b>1. ETH Zürich IWF Database (Klippel et al., arXiv:2209.04197 / IJAMT 2024):</b> Comprises 519 high-precision dry orthogonal tube cuts "
        "on a CNC lathe for Ck45 (AISI 1045 carbon steel) and Ti6Al4V over cutting speeds <i>v<sub>c</sub></i> = 10&ndash;500 m/min, feeds <i>f</i> = 0.01&ndash;0.40 mm/rev, "
        "and edge radius <i>r<sub>n</sub></i> &approx; 38 &mu;m at rake &gamma;<sub>0</sub> = 0&deg;. All rows were systematically parsed into "
        "<font face='Courier'>data/eth_full.csv</font> (232 Ck45, 287 Ti6Al4V). The ingestion pipeline (<font face='Courier'>datapipe.py</font>) applies strict "
        "scope filtering: cuts below 150 m/min for Ck45 were dropped due to severe BUE formation, leaving 95 high-speed, continuous-chip cuts for calibration.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2. Lund University 316L Dataset (Agmell et al., Procedia CIRP 58 (2017) 13&ndash;18):</b> Semi-automated extraction using the newly developed "
        "<font face='Courier'>lit_tools.py</font> utility captured experimental orthogonal force data for AISI 316L stainless steel at <i>v<sub>c</sub></i> = 125 m/min "
        "(uncut thicknesses <i>t</i> = 0.1, 0.2, 0.3 mm) into <font face='Courier'>data/lit_316L.csv</font>.",
        body_style
    ))

    # 4. Calibration Engine & Phenomenological Findings
    story.append(Paragraph("4. Calibration Engine & Empirical Findings", h1_style))
    story.append(Paragraph(
        "Fitting the pure slide equations against the ETH database exposed two fundamental physical realities:",
        body_style
    ))
    story.append(Paragraph(
        "1. <b>Non-Zero Force Intercepts (Edge Ploughing):</b> The pure slide model predicts zero force at <i>t</i> = 0. Real data exhibits substantial "
        "positive intercepts (<i>P<sub>z</sub></i> &approx; 13&ndash;15 N/mm, <i>P<sub>xy</sub></i> &approx; 100 N/mm). This stems from the tool hone (<i>r<sub>n</sub></i> &approx; 38 &mu;m) "
        "causing ploughing and rubbing at the flank. Adding calibrated edge terms <i>K<sub>e,z</sub></i> and <i>K<sub>e,xy</sub></i> directly resolves this.",
        body_style
    ))
    story.append(Paragraph(
        "2. <b>Apparent Friction Scale Effect:</b> Measured ratio <i>F/N</i> drops dramatically from ~1.85 at <i>t</i> = 0.01 mm down to ~0.50 at <i>t</i> = 0.20 mm. "
        "A power-law correction <i>&mu;</i>(<i>t</i>) = &mu;<sub>ref</sub> &middot; (<i>t</i> / <i>t</i><sub>ref</sub>)<sup>&minus;n<sub>&mu;</sub></sup> accounts for this size effect.",
        body_style
    ))
    story.append(Paragraph(
        "3. <b>Plastic Strain Hardening (&tau;<sub>k</sub> Multiplier):</b> Material along the shear plane experiences severe plastic strain (&gamma; &approx; 2&ndash;3). "
        "Initial yield stress (&tau;<sub>s</sub> = &sigma;<sub>y</sub>/&radic;3) significantly under-predicts cutting forces for strain-hardening steels. "
        "The calibrated multiplier &tau;<sub>k</sub> matches Johnson-Cook flow stress at true shear-plane strain.",
        body_style
    ))

    # Calibration Table
    calib_table_data = [
        [
            Paragraph("Material", table_cell_header),
            Paragraph("In-Scope Rows", table_cell_header),
            Paragraph("&tau;<sub>s</sub> (Yield)", table_cell_header),
            Paragraph("Fitted &mu;", table_cell_header),
            Paragraph("&tau;<sub>k</sub> Multiplier", table_cell_header),
            Paragraph("Edge K<sub>e,z</sub>", table_cell_header),
            Paragraph("Size n<sub>&mu;</sub>", table_cell_header),
            Paragraph("Baseline MAPE (Pz/Pxy)", table_cell_header),
            Paragraph("Calibrated MAPE (Pz/Pxy)", table_cell_header)
        ],
        [
            Paragraph("<b>Ck45</b> (Carbon Steel)", table_cell),
            Paragraph("95 (vc &ge; 150)", table_cell),
            Paragraph("242.5 MPa", table_cell),
            Paragraph("0.877", table_cell),
            Paragraph("2.663", table_cell),
            Paragraph("13.2 N/mm", table_cell),
            Paragraph("0.266", table_cell),
            Paragraph("28.4% / 37.1%", table_cell),
            Paragraph("<b>6.8% / 8.2%</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>Ti6Al4V</b> (Titanium)", table_cell),
            Paragraph("273 (All speeds)", table_cell),
            Paragraph("501.7 MPa", table_cell),
            Paragraph("0.766", table_cell),
            Paragraph("0.888", table_cell),
            Paragraph("15.3 N/mm", table_cell),
            Paragraph("0.419", table_cell),
            Paragraph("17.2% / 41.5%", table_cell),
            Paragraph("<b>7.1% / 7.8%</b>", table_cell_bold)
        ],
        [
            Paragraph("<b>SS316L</b> (Provisional)", table_cell),
            Paragraph("Analytical / JC", table_cell),
            Paragraph("176.1 MPa", table_cell),
            Paragraph("0.877 (from Ck45)", table_cell),
            Paragraph("5.439 (JC Model)", table_cell),
            Paragraph("13.2 N/mm", table_cell),
            Paragraph("0.266", table_cell),
            Paragraph("N/A (Provisional)", table_cell),
            Paragraph("Ready for Lab Test", table_cell)
        ]
    ]
    t_calib = Table(calib_table_data, colWidths=[68, 55, 52, 45, 52, 50, 42, 70, 70])
    t_calib.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_calib)
    story.append(Spacer(1, 10))

    # 5. Held-Out Literature Validation & Option B Justification
    story.append(Paragraph("5. Held-Out Literature Validation & Option B Justification", h1_style))
    story.append(Paragraph(
        "Using <font face='Courier'>holdout_316l.py</font> and §6 of <font face='Courier'>04_external_data_validation.ipynb</font>, we executed a blind held-out evaluation "
        "of our provisional SS316L model against the experimental Agmell 2017 points (<i>v<sub>c</sub></i> = 125 m/min):",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Pure Slide Model Baseline:</b> MAPE <i>P<sub>z</sub></i> = 134%, MAPE <i>P<sub>xy</sub></i> = 430%.", bullet_style))
    story.append(Paragraph("&bull; <b>Corrected Provisional Model:</b> MAPE <i>P<sub>z</sub></i> = 115%, MAPE <i>P<sub>xy</sub></i> = 291%.", bullet_style))
    story.append(Paragraph(
        "<b>Option B Engineering Decision:</b> The provisional model predicts forces approximately 2&times; higher than Agmell's measured values. "
        "A rigorous physical audit explains why: Agmell's tests utilized commercial CNMG120408 inserts (longitudinal turning with &kappa;<sub>r</sub> = 95&deg; and positive chip-breaker rake), "
        "whereas our provisional model assumed &gamma;<sub>0</sub> = 0&deg; and transferred friction from Ck45. "
        "Under <b>Option B</b>, we strictly refuse to over-fit or force-calibrate on 3 quasi-orthogonal literature points with unmeasured insert rake. "
        "Instead, we preserve our pure theoretical model and retain the instructor's forthcoming SS316L tube data as the definitive one-shot blind benchmark.",
        body_style
    ))

    # 6. Assumption-by-Assumption Justification Matrix
    story.append(Paragraph("6. Assumption-by-Assumption Justification Matrix", h1_style))
    story.append(Paragraph(
        "Every simplifying assumption from the Lecture 2 slides has been documented, physically justified, and accounted for in the digital twin:",
        body_style
    ))

    matrix_data = [
        [
            Paragraph("Slide Assumption", table_cell_header),
            Paragraph("Physical Reality (Data)", table_cell_header),
            Paragraph("Digital Twin Handling", table_cell_header),
            Paragraph("Scope Status", table_cell_header)
        ],
        [
            Paragraph("<b>1. Perfectly sharp tool</b> (rn = 0, no flank contact)", table_cell),
            Paragraph("Real tools have finite hone (rn &approx; 38 &mu;m), producing non-zero force at t &rarr; 0.", table_cell),
            Paragraph("Calibrated edge force terms Ke_z & Ke_xy added when corrections enabled.", table_cell),
            Paragraph("CORRECTED", table_cell_bold)
        ],
        [
            Paragraph("<b>2. Constant friction &mu;</b> on rake face", table_cell),
            Paragraph("Apparent &mu; drops from ~1.8 to ~0.5 as t increases from 0.01 to 0.20 mm.", table_cell),
            Paragraph("Fitted thickness sensitivity n_&mu; (&mu; &prop; t<sup>&minus;n</sup>) corrects scale effect.", table_cell),
            Paragraph("CORRECTED", table_cell_bold)
        ],
        [
            Paragraph("<b>3. Shear strength &tau;<sub>s</sub> = &sigma;<sub>y</sub>/&radic;3</b>", table_cell),
            Paragraph("Severe plastic shear strain (&gamma; &approx; 2&ndash;3) causes extensive work-hardening.", table_cell),
            Paragraph("&tau;<sub>k</sub> flow stress multiplier calibrated to true shear strain.", table_cell),
            Paragraph("CORRECTED", table_cell_bold)
        ],
        [
            Paragraph("<b>4. Continuous chip formation</b>", table_cell),
            Paragraph("Ti6Al4V exhibits shear-banding/segmentation; Ck45 is continuous above 150 m/min.", table_cell),
            Paragraph("Ck45 serves as continuous-chip baseline; Ti6Al4V documented as violation.", table_cell),
            Paragraph("IN-SCOPE", table_cell_bold)
        ],
        [
            Paragraph("<b>5. No Built-Up Edge (BUE)</b>", table_cell),
            Paragraph("Severe BUE occurs in Ck45 below 150 m/min, altering effective rake geometry.", table_cell),
            Paragraph("All BUE-suspect rows dropped by datapipe.apply_scope with logged reasons.", table_cell),
            Paragraph("FILTERED OUT", table_cell_bold)
        ],
        [
            Paragraph("<b>6. Isothermal cutting</b> (no thermal fields)", table_cell),
            Paragraph("High speeds cause adiabatic thermal softening, reducing cutting resistance.", table_cell),
            Paragraph("Speed terms c_rate kept OFF by default to preserve locked slide scope.", table_cell),
            Paragraph("LOCKED SCOPE", table_cell_bold)
        ],
        [
            Paragraph("<b>7. Steady-state within a run</b>", table_cell),
            Paragraph("Forces reach steady plateau after initial ~1&ndash;2 ms engagement.", table_cell),
            Paragraph("Forces remain constant across time; live feed demonstrates steady state.", table_cell),
            Paragraph("LOCKED SCOPE", table_cell_bold)
        ]
    ]
    t_mat = Table(matrix_data, colWidths=[105, 135, 184, 80])
    t_mat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_mat)
    story.append(Spacer(1, 10))

    # 7. Deliverables & Web Twin Features
    story.append(Paragraph("7. Completed Deliverables & Interactive Web Twin", h1_style))
    story.append(Paragraph(
        "All required software artifacts are implemented, verified, and ready for deployment:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Interactive Web Twin (<font face='Courier'>web/</font>):</b> Modern, zero-dependency browser application featuring animated kinematic chip flow, live dynamic Merchant circle, real-time oscilloscope chart, streaming tabular telemetry, CSV log exporter, calibrated preset selector, master correction toggles, and modal justification table.", bullet_style))
    story.append(Paragraph("&bull; <b>Python Core Physics & Animation:</b> <font face='Courier'>orthocut.py</font> and <font face='Courier'>twin_anim.py</font> supporting CLI, scriptable presets, and animated MP4/GIF export.", bullet_style))
    story.append(Paragraph("&bull; <b>Data Utilities:</b> <font face='Courier'>datapipe.py</font> (schema standardization and scope filtering), <font face='Courier'>calibrate.py</font> (empirical fitting engine), and <font face='Courier'>lit_tools.py</font> (semi-automated literature data ingestion).", bullet_style))
    story.append(Paragraph("&bull; <b>Notebook Trajectory:</b> Notebooks 01 (Physics Core), 02 (Animation Prototype), 03 (Synthetic Calibration Demo), and 04 (External Data Validation on full ETH and Lund datasets).", bullet_style))

    # 8. Next Steps
    story.append(Paragraph("8. Final Project Milestone (Awaiting Instructor Data)", h1_style))
    story.append(Paragraph(
        "Upon receipt of the instructor's SS316L orthogonal tube test data and batch mill certificate:",
        body_style
    ))
    story.append(Paragraph("1. Update <i>&sigma;<sub>y</sub></i> with the mill certificate value (replacing the provisional 305 MPa placeholder).", bullet_style))
    story.append(Paragraph("2. Scale <i>K<sub>e,z</sub></i> and set <i>&gamma;<sub>0</sub></i> according to the exact lab insert geometry provided.", bullet_style))
    story.append(Paragraph("3. Execute a single-shot, blind held-out evaluation against the instructor's test cuts (strictly without re-tuning).", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report successfully compiled to {filename}")

if __name__ == '__main__':
    build_pdf()
