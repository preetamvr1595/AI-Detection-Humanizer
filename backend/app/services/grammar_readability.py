"""
Grammar & Readability Checker (PRD Module 7, FR unspecified numbered but
covered under Section 4.4). Real, formula-based readability scoring (Flesch
Reading Ease, Flesch-Kincaid Grade, Gunning Fog, SMOG) — these are public
domain linguistic formulas computed directly from the text, not an external
API call, so there is no network dependency and no accuracy caveat needed
for this half of the module.

Grammar correction itself (the PRD's "Light Model" GenAI rewrite) is
implemented here as a real spell-checker (pyspellchecker, a Levenshtein-
distance dictionary lookup — genuinely functional, not a stub) plus a set
of explainable rule-based structural checks (double spacing, repeated
words, run-on sentences, passive-voice density). A full contextual grammar
model (e.g. LanguageTool's grammar engine) would need a ~200MB local Java
service or a hosted API neither of which are available here; the rule-based
layer below catches a real, useful subset of issues rather than mocking the
full feature.
"""
import re
import textstat
from spellchecker import SpellChecker

_spell = SpellChecker()


def _tokenize_words(text):
    return re.findall(r"[A-Za-z']+", text)


def check_spelling(text: str, max_report=25) -> list:
    words = _tokenize_words(text)
    candidates = {w.lower() for w in words if w.isalpha() and len(w) > 2}
    misspelled = _spell.unknown(candidates)
    findings = []
    for w in list(misspelled)[:max_report]:
        suggestion = _spell.correction(w)
        if suggestion and suggestion != w:
            findings.append({"word": w, "suggestion": suggestion})
    return findings


def check_structural_issues(text: str) -> list:
    issues = []

    for m in re.finditer(r"\b(\w+)\s+\1\b", text, flags=re.IGNORECASE):
        issues.append({"type": "repeated_word", "detail": f"Repeated word: '{m.group(1)}'", "position": m.start()})

    for m in re.finditer(r"  +", text):
        issues.append({"type": "double_space", "detail": "Multiple consecutive spaces", "position": m.start()})

    for m in re.finditer(r"\s([,.;:!?])", text):
        issues.append({"type": "spacing_before_punctuation", "detail": f"Space before '{m.group(1)}'", "position": m.start()})

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for s in sentences:
        wc = len(s.split())
        if wc > 45:
            issues.append({"type": "run_on_sentence", "detail": f"Sentence has {wc} words — consider splitting", "position": None})

    passive_markers = len(re.findall(r"\b(is|are|was|were|been|being|be)\s+\w+ed\b", text, flags=re.IGNORECASE))
    total_sentences = max(1, len(sentences))
    passive_ratio = passive_markers / total_sentences
    if passive_ratio > 0.35:
        issues.append({"type": "passive_voice_density", "detail": f"High passive-voice usage ({round(passive_ratio*100)}% of sentences)", "position": None})

    return issues[:50]


def analyze_grammar_readability(text: str) -> dict:
    if not text or len(text.split()) < 5:
        return {
            "flesch_reading_ease": None, "flesch_kincaid_grade": None,
            "gunning_fog": None, "smog_index": None, "grade_level_summary": "Insufficient text",
            "spelling_issues": [], "structural_issues": [], "total_issues": 0,
        }

    spelling = check_spelling(text)
    structural = check_structural_issues(text)

    flesch = textstat.flesch_reading_ease(text)
    fk_grade = textstat.flesch_kincaid_grade(text)
    fog = textstat.gunning_fog(text)
    smog = textstat.smog_index(text)

    if flesch >= 70:
        grade_summary = "Easy to read (general audience)"
    elif flesch >= 50:
        grade_summary = "Moderately difficult (high school–college level)"
    else:
        grade_summary = "Difficult (college/graduate/technical level)"

    return {
        "flesch_reading_ease": round(flesch, 1),
        "flesch_kincaid_grade": round(fk_grade, 1),
        "gunning_fog": round(fog, 1),
        "smog_index": round(smog, 1),
        "grade_level_summary": grade_summary,
        "spelling_issues": spelling,
        "structural_issues": structural,
        "total_issues": len(spelling) + len(structural),
    }
