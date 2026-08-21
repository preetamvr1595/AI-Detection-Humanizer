# ScholarShield — AI-Powered Document Intelligence & Cybersecurity Platform


Full-stack implementation covering the GM University MCA Phase 1 SRS, the
Phase 2 Software Design document, and the **ScholarShield Master PRD**
(module requirements matrix + cybersecurity architecture, Sections 3–6).




## Quick start

```bash
cd backend
pip install -r requirements.txt
bash scripts/setup_security_deps.sh        # installs & starts real ClamAV + YARA (see script)
uvicorn app.main:app --reload --port 8010
```

```bash
cd frontend
npm install
npm run dev
```

The **first account you register becomes Admin** (see the Security and
Admin analytics pages). Enable MFA from the Security panel — it's real
TOTP, scan the QR code with Google Authenticator/Authy/any RFC 6238 app.

For TLS 1.3 locally: `python3 run_tls.py` (uses the self-signed cert under
`.certs/`, generated with the same `openssl` command PRD 6.4 specifies).

## The product surface: instant Tools + full Document Scan

The home page after login is a **Tools Hub** — four paste-text-and-go tools
matching the UX of consumer products like QuillBot/Undetectable.ai/GPTZero,
each hitting a synchronous endpoint under `/api/tools/*` (no file upload,
no job polling, results in one call):

- **AI Detector** (`/tools/ai-detector`) — multi-model consensus score plus
  a sentence-by-sentence highlighted heatmap of which parts of the text
  read as most AI-like.
- **Humanizer** (`/tools/humanizer`) — rewrites AI-flagged phrasing in one
  of 4 modes (Academic/Professional/Short-form/Structural), shows a
  before/after AI-detection score comparison, and hard-guarantees no
  number, date, or name is altered (rewrites that would change a fact are
  automatically rejected and the original sentence is kept).
- **Plagiarism Checker** (`/tools/plagiarism`) — hybrid structural +
  lexical-semantic match against the reference corpus, with a full
  source-by-source breakdown.
- **Grammar & Citations** (`/tools/grammar`) — real readability formulas,
  rule-based grammar issues, and citation-format validation in one view.

Separately, **Document Scan** (`/documents`) is the full file-upload
pipeline from the PRD's Section 5 architecture diagram: real ClamAV +
YARA gating, all four analysis modules run in parallel, conditional
auto-paraphrasing, and a signed + AES-256-GCM-encrypted PDF report.

## PRD Module Requirements Matrix — implementation status

| # | Module | PRD Complexity | Status here |
|---|---|---|---|
| 1 | Document Processing | Medium | **Real.** PyMuPDF/pdfplumber/python-docx extraction. |
| 2 | AI Detector #1 (Perplexity) | High | Real signal extraction (n-gram-model perplexity proxy). Not a hosted LM — see note below. |
| 3 | AI Detector #2 (Stylometry) | High | **Real**, fully deterministic stylometric signal computation. |
| 4 | AI Detector #3 (Transformer classifier) | Very High | Heuristic family-distribution stand-in — **no GPU/model-hub access in this environment**, honestly labeled, not claimed as a trained classifier. |
| 5 | Plagiarism Detector | Very High | **Real hybrid** structural (word-shingle containment) + lexical-semantic (TF-IDF cosine) matcher against a local corpus. Production target (dense embeddings + Qdrant/Elasticsearch) needs a reachable embedding model + vector DB. |
| 6 | Plagiarism Remover / Auto-Paraphraser | Very High | **Real**, rule-based (WordNet + POS-tagged synonym substitution), with an enforced fact-preservation constraint check — not a GenAI rewrite (see note below). |
| 7 | Grammar & Readability | Medium | **Real.** Flesch/Gunning Fog/SMOG are exact published formulas; grammar checks are rule-based + real spellchecker. |
| 8 | Fact & Citation Checker | Very High | **Real structural validation** (APA/MLA/IEEE/DOI pattern detection, uncited-claim flagging). No live CrossRef/DOI truth verification — no network route to `api.crossref.org` from this environment. |
| 9 | Report Generator | Medium | **Real.** Aggregates every module, AES-256-GCM encrypted at rest, RSA-PSS signed. |

## Cybersecurity Architecture (PRD Section 6) — implementation status

| Module | PRD tech | Status here |
|---|---|---|
| Secure Upload Gateway | Isolated sandbox + MIME validation | **Real** — file-type/size gating before any processing. |
| Malware Scanning Engine | ClamAV (`clamd`) | **Real ClamAV daemon**, real INSTREAM protocol, verified against the actual EICAR test file (rejected with 422). See "On the ClamAV signature database" below. |
| Prompt-Injection / Payload Detector | YARA | **Real** — `yara-python`, your exact rule from the PRD, plus two additional rules (jailbreak phrasing, macro markers). |
| Identity & Access Management | Keycloak (OAuth2/OIDC) + JWT | RS256 JWTs with the **identical claim shape** Keycloak produces (`realm_access.roles`, `mfa_verified`), issued by a local key pair since no Keycloak realm is reachable here. Two-line swap to real Keycloak — see `app/security/auth.py`. |
| MFA | OTP/TOTP | **Real RFC 6238 TOTP** (`pyotp`), works with any standard authenticator app — not simulated. |
| Transport Encryption | TLS 1.3 | **Real** — verified handshake negotiates `TLSv1.3 / TLS_AES_256_GCM_SHA384`. |
| At-Rest Encryption & Signing | AES-256-GCM + RSA/ECDSA | **Real** — `cryptography` library, AES-256-GCM + RSA-PSS, tested round-trip and tamper-rejection. |
| Audit & Compliance Logging | Hash-chained append-only log | **Real** — every entry embeds the previous entry's SHA-256 hash; `verify_chain()` detects any DB-level tampering, tested. |

## On the ClamAV signature database

ClamAV's official CDN (`database.clamav.net`) rate-limits/blocks this
sandbox's shared IP (HTTP 429/403 — this is ClamAV's own infrastructure,
not an Anthropic restriction). Rather than mock the scanner, this
deployment runs the **real clamd daemon** with a minimal local database
(`/var/lib/clamav/local.hdb`) containing the industry-standard EICAR test
signature (published by eicar.org specifically for AV integration testing
— not real malware). Every part of the pipeline — daemon process, Unix
socket, INSTREAM protocol, reject-on-detection flow — is genuine; only the
signature *set* is reduced from ~1M+ down to 1. On a normal machine or
production server, `scripts/setup_security_deps.sh` will pull the full official
database via `freshclam` automatically, no code changes needed.

## Fixed: silent extraction failures producing meaningless scores

A real bug was reported: a fully AI-generated PDF/DOCX scored 10-20% AI
probability — badly wrong. Root cause, confirmed by reproduction:

1. **DOCX extraction only read paragraphs**, silently dropping any content
   inside tables. Assignment documents that put code/answers in table
   cells lost most of their actual content before analysis ever ran.
2. **PDF extraction had no OCR fallback.** A scanned page or a screenshot
   of code with no embedded text layer returned empty text *silently* —
   no error, no warning — and the pipeline confidently scored whatever
   fragment of real text happened to exist elsewhere (often just a title).

Both are now fixed in `app/services/extraction.py`:
- DOCX tables are walked and included (`_extract_docx_tables`).
- Every PDF page below a real-text-length threshold falls back to
  rendering the page as an image and running it through a **real
  Tesseract OCR pass** (`pytesseract` + `pdf2image`/poppler — genuinely
  installed, not simulated). This is the "Tesseract-driven OCR"
  requirement from PRD Module 1, which was previously unimplemented.
- Extraction now returns diagnostics (word count, method per page, OCR
  pages used) alongside the text. If fewer than 15 words are recovered,
  the upload is **refused with a clear explanation** instead of silently
  producing a confident-looking but meaningless score. Between 15-50
  words, the job still runs but is flagged `low_confidence_extraction`
  and both the API response and the generated PDF report show a visible
  warning banner.

Verified via reproduction test: an image-only PDF with real AI-generated
text baked into it went from **0 words extracted / meaningless default
score** to **52 words recovered via OCR / 58.9% AI-probability** — a
correct, non-trivial result on the actual content.

## On the "98% accuracy" request

I want to be direct about this rather than move past it: I cannot make
that number true by changing code, and I'm not going to claim it. A
validated accuracy figure only comes from running a detector against a
labeled ground-truth dataset (confirmed-human and confirmed-AI documents)
and measuring precision/recall — that evaluation hasn't been done here,
and this environment has no labeled benchmark to run it against. What I
*can* do, and did, is find and fix a real bug that was making the numbers
wrong for a specific document class (scanned/table-heavy files) — that's
a correctness fix, not an accuracy guarantee. If your coursework requires
a stated accuracy figure, the honest path is to build a small labeled test
set yourself (a folder of known-human and known-AI documents) and compute
precision/recall against it; `methodology_note` and the new extraction
diagnostics in every response are designed to make that evaluation
possible to set up quickly.

## On accuracy claims

No number in this codebase claims a validated accuracy rate for AI
detection, plagiarism detection, or any other module. Doing so would
require evaluating against a labeled benchmark dataset, which this
environment does not have access to. The AI Detector Suite and Plagiarism
Detector are real, deterministic, explainable pipelines producing genuine
signal — useful as decision support for a human reviewer — but they are
statistical/heuristic, not trained classifiers, and every module's
docstring says so explicitly. If you need a validated accuracy figure for
your assignment writeup, that would come from running these detectors
against a labeled corpus and computing precision/recall yourself; the
`methodology_note` field returned by each module is designed to make that
evaluation straightforward to set up.

## On the auto-paraphraser

Genuinely rule-based: WordNet synonym substitution restricted to nouns/
adjectives (POS-tagged via NLTK, verbs are deliberately excluded because
WordNet sense disambiguation for verbs is unreliable without a full word-
sense-disambiguation model, and a wrong verb swap corrupts meaning worse
than a generic noun swap). Every rewrite is checked against the original
for numbers/dates/proper-noun preservation before being accepted — if a
sentence would lose or change a factual token, the original sentence is
kept unchanged instead. This is the PRD's "100% data facts preservation,
zero structural hallucinations" constraint, enforced in code
(`verify_fact_preservation()` in `app/services/paraphraser.py`), not just
documented.

## Project structure

```
backend/
  app/
    main.py                  FastAPI entrypoint
    models.py                 SQLAlchemy models (mirrors the Phase 2 ER diagram + PRD fields)
    schemas.py                  Pydantic request/response schemas
    core/                        database session, password hashing, JWT wiring
    security/                     REAL security modules (PRD Section 6)
      malware_scanner.py           ClamAV INSTREAM client
      threat_detector.py            YARA rule compilation/matching
      rules/prompt_injection.yar     your exact YARA rule + 2 more
      encryption.py                  AES-256-GCM + RSA-PSS signing
      audit_log.py                    hash-chained audit trail
      auth.py                          RS256 JWT issuance/verification (Keycloak-shaped)
    routers/                     auth (+MFA), documents (pipeline), admin
    services/                     PRD Module 1-9 implementations
      extraction.py                 Module 1
      ai_detection.py                 Modules 2-4 (3-detector consensus)
      plagiarism.py                     Module 5 (hybrid structural+semantic)
      paraphraser.py                      Module 6
      grammar_readability.py                Module 7
      fact_citation.py                        Module 8
      report_gen.py                             Module 9
  scripts/setup_security_deps.sh      ClamAV + YARA installer
  run_tls.py                   TLS 1.3 launcher
  .certs/                      self-signed cert for local HTTPS (regenerate for prod)
  .keys/                       generated AES/RSA keys (gitignored — regenerate, don't ship)
frontend/
  src/
    pages/                     Login (+MFA), Dashboard, Report (full module breakdown), Security (MFA enrollment), Admin (+ audit chain verify)
```

## Moving to full production infrastructure

1. **Keycloak**: point `KEYCLOAK_JWKS_URL` in `app/security/auth.py` at a
   real realm's certs endpoint and switch `verify_token()` to use
   `PyJWKClient` against it (code is already structured for this swap).
2. **Full ClamAV database**: run `freshclam` on a schedule (cron) once
   deployed somewhere with unrestricted network access.
3. **Dense embeddings + Qdrant**: replace the TF-IDF layer in
   `plagiarism.py` with a sentence-transformer model + Qdrant client.
4. **Real transformer AI classifier**: fine-tune/host a RoBERTa (or
   similar) classifier and replace `detector_3_family_classifier()`'s
   internals — the JSON contract it returns doesn't need to change.
5. **PostgreSQL**: change `DATABASE_URL`; models are already
   database-agnostic SQLAlchemy.
6. **Live CrossRef/DOI verification**: implement `verify_doi_live()` in
   `fact_citation.py` with a real HTTP call once deployed somewhere that
   can reach `api.crossref.org`.
   ### Development Update
GitHub workflow and project documentation update.
