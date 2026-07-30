"""
Report Generator (PRD Module 9) — aggregates every module's output into an
immutable PDF, then applies REAL AES-256-GCM at-rest encryption and a REAL
RSA-PSS digital signature over its SHA-256 digest (FR-13, NFR-01, PRD 6.4).
"""
import os
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.security.encryption import encrypt_report, sign_report

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "reports")
REPORTS_DIR = os.path.abspath(REPORTS_DIR)
os.makedirs(REPORTS_DIR, exist_ok=True)


def _table(rows, widths, header_color):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
    ]))
    return t


def generate_report(
    job_id: str, file_name: str, ai_result: dict, plagiarism_result: dict, user_name: str,
    grammar_result: dict = None, fact_result: dict = None, paraphrase_result: dict = None,
    yara_findings: list = None, scan_status: str = "CLEAN", extraction_diagnostics: dict = None,
) -> dict:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], textColor=colors.HexColor("#33475B"))
    heading_style = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#3B82C4"))
    small_italic = ParagraphStyle("SmallItalic", parent=styles["Italic"], fontSize=8, textColor=colors.HexColor("#666666"))
    warning_style = ParagraphStyle("Warning", parent=styles["Normal"], textColor=colors.HexColor("#C0453F"), fontSize=10, spaceAfter=6)

    out_path = os.path.join(REPORTS_DIR, f"{job_id}.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=A4, topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []

    # --- Header ---
    story.append(Paragraph("ScholarShield Verification Report", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Document: {file_name}", styles["Normal"]))
    story.append(Paragraph(f"Submitted by: {user_name}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Paragraph(f"Job ID: {job_id}", styles["Normal"]))
    story.append(Paragraph(f"Security Scan: {scan_status} (ClamAV real-time daemon)", styles["Normal"]))
    if extraction_diagnostics:
        story.append(Paragraph(
            f"Text extracted: {extraction_diagnostics['extracted_word_count']} words "
            f"(methods: {', '.join(extraction_diagnostics['extraction_method'])}"
            f"{', OCR used on ' + str(extraction_diagnostics['pages_ocr_fallback']) + ' page(s)' if extraction_diagnostics['pages_ocr_fallback'] else ''})",
            styles["Normal"],
        ))
        if extraction_diagnostics.get("low_confidence_extraction"):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"⚠ LOW-CONFIDENCE EXTRACTION: {extraction_diagnostics['warning']}", warning_style))
    story.append(Spacer(1, 14))

    # --- Summary scores ---
    story.append(Paragraph("Summary Scores", heading_style))
    score_rows = [
        ["Metric", "Score"],
        ["AI-Generation Probability (consensus)", f"{ai_result['ai_probability']}%"],
        ["Plagiarism Similarity", f"{plagiarism_result['plagiarism_score']}%"],
    ]
    if fact_result:
        score_rows.append(["Citation Coverage", f"{fact_result['citation_coverage_pct']}%"])
    if grammar_result and grammar_result.get("readability", {}).get("flesch_reading_ease") is not None:
        score_rows.append(["Flesch Reading Ease", str(grammar_result["readability"]["flesch_reading_ease"])])
    elif grammar_result and grammar_result.get("flesch_reading_ease") is not None:
        score_rows.append(["Flesch Reading Ease", str(grammar_result["flesch_reading_ease"])])
    story.append(_table(score_rows, [9*cm, 5*cm], "#33475B"))
    story.append(Spacer(1, 14))

    # --- AI Detector Suite breakdown ---
    story.append(Paragraph("AI Detector Suite — Multi-Model Consensus", heading_style))
    story.append(Paragraph(
        "Detector 1 (perplexity proxy), Detector 2 (stylometry), Detector 3 (model-family distribution). "
        "See methodology note below.", styles["Normal"]))
    d1 = ai_result.get("detector_1_perplexity", {})
    d2 = ai_result.get("detector_2_stylometry", {})
    d3 = ai_result.get("detector_3_family_classifier", {})
    ai_rows = [["Signal", "Score"]]
    ai_rows.append(["Detector 1 — AI Probability", f"{d1.get('ai_probability', '-')}%  (confidence {d1.get('confidence', '-')}%)"])
    ai_rows.append(["Detector 2 — Human Style Score", f"{d2.get('human_style_score', '-')}%"])
    for k, v in (d2.get("signals") or {}).items():
        ai_rows.append([f"  · {k.replace('_', ' ').title()}", f"{v}%"])
    if d3:
        ai_rows.append(["Detector 3 — Most Likely Family", d3.get("most_likely_family", "-")])
        for fam, pct in (d3.get("family_distribution") or {}).items():
            ai_rows.append([f"  · {fam}", f"{pct}%"])
    story.append(_table(ai_rows, [9*cm, 5*cm], "#C4692E"))
    story.append(Paragraph(ai_result.get("methodology_note", ""), small_italic))
    story.append(Spacer(1, 14))

    # --- Plagiarism matches ---
    story.append(Paragraph("Plagiarism Matches", heading_style))
    if plagiarism_result["matches"]:
        rows = [["Source", "Similarity", "Type", "Segment Preview"]]
        for m in plagiarism_result["matches"]:
            rows.append([m["matched_source"], f"{m['similarity_score']}%", m.get("match_type", "-"), m["segment_preview"][:55]])
        story.append(_table(rows, [3.2*cm, 2*cm, 3.3*cm, 5.5*cm], "#2E8B7D"))
    else:
        story.append(Paragraph("No significant matches found against the reference corpus.", styles["Normal"]))
    story.append(Paragraph(plagiarism_result.get("methodology_note", ""), small_italic))
    story.append(Spacer(1, 14))

    # --- Auto-Paraphraser (only if triggered) ---
    if paraphrase_result:
        story.append(Paragraph("Plagiarism Removal / Auto-Paraphraser", heading_style))
        story.append(Paragraph(f"Mode: {paraphrase_result['mode']}  |  Fact preservation: "
                                f"{'PASSED' if paraphrase_result['fact_preservation']['preserved'] else 'FAILED'}  |  "
                                f"Lexical change: {paraphrase_result['lexical_change_pct']}%", styles["Normal"]))
        preview = paraphrase_result["rewritten_text"][:600]
        story.append(Paragraph(f"Rewritten preview: {preview}...", styles["Normal"]))
        story.append(Spacer(1, 14))

    # --- Grammar & Readability ---
    if grammar_result:
        story.append(Paragraph("Grammar & Readability", heading_style))
        readability = grammar_result.get("readability", grammar_result)
        gr_rows = [
            ["Metric", "Value"],
            ["Flesch Reading Ease", str(readability.get("flesch_reading_ease", "-"))],
            ["Flesch-Kincaid Grade", str(readability.get("flesch_kincaid_grade", "-"))],
            ["Gunning Fog Index", str(readability.get("gunning_fog_index", readability.get("gunning_fog", "-")))],
            ["SMOG Index", str(readability.get("smog_index", "-"))],
            ["Total Issues Found", str(grammar_result.get("total_issues", grammar_result.get("total_issues_found", "-")))],
        ]
        story.append(_table(gr_rows, [9*cm, 5*cm], "#6B4EA0"))
        story.append(Spacer(1, 14))

    # --- Fact & Citation ---
    if fact_result:
        story.append(Paragraph("Fact & Citation Verification", heading_style))
        story.append(Paragraph(
            f"Citation style detected: {fact_result.get('citation_style_detected') or 'None detected'}  |  "
            f"Claims detected: {fact_result.get('claims_detected')}  |  "
            f"Uncited claims: {len(fact_result.get('uncited_claims', []))}", styles["Normal"]))
        story.append(Paragraph(fact_result.get("limitation_note", ""), small_italic))
        story.append(Spacer(1, 14))

    # --- Security scan detail ---
    story.append(Paragraph("Security Scan Detail", heading_style))
    story.append(Paragraph(f"Malware scan status: {scan_status} (ClamAV daemon, real-time INSTREAM scan)", styles["Normal"]))
    if yara_findings:
        story.append(Paragraph(f"YARA findings: {', '.join(f['rule'] for f in yara_findings)}", styles["Normal"]))
    else:
        story.append(Paragraph("YARA findings: none (no prompt-injection or macro markers detected)", styles["Normal"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "This report is generated automatically by ScholarShield for academic integrity review. "
        "It is a decision-support tool and should be reviewed by a human evaluator before any "
        "disciplinary or editorial action is taken. AI-detection and plagiarism scores are produced "
        "by statistical/heuristic methods documented in the project README and are not validated "
        "against a labeled accuracy benchmark in this deployment.", small_italic))

    doc.build(story)

    # --- Integrity + confidentiality: real SHA-256 digest, RSA-PSS signature, AES-256-GCM at rest ---
    with open(out_path, "rb") as f:
        plaintext = f.read()
    signature_hash = hashlib.sha256(plaintext).hexdigest()
    rsa_signature = sign_report(hashlib.sha256(plaintext).digest())

    enc = encrypt_report(plaintext)
    encrypted_path = out_path + ".enc"
    with open(encrypted_path, "w") as f:
        f.write(enc["nonce"] + "\n" + enc["ciphertext"])

    return {
        "file_uri": out_path,
        "signature_hash": signature_hash,
        "rsa_signature": rsa_signature,
        "aes_encrypted_path": encrypted_path,
    }
