"""
Prompt-Injection / Payload Detector (FR-05) — real YARA rule compilation and
matching, per PRD Section 6.3. This is a second detection layer beyond
ClamAV signature scanning: it inspects *extracted document text* for
indirect prompt-injection strings, jailbreak phrasing, and embedded macro
markers that a pure antivirus signature scan would not catch.
"""
import os
import yara

RULES_PATH = os.path.join(os.path.dirname(__file__), "rules", "prompt_injection.yar")
_compiled = None


def _get_rules():
    global _compiled
    if _compiled is None:
        _compiled = yara.compile(filepath=RULES_PATH)
    return _compiled


def detect_injection_or_macro(extracted_text: str) -> list:
    """
    Runs compiled YARA rules against normalized document text.
    Returns a list of {"rule": str, "severity": str} — empty list = clean.
    """
    if not extracted_text:
        return []
    rules = _get_rules()
    matches = rules.match(data=extracted_text.encode("utf-8", errors="ignore"))
    findings = []
    for m in matches:
        severity = m.meta.get("severity", "unknown") if hasattr(m, "meta") else "unknown"
        findings.append({"rule": m.rule, "severity": severity})
    return findings
