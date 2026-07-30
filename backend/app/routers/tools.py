"""
Instant "tools" endpoints — the product-facing surface real users of a
QuillBot/Undetectable.ai-style site expect: paste text, get an answer back
in one call, no file upload or job polling required. These reuse the exact
same PRD Module 2-8 service implementations as the document pipeline, just
exposed as immediate, stateless calls over raw text.
"""
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.security.audit_log import AuditLog
from app.security import threat_detector
from app import models
from app.services import ai_detection, plagiarism, grammar_readability, fact_citation, paraphraser

router = APIRouter(prefix="/api/tools", tags=["tools"])

MIN_WORDS = 15
MAX_CHARS = 50_000


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)


class HumanizeIn(TextIn):
    mode: str = "academic"  # academic | professional | short_form | structural


def _check_length(text: str):
    words = len(re.findall(r"\S+", text))
    if words < MIN_WORDS:
        raise HTTPException(status_code=400, detail=f"Please provide at least {MIN_WORDS} words for a reliable result.")
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=400, detail="Text is too long for a single request.")


@router.post("/detect-ai")
def detect_ai(payload: TextIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _check_length(payload.text)
    result = ai_detection.analyze_ai_generated(payload.text, include_sentence_breakdown=True)
    AuditLog(db).record(current_user.user_id, "TOOL_DETECT_AI", f"{len(payload.text)} chars")
    return result


@router.post("/humanize")
def humanize(payload: HumanizeIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _check_length(payload.text)
    before = ai_detection.analyze_ai_generated(payload.text)
    result = paraphraser.paraphrase_text(payload.text, mode=payload.mode)
    after = ai_detection.analyze_ai_generated(result["rewritten_text"])

    result["ai_probability_before"] = before["ai_probability"]
    result["ai_probability_after"] = after["ai_probability"]
    result["ai_probability_delta"] = round(before["ai_probability"] - after["ai_probability"], 1)

    AuditLog(db).record(
        current_user.user_id, "TOOL_HUMANIZE",
        f"mode={payload.mode}, delta={result['ai_probability_delta']}",
    )
    return result


@router.post("/check-plagiarism")
def check_plagiarism(payload: TextIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _check_length(payload.text)
    result = plagiarism.analyze_plagiarism(payload.text)
    AuditLog(db).record(current_user.user_id, "TOOL_CHECK_PLAGIARISM", f"score={result['plagiarism_score']}")
    return result


@router.post("/grammar-check")
def grammar_check(payload: TextIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _check_length(payload.text)
    result = grammar_readability.analyze_grammar_readability(payload.text)
    AuditLog(db).record(current_user.user_id, "TOOL_GRAMMAR_CHECK", "")
    return result


@router.post("/citation-check")
def citation_check(payload: TextIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    _check_length(payload.text)
    result = fact_citation.analyze_fact_citation(payload.text)
    AuditLog(db).record(current_user.user_id, "TOOL_CITATION_CHECK", "")
    return result


@router.post("/security-scan-text")
def security_scan_text(payload: TextIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Runs the real YARA prompt-injection/macro detector directly against pasted text."""
    findings = threat_detector.detect_injection_or_macro(payload.text)
    AuditLog(db).record(current_user.user_id, "TOOL_SECURITY_SCAN_TEXT", f"{len(findings)} findings")
    return {"findings": findings, "clean": len(findings) == 0}


@router.post("/full-check")
def full_check(payload: HumanizeIn, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Runs every module at once against pasted text — the 'all-in-one' scan
    view, mirroring the document pipeline but for instant text input."""
    _check_length(payload.text)
    ai_result = ai_detection.analyze_ai_generated(payload.text)
    plag_result = plagiarism.analyze_plagiarism(payload.text)
    grammar_result = grammar_readability.analyze_grammar_readability(payload.text)
    fact_result = fact_citation.analyze_fact_citation(payload.text)
    yara_findings = threat_detector.detect_injection_or_macro(payload.text)

    AuditLog(db).record(current_user.user_id, "TOOL_FULL_CHECK", f"ai={ai_result['ai_probability']}")
    return {
        "ai_detection": ai_result,
        "plagiarism": plag_result,
        "grammar_readability": grammar_result,
        "citation": fact_result,
        "security": {"findings": yara_findings, "clean": len(yara_findings) == 0},
    }
