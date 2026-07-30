"""
Plagiarism Removal / Auto-Paraphraser (PRD Module 6, Section 4.3).

Production target: a GenAI rewrite model performing fact-preserving
paraphrasing. This sandbox has no reachable LLM API to call for genuine
generative rewriting (Claude/GPT API calls from inside a user-facing demo
pipeline would also be a questionable architecture — paraphrasing student
submissions with a live LLM call raises its own academic-integrity
questions). What ships here is a REAL, deterministic, rule-based rewriter:

  - WordNet-based synonym substitution (genuine synsets, not a stub)
  - Clause/sentence reordering for conjunction-joined sentences
  - Sentence-opener variation

CONSTRAINT ANCHOR (per PRD 4.3 — "100% data facts preservation, zero
structural hallucinations"): before/after every rewrite, this module
extracts numbers, dates, and capitalized proper nouns from both versions
and refuses to substitute anything that would change or drop a factual
token. `verify_fact_preservation()` is the check the PRD's "constraint
anchor" describes, and it runs automatically inside `paraphrase_text()` —
if it fails, the original sentence is returned unmodified rather than risk
an inaccurate rewrite.
"""
import re
import random
from nltk.corpus import wordnet
from nltk import pos_tag, word_tokenize

random.seed(42)  # deterministic output for reproducible grading/demo runs

# ---------------------------------------------------------------------------
# AI-cliche opener rewriting. LLM output disproportionately favours a small
# set of hedging/transition templates ("it is important to note that...",
# "furthermore", "moreover", "in conclusion"). These are exactly the
# templated patterns the AI Detector's sentence-uniformity and repeated-ngram
# signals key on, and — critically — naive word-level synonym substitution
# can accidentally CREATE a new repeated phrase (e.g. "crucial" and
# "important" both getting mapped to "important"), making text score WORSE,
# not better. Rewriting these templates at the phrase level, with rotation
# so the same replacement is never used twice in one document, is what
# actually reduces both signals — this is the real mechanism a humanizer
# needs, not just single-word swaps.
# ---------------------------------------------------------------------------
CLICHE_PATTERNS = [
    (re.compile(r"\bit is (important|essential|crucial|vital|critical) to (note|understand|recognize|consider|acknowledge|highlight)(\s+that)?\s*", re.IGNORECASE),
     ["Notably, ", "Worth flagging: ", "One key point: ", "In practice, ", "Here's the thing: ", "Significantly, ", "Tellingly, "]),
    (re.compile(r"^(furthermore|moreover|additionally|in addition)[,:]?\s*", re.IGNORECASE),
     ["Beyond that, ", "On top of this, ", "There's more: ", "Also, ", "What's more, ", "Add to that: "]),
    (re.compile(r"^in conclusion[,:]?\s*", re.IGNORECASE),
     ["Overall, ", "Putting it together, ", "To sum up, ", "Stepping back, "]),
    (re.compile(r"^overall[,:]?\s*", re.IGNORECASE),
     ["Taking a step back, ", "On the whole, ", "All told, "]),
]


MASK_CHAR = "\x00"


def _rewrite_cliche_opener(sentence: str, used_replacements: set) -> str:
    for pattern, options in CLICHE_PATTERNS:
        m = pattern.search(sentence)
        if m:
            available = [o for o in options if o not in used_replacements] or options
            choice = available[0]
            used_replacements.add(choice)
            # Mid-sentence matches (position > 0) shouldn't be capitalized —
            # only sentence-initial replacements should be.
            replacement = choice if m.start() == 0 else choice[0].lower() + choice[1:]
            # Wrap the replacement in mask characters so the later synonym-
            # substitution pass leaves it untouched (it previously re-processed
            # the inserted phrase itself, e.g. turning "Worth flagging:" into
            # "deserving flagging:" — the mask prevents that).
            masked = MASK_CHAR + replacement.replace(" ", MASK_CHAR + " " + MASK_CHAR) + MASK_CHAR
            return sentence[:m.start()] + masked + sentence[m.end():]
    return sentence

BUZZWORD_REPLACEMENTS = {
    "delve": ["explore", "go deep", "look"],
    "delves": ["explores", "goes deep", "looks"],
    "delved": ["explored", "looked"],
    "delving": ["exploring", "looking"],
    "tapestry": ["mix", "combination", "blend", "web"],
    "testament": ["proof", "sign", "tribute"],
    "foster": ["encourage", "promote", "build", "grow"],
    "fosters": ["encourages", "promotes", "builds", "grows"],
    "fostered": ["encouraged", "promoted", "built"],
    "fostering": ["encouraging", "promoting", "building"],
    "ensure": ["make sure", "guarantee", "secure"],
    "ensures": ["makes sure", "guarantees", "secures"],
    "ensured": ["made sure", "guaranteed", "secured"],
    "ensuring": ["making sure", "guaranteeing", "securing"],
    "moreover": ["also", "in addition", "besides", "plus"],
    "furthermore": ["also", "what's more", "besides", "additionally"],
    "additionally": ["also", "as well", "on top of that"],
    "consequently": ["so", "therefore", "as a result"],
    "meticulous": ["careful", "thorough", "precise"],
    "meticulously": ["carefully", "thoroughly", "precisely"],
    "demystify": ["explain", "simplify", "make clear"],
    "demystifies": ["explains", "simplifies", "makes clear"],
    "demystified": ["explained", "simplified", "made clear"],
    "demystifying": ["explaining", "simplifying", "making clear"],
    "vibrant": ["lively", "bright", "active"],
    "paramount": ["key", "essential", "most important"],
    "pivotal": ["key", "critical", "crucial"],
    "multifaceted": ["complex", "varied", "diverse"],
    "revolutionize": ["change", "transform", "reshape"],
    "revolutionizes": ["changes", "transforms", "reshapes"],
    "revolutionized": ["changed", "transformed", "reshaped"],
    "revolutionizing": ["changing", "transforming", "reshaping"],
    "catalyst": ["spark", "cause", "trigger"],
    "beacon": ["guide", "light", "sign"],
    "pinnacle": ["peak", "top", "height"],
    "unwavering": ["steady", "constant", "strong"],
    "transformative": ["deep", "major", "powerful"],
    "realm": ["area", "field", "domain"],
    "spearhead": ["lead", "drive", "head"],
    "spearheaded": ["led", "drove", "headed"],
    "resonate": ["strike a chord", "connect", "align"],
    "resonates": ["strikes a chord", "connects", "aligns"],
}


def _replace_buzzwords(sentence: str) -> str:
    words = sentence.split()
    out = []
    for w in words:
        core = re.sub(r"[^\w'-]", "", w)
        trailing = w[len(core):] if core else ""
        leading = w[:-len(core) - len(trailing)] if core and len(w) > len(core) + len(trailing) else ""
        
        core_lower = core.lower()
        if core_lower in BUZZWORD_REPLACEMENTS:
            candidates = BUZZWORD_REPLACEMENTS[core_lower]
            replacement = candidates[0]
            if core[0].isupper():
                replacement = replacement.capitalize()
            out.append(leading + MASK_CHAR + replacement.replace(" ", MASK_CHAR + " " + MASK_CHAR) + MASK_CHAR + trailing)
        else:
            out.append(w)
    return " ".join(out)


def _split_sentence_for_burstiness(sentence: str) -> str:
    words = sentence.split()
    if len(words) < 18:
        return sentence
    m = re.match(r"^(.+?),\s*(and|but|or|while)\s+(.+)$", sentence, re.IGNORECASE)
    if m:
        clause1, conj, clause2 = m.groups()
        if len(clause1.split()) > 5 and len(clause2.split()) > 5:
            sentence1 = clause1.strip()
            if not sentence1.endswith(('.', '!', '?')):
                sentence1 += "."
            sentence2 = conj.capitalize() + " " + clause2.strip()
            return f"{sentence1} {sentence2}"
    return sentence


MODES = ("academic", "professional", "short_form", "structural")

NUMBER_PATTERN = re.compile(r"\b\d[\d,.]*%?\b")
PROPER_NOUN_PATTERN = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")

STOPWORDS_NO_SUBSTITUTE = {
    "the", "a", "an", "is", "are", "was", "were", "this", "that", "these", "those",
    "and", "or", "but", "not", "no", "of", "to", "in", "on", "for", "with", "as",
    "has", "have", "had", "at", "by", "it", "its", "be", "been", "being", "from",
    "which", "who", "whom", "into", "onto", "than", "then", "so", "if", "when",
    "while", "because", "about", "over", "under", "between", "there", "their",
}


def _is_reasonable_synonym(word: str, candidate: str) -> bool:
    if len(word) < 4:
        return False
    if not candidate.replace(" ", "").replace("-", "").isalpha():
        return False
    if candidate.isupper():  # avoid acronym lemma matches like "HA"
        return False
    if len(candidate) < 3:
        return False
    # Guard against wildly different length substitutions (register mismatch)
    if abs(len(candidate) - len(word)) > max(4, len(word) // 2):
        return False
    return True


POS_MAP = {"NN": wordnet.NOUN, "NNS": wordnet.NOUN, "JJ": wordnet.ADJ, "JJR": wordnet.ADJ, "JJS": wordnet.ADJ}
SAFE_TAGS = set(POS_MAP.keys())  # deliberately excludes verbs (VB*) — WordNet's
# sense/tense disambiguation for verbs is unreliable without a full WSD model,
# and a wrong verb substitution ("found" -> "plant") is a much worse failure
# than a slightly generic noun/adjective swap. This is a real precision/recall
# tradeoff, made in favour of not corrupting meaning.


def _best_synonym(word: str, tag: str = None, used_outputs: set = None) -> str:
    wn_pos = POS_MAP.get(tag)
    synsets = wordnet.synsets(word, pos=wn_pos) if wn_pos else wordnet.synsets(word)
    if not synsets:
        return word
    candidates = set()
    for syn in synsets[:1]:  # most frequent sense only — reduces rare/obscure-sense noise
        for lemma in syn.lemmas():
            name = lemma.name().replace("_", " ")
            if name.lower() != word.lower() and " " not in name and _is_reasonable_synonym(word, name):
                candidates.add(name)
    if not candidates:
        return word
    candidates = sorted(candidates, key=lambda c: abs(len(c) - len(word)))
    # Skip any candidate already used elsewhere in this document — reusing an
    # output word for two different original words is exactly what creates a
    # NEW repeated pattern that wasn't in the source text (see module
    # docstring: this was a real bug where "crucial" and "important" both
    # collapsed to "important", making the text score worse, not better).
    if used_outputs is not None:
        fresh = [c for c in candidates if c.lower() not in used_outputs]
        if fresh:
            candidates = fresh
        else:
            return word  # every known synonym already used — leave unchanged rather than create a duplicate
    chosen = candidates[0]
    if used_outputs is not None:
        used_outputs.add(chosen.lower())
    if word[0].isupper():
        chosen = chosen.capitalize()
    return chosen


def _extract_facts(text: str) -> set:
    text = text.replace(MASK_CHAR, "")
    numbers = set(NUMBER_PATTERN.findall(text))
    # Lowercase each sentence's first letter before hunting for capitalized
    # words — otherwise ordinary sentence-initial capitalization ("Notably,",
    # "The results...") gets misread as a proper noun, and a cliche-opener
    # rewrite like "It is important..." -> "Notably, ..." gets rejected by
    # the fact-preservation check even though no real fact changed. Real
    # proper nouns (capitalized mid-sentence, e.g. "Stanford") are unaffected.
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    normalized_parts = []
    for s in sentences:
        if s:
            normalized_parts.append(s[0].lower() + s[1:] if len(s) > 1 else s.lower())
    normalized_text = " ".join(normalized_parts)
    proper_nouns = set(PROPER_NOUN_PATTERN.findall(normalized_text))
    return numbers | proper_nouns


def verify_fact_preservation(original: str, rewritten: str) -> dict:
    """Constraint anchor: numbers/dates/proper-noun tokens must be identical
    between original and rewritten text — this is the PRD's '100% data
    facts preservation, zero structural hallucinations' rule, enforced."""
    original_facts = _extract_facts(original)
    rewritten_facts = _extract_facts(rewritten)
    missing = original_facts - rewritten_facts
    added = rewritten_facts - original_facts
    return {
        "preserved": len(missing) == 0 and len(added) == 0,
        "missing_facts": sorted(missing),
        "added_facts": sorted(added),
    }


def _substitute_synonyms(sentence: str, intensity: float = 0.35, used_outputs: set = None) -> str:
    tokens = sentence.split()
    try:
        tagged = pos_tag(word_tokenize(sentence))
    except Exception:
        tagged = [(t, None) for t in tokens]
    # word_tokenize can split differently than simple .split() (e.g. punctuation) —
    # fall back to untagged substitution if lengths don't line up cleanly.
    tag_lookup = {}
    for word, tag in tagged:
        tag_lookup.setdefault(word.lower(), tag)

    out = []
    for w in tokens:
        if MASK_CHAR in w:
            out.append(w)
            continue
        core = re.sub(r"[^\w'-]", "", w)
        trailing = w[len(core):] if core else ""
        if not core or core.lower() in STOPWORDS_NO_SUBSTITUTE or core[0].isupper() or core.isdigit():
            out.append(w)
            continue
        tag = tag_lookup.get(core.lower())
        if tag not in SAFE_TAGS:
            out.append(w)
            continue
        if random.random() < intensity:
            syn = _best_synonym(core, tag, used_outputs=used_outputs)
            out.append(syn + trailing)
        else:
            out.append(w)
    return " ".join(out)


def _reorder_clauses(sentence: str) -> str:
    m = re.match(r"^(.+?),\s*(and|but|so|while|because)\s+(.+)$", sentence, re.IGNORECASE)
    if m:
        clause1, conj, clause2 = m.groups()
        return f"{clause2.strip().capitalize()}, {conj} {clause1.strip()[0].lower()}{clause1.strip()[1:]}."
    return sentence


MODE_INTENSITY = {"academic": 0.30, "professional": 0.35, "short_form": 0.45, "structural": 0.20}


def paraphrase_text(text: str, mode: str = "academic") -> dict:
    if mode not in MODES:
        mode = "academic"
    intensity = MODE_INTENSITY[mode]

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    rewritten_sentences = []
    rejected_sentences = []
    used_synonym_outputs = set()   # document-wide, prevents accidental new repetition
    used_cliche_replacements = set()  # document-wide, rotates opener variety

    for s in sentences:
        if not s.strip():
            continue

        # Phrase-level rewrite first (breaks up AI-cliche templates)
        de_clicheed = _rewrite_cliche_opener(s, used_cliche_replacements)
        
        # New Step: Replace typical AI buzzwords/clichés
        buzzword_replaced = _replace_buzzwords(de_clicheed)
        
        # Word-level synonym substitution
        candidate = _substitute_synonyms(buzzword_replaced, intensity=intensity, used_outputs=used_synonym_outputs)
        
        if mode == "structural":
            candidate = _reorder_clauses(candidate)

        # New Step: Split long sentences to inject human-like burstiness (sentence variance)
        if mode in ("academic", "professional", "structural"):
            candidate = _split_sentence_for_burstiness(candidate)

        check = verify_fact_preservation(s, candidate)
        if check["preserved"]:
            rewritten_sentences.append(candidate)
        else:
            # Constraint anchor violated -> keep original sentence unchanged.
            rewritten_sentences.append(s)
            rejected_sentences.append({"original": s, "attempted": candidate, "reason": check})

    rewritten_text = " ".join(rewritten_sentences)
    rewritten_text = rewritten_text.replace(MASK_CHAR, "")
    rewritten_text = re.sub(r"\s{2,}", " ", rewritten_text)
    overall_check = verify_fact_preservation(text, rewritten_text)

    original_words = set(re.findall(r"[a-zA-Z']+", text.lower()))
    rewritten_words = set(re.findall(r"[a-zA-Z']+", rewritten_text.lower()))
    uniqueness_delta = round(
        (len(rewritten_words - original_words) / max(1, len(original_words))) * 100, 1
    )

    return {
        "mode": mode,
        "rewritten_text": rewritten_text,
        "fact_preservation": overall_check,
        "sentences_rewritten": len(rewritten_sentences) - len(rejected_sentences),
        "sentences_rejected_for_fact_risk": len(rejected_sentences),
        "rejected_detail": rejected_sentences[:10],
        "lexical_change_pct": uniqueness_delta,
    }
