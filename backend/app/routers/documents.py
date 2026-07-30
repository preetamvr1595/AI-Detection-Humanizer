"""
Document ingestion + analysis pipeline router.

Implements the PRD Section 5 pipeline:
  File Upload -> Doc Processing -> Text Normalization
    -> [AI Detector Suite | Plagiarism Detector | Grammar/Readability | Fact/Citation]  (parallel workers entry)
    -> conditional: Plagiarism Removal Engine (if overlap exceeds threshold)
    -> Report Compilation (signed + AES-256 encrypted)
    -> Client Delivery & Dashboard Sync

Every stage is recorded in the hash-chained audit log (FR-19/FR-20).
"""
import os
import io
import hashlib
import concurrent.futures
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.security.audit_log import AuditLog
from app.security import malware_scanner, threat_detector
from app import models, schemas
from app.services import extraction, ai_detection, plagiarism, grammar_readability, fact_citation, paraphraser, report_gen

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

PLAGIARISM_PARAPHRASE_THRESHOLD = 25.0  # PRD 4.3: auto-paraphrase engine triggers on high-overlap segments


@router.post("/upload", response_model=schemas.JobOut)
async def upload_and_analyze(
    file: UploadFile = File(...),
    paraphrase_mode: str = Query(default="academic", description="academic | professional | short_form | structural"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    audit = AuditLog(db)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "docx", "txt"):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")

    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    # --- Secure Upload Gateway: REAL ClamAV daemon scan (FR-04/FR-05) ---
    try:
        scan_result = malware_scanner.scan_bytes(contents, file.filename)
    except HTTPException as e:
        audit.record(current_user.user_id, "UPLOAD_REJECTED_MALWARE", file.filename)
        raise e

    saved_name = f"{file_hash}.{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(contents)

    audit.record(current_user.user_id, "CLAMAV_SCAN", f"{file.filename}: {scan_result['status']}")

    document = models.Document(
        user_id=current_user.user_id,
        file_name=file.filename,
        file_type=ext,
        file_hash=file_hash,
        storage_uri=saved_path,
        scan_status=scan_result["status"],
        scan_engine="ClamAV 1.5.3 (local signature DB — see README)",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    job = models.AnalysisJob(doc_id=document.doc_id, status="RUNNING")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        # --- Doc Processing + Text Normalization (Module 1) ---
        extraction_result = extraction.extract_text_with_diagnostics(saved_path, ext)
        text = extraction_result["text"]
        diagnostics = extraction_result["diagnostics"]
        job.extraction_diagnostics = diagnostics
        db.commit()
        audit.record(
            current_user.user_id, "TEXT_EXTRACTED",
            f"{diagnostics['extracted_word_count']} words, methods={diagnostics['extraction_method']}, "
            f"ocr_pages={diagnostics['pages_ocr_fallback']}",
        )
        if diagnostics["low_confidence_extraction"]:
            audit.record(current_user.user_id, "LOW_CONFIDENCE_EXTRACTION_WARNING", diagnostics["warning"])

        if diagnostics["extracted_word_count"] < 15:
            # Not enough text to produce a meaningful score of any kind — refuse
            # rather than return a confident-looking but meaningless number
            # (this was the root cause of a real bug report: near-empty
            # extraction silently producing a fixed default score).
            job.status = "FAILED"
            db.commit()
            audit.record(current_user.user_id, "ANALYSIS_REFUSED_INSUFFICIENT_TEXT", str(diagnostics))
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Only {diagnostics['extracted_word_count']} words could be extracted from this document "
                    "— too little for a reliable result. If this is a scanned document, OCR was attempted "
                    f"({diagnostics['pages_ocr_fallback']} of {diagnostics['pages_total']} pages) but recovered "
                    "very little usable text. Try a higher-resolution scan or a text-based export."
                ),
            )

        # --- Prompt-Injection / Macro Threat Detector (real YARA, FR-05) ---
        yara_findings = threat_detector.detect_injection_or_macro(text)
        document.yara_findings = yara_findings
        db.commit()
        if yara_findings:
            audit.record(current_user.user_id, "YARA_FINDINGS", f"{len(yara_findings)} rule(s) matched")

        # --- Parallel worker entry: run the four analysis modules concurrently ---
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            f_ai = pool.submit(ai_detection.analyze_ai_generated, text)
            f_plag = pool.submit(plagiarism.analyze_plagiarism, text)
            f_grammar = pool.submit(grammar_readability.analyze_grammar_readability, text)
            f_fact = pool.submit(fact_citation.analyze_fact_citation, text)

            ai_result = f_ai.result()
            plag_result = f_plag.result()
            grammar_result = f_grammar.result()
            fact_result = f_fact.result()

        audit.record(current_user.user_id, "AI_DETECTION_COMPLETE", f"score={ai_result['ai_probability']}")
        audit.record(current_user.user_id, "PLAGIARISM_DETECTION_COMPLETE", f"score={plag_result['plagiarism_score']}")
        audit.record(current_user.user_id, "GRAMMAR_READABILITY_COMPLETE", "")
        audit.record(current_user.user_id, "FACT_CITATION_COMPLETE", f"claims={fact_result['claims_detected']}")

        # --- Conditional direct branching: Plagiarism Removal Engine (Module 6) ---
        paraphrase_result = None
        if plag_result["plagiarism_score"] >= PLAGIARISM_PARAPHRASE_THRESHOLD:
            paraphrase_result = paraphraser.paraphrase_text(text, mode=paraphrase_mode)
            audit.record(
                current_user.user_id, "AUTO_PARAPHRASE_TRIGGERED",
                f"mode={paraphrase_mode}, fact_preserved={paraphrase_result['fact_preservation']['preserved']}",
            )

        job.ai_score = ai_result["ai_probability"]
        job.plagiarism_score = plag_result["plagiarism_score"]
        job.fact_check_score = fact_result["citation_coverage_pct"]
        job.readability_grade = grammar_result.get("grade_level_summary") or grammar_result.get("readability", {}).get("grade_level_label")
        job.ai_detection_detail = ai_result
        job.grammar_readability_detail = grammar_result
        job.citation_detail = fact_result
        job.paraphrase_detail = paraphrase_result
        job.plagiarism_match_matrix = plag_result.get("match_matrix", [])[:200]  # cap stored matrix size
        job.status = "COMPLETE"
        job.completed_at = datetime.utcnow()
        db.commit()

        for m in plag_result["matches"]:
            db.add(models.PlagiarismResult(
                job_id=job.job_id,
                matched_source=m["matched_source"],
                similarity_score=m["similarity_score"],
                match_type=m.get("match_type"),
                segment_preview=m["segment_preview"],
            ))
        db.commit()

        # --- Report Compilation (Module 9): signed + AES-256-GCM encrypted (FR-13) ---
        report_meta = report_gen.generate_report(
            job.job_id, document.file_name, ai_result, plag_result, current_user.full_name,
            grammar_result=grammar_result, fact_result=fact_result, paraphrase_result=paraphrase_result,
            yara_findings=yara_findings, scan_status=scan_result["status"], extraction_diagnostics=diagnostics,
        )
        db.add(models.Report(
            job_id=job.job_id,
            file_uri=report_meta["file_uri"],
            signature_hash=report_meta["signature_hash"],
            rsa_signature=report_meta.get("rsa_signature"),
            aes_encrypted_path=report_meta.get("aes_encrypted_path"),
        ))
        db.commit()
        audit.record(current_user.user_id, "REPORT_GENERATED_SIGNED_ENCRYPTED", job.job_id)

    except HTTPException:
        job.status = "FAILED"
        db.commit()
        raise
    except Exception as e:
        job.status = "FAILED"
        db.commit()
        audit.record(current_user.user_id, "PIPELINE_FAILED", str(e))
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {e}")

    audit.record(current_user.user_id, "UPLOAD_AND_ANALYZE_COMPLETE", document.file_name)
    db.refresh(job)
    job.file_name = document.file_name
    return job


@router.get("/jobs", response_model=list[schemas.JobOut])
def list_jobs(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    docs = db.query(models.Document).filter(models.Document.user_id == current_user.user_id).all()
    doc_map = {d.doc_id: d.file_name for d in docs}
    doc_ids = list(doc_map.keys())
    jobs = db.query(models.AnalysisJob).filter(models.AnalysisJob.doc_id.in_(doc_ids)).order_by(models.AnalysisJob.started_at.desc()).all()
    for j in jobs:
        j.file_name = doc_map.get(j.doc_id)
    return jobs


@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    job = db.query(models.AnalysisJob).filter(models.AnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    doc = db.query(models.Document).filter(models.Document.doc_id == job.doc_id).first()
    if doc.user_id != current_user.user_id and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    job.file_name = doc.file_name
    return job


@router.get("/jobs/{job_id}/report")
def download_report(job_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    job = db.query(models.AnalysisJob).filter(models.AnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    doc = db.query(models.Document).filter(models.Document.doc_id == job.doc_id).first()
    if doc.user_id != current_user.user_id and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    report = db.query(models.Report).filter(models.Report.job_id == job_id).first()
    if not report or not os.path.exists(report.file_uri):
        raise HTTPException(status_code=404, detail="Report not available")
    AuditLog(db).record(current_user.user_id, "DOWNLOAD_REPORT", job_id)
    return FileResponse(report.file_uri, media_type="application/pdf", filename=f"ScholarShield_Report_{job_id[:8]}.pdf")
