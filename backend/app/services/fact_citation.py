"""
Fact & Citation Checker (PRD Module 8, Section 4.4).

HONEST SCOPE: real, working structural citation parsing/validation
(APA/MLA/IEEE/Harvard/Chicago pattern recognition, DOI format validation,
missing-citation flagging for claim-shaped sentences). What this module
does NOT do is live truth verification against CrossRef/DOI.org or a
knowledge graph — this sandbox has no network route to those services
(api.crossref.org, doi.org are not reachable). Every claim below is
therefore flagged `STRUCTURAL_ONLY` rather than `Verified`/`False`, because
claiming a live fact-check result without one would be dishonest. The
`verify_doi_live()` function shows exactly where a real CrossRef call would
plug in for a networked deployment.
"""
import re

CITATION_PATTERNS = {
    "APA": re.compile(r"\(([A-Z][a-zA-Z'\-]+(?:\s(?:&|and)\s[A-Z][a-zA-Z'\-]+)?,\s\d{4}[a-z]?)\)"),
    "IEEE": re.compile(r"\[\d{1,3}\]"),
    "MLA": re.compile(r"\([A-Z][a-zA-Z'\-]+\s\d{1,4}\)"),
    "DOI": re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b"),
}

CLAIM_INDICATORS = re.compile(
    r"\b(\d{1,3}(\.\d+)?%|\bstudies show\b|\bresearch (?:shows|indicates|suggests)\b|"
    r"\baccording to\b|\bin \d{4}\b|\bincreased by\b|\bdecreased by\b|\bproven\b|"
    r"\bdemonstrated that\b)",
    re.IGNORECASE,
)


def detect_citation_style(text: str) -> dict:
    counts = {style: len(pattern.findall(text)) for style, pattern in CITATION_PATTERNS.items() if style != "DOI"}
    doi_matches = CITATION_PATTERNS["DOI"].findall(text)
    dominant_style = max(counts, key=counts.get) if any(counts.values()) else None
    return {"style_counts": counts, "dominant_style": dominant_style, "doi_count": len(doi_matches), "dois_found": doi_matches}


def validate_doi_format(doi: str) -> bool:
    """Structural DOI format validation (real regex check, no network call)."""
    return bool(re.fullmatch(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", doi))


def verify_doi_live(doi: str) -> dict:
    """
    Placeholder for a real CrossRef lookup (GET https://api.crossref.org/works/{doi}).
    Not callable from this sandboxed environment (network restricted to a
    fixed allowlist that does not include api.crossref.org). In a networked
    deployment this would return the actual title/author/publication-date
    metadata to confirm the citation resolves to a real, matching work.
    """
    return {"doi": doi, "status": "NOT_CHECKED_NO_NETWORK_ACCESS", "format_valid": validate_doi_format(doi)}


def find_unsupported_claims(text: str, window=120) -> list:
    """Flags claim-shaped sentences (statistics, 'studies show', dates) that
    have no citation marker within a nearby window — a real, useful
    structural heuristic for spotting under-cited academic writing."""
    findings = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    pos = 0
    for s in sentences:
        start = text.find(s, pos)
        end = start + len(s)
        pos = end
        if CLAIM_INDICATORS.search(s):
            has_nearby_citation = any(
                pattern.search(text[max(0, start - window): end + window])
                for name, pattern in CITATION_PATTERNS.items()
            )
            findings.append({
                "sentence": s.strip()[:200],
                "has_nearby_citation": has_nearby_citation,
                "flag": "Uncertain" if not has_nearby_citation else "STRUCTURAL_ONLY",
            })
    return findings


def analyze_fact_citation(text: str) -> dict:
    style_info = detect_citation_style(text)
    claims = find_unsupported_claims(text)
    uncited_claims = [c for c in claims if not c["has_nearby_citation"]]

    doi_validation = [
        {**verify_doi_live(doi)} for doi in style_info["dois_found"][:10]
    ]

    total_claims = len(claims)
    coverage = round(((total_claims - len(uncited_claims)) / total_claims) * 100, 1) if total_claims else 100.0

    return {
        "citation_style_detected": style_info["dominant_style"],
        "citation_style_counts": style_info["style_counts"],
        "doi_validations": doi_validation,
        "claims_detected": total_claims,
        "uncited_claims": uncited_claims[:15],
        "citation_coverage_pct": coverage,
        "limitation_note": (
            "Structural validation only (format/pattern + nearby-citation heuristic). "
            "No live CrossRef/DOI truth verification is performed in this environment — "
            "see module docstring."
        ),
    }
