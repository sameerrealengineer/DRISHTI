"""Citizen report AI v1 — rule-based triage (PRD §6.6 BE-REP-2, Appendix 21.3).

Pure functions. The v2 model (MuRIL/IndicBERT) will sit behind the REPORT_AI flag
and must return the same `Triage` shape.

Matching: Latin-script stems match at a word start; stems of 4 letters or fewer
must match a whole word (optionally plural "s"), so "pole" does not fire on
"Polasara". Odia / Devanagari stems match as plain substrings.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

HAZARDS: dict[str, list[str]] = {
    "flood": [
        "flood",
        "water",
        "inundat",
        "submerg",
        "paani",
        "pani",
        "baadh",
        "badh",
        "banya",
        "bonya",
        "jala",
        "overflow",
        "breach",
        "washed",
        "ପାଣି",
        "ବନ୍ୟା",
        "पानी",
        "बाढ़",
    ],
    "wind": [
        "tree fell",
        "tree fall",
        "uprooted",
        "roof",
        "wind",
        "toofan",
        "tufan",
        "bataasa",
        "pole",
        "collapsed",
        "flattened",
        "huts",
        "ବାତ୍ୟା",
        "तूफान",
    ],
    "surge": ["sea water", "tidal", "surge", "samudra", "ସମୁଦ୍ର"],
    "cut_off": ["bridge", "road cut", "cut off", "washed away", "no road", "stranded"],
    "medical": ["injured", "doctor", "medical", "bleeding", "sick"],
    "power": ["power line", "electric pole", "wire"],
}
HAZARD_ORDER = ["flood", "wind", "surge", "cut_off", "medical", "power"]

NEEDS: dict[str, list[str]] = {
    "rescue": ["stuck", "trapped", "fasa", "roof", "boat", "rescue", "bachao", "help"],
    "medical": ["injured", "medical", "doctor", "pregnant", "elderly", "sick", "bleeding"],
    "food_water": ["food", "khana", "water to drink", "ration", "hungry"],
    "shelter": ["huts", "house", "ghar", "homeless", "in open", "collapsed"],
}
NEED_ORDER = ["rescue", "medical", "food_water", "shelter"]

DEPTH_WORDS: list[tuple[str, int]] = [
    ("chest", 5),
    ("neck", 5),
    ("roof", 5),
    ("waist", 4),
    ("kamar", 4),
    ("knee", 3),
    ("ghutna", 3),
    ("ankle", 2),
]

DEFAULT_ALIASES: dict[str, str] = {
    "gopalpur": "rangeilunda",
    "berhampur": "kukudakhandi",
    "brahmapur": "kukudakhandi",
    "chatrapur": "chhatrapur",
    "purusottampur": "purushottampur",
    "hinjili": "hinjilicut",
    "sunapur": "rangeilunda",
    "sonapur": "patrapur",
    "humma": "ganjam",
    "khalikote": "khallikote",
    "rushikulya mouth": "ganjam",
}

PEOPLE_RE = re.compile(r"(\d+)\s*(famil|people|log|person)")
_HINDI_ROMAN = {
    "paani",
    "baadh",
    "badh",
    "log",
    "bachao",
    "ghar",
    "khana",
    "kamar",
    "ghutna",
    "fasa",
    "fase",
    "hai",
    "hain",
    "mein",
    "nahi",
    "toofan",
    "tufan",
}
_ODIA_ROMAN = {"bonya", "banya", "jala", "bataasa", "samudra", "pani", "achhi", "achhu", "heba", "gaan"}


@dataclass
class Triage:
    language: str
    place: str | None  # block id
    place_source: str | None  # block | alias | village
    hazards: list[str] = field(default_factory=list)
    severity: int = 1
    needs: list[str] = field(default_factory=list)
    people_count: int | None = None
    confidence: float = 0.35

    def as_dict(self) -> dict:
        return asdict(self)


def _is_latin(stem: str) -> bool:
    return all(ord(c) < 128 for c in stem)


def _pattern(stem: str) -> re.Pattern[str] | None:
    if not _is_latin(stem):
        return None
    esc = re.escape(stem)
    if len(stem) <= 4:
        return re.compile(rf"(?<![a-z]){esc}s?(?![a-z])")
    return re.compile(rf"(?<![a-z]){esc}")


_PATTERNS: dict[str, re.Pattern[str] | None] = {}


def has_term(text: str, stem: str) -> bool:
    if stem not in _PATTERNS:
        _PATTERNS[stem] = _pattern(stem)
    pat = _PATTERNS[stem]
    return stem in text if pat is None else bool(pat.search(text))


def detect_language(text: str) -> str:
    if any("଀" <= c <= "୿" for c in text):
        return "or"
    if any("ऀ" <= c <= "ॿ" for c in text):
        return "hi"
    words = set(re.findall(r"[a-z]+", text.lower()))
    hi, od = len(words & _HINDI_ROMAN), len(words & _ODIA_ROMAN)
    if hi == 0 and od == 0:
        return "en"
    return "hi" if hi >= od else "or"


def extract_place(
    text: str,
    block_names: dict[str, str],
    aliases: dict[str, str] | None = None,
    villages: dict[str, str] | None = None,
) -> tuple[str | None, str | None]:
    """Return (block_id, source). `block_names` maps lower-case name -> block id."""
    low = text.lower()
    hits = [(low.find(name), bid) for name, bid in block_names.items() if name in low]
    if hits:
        return min(hits)[1], "block"
    alias_map = aliases if aliases is not None else DEFAULT_ALIASES
    # longest alias first so "rushikulya mouth" wins over shorter overlaps
    for alias in sorted(alias_map, key=len, reverse=True):
        if alias in low:
            return alias_map[alias], "alias"
    for vname, bid in (villages or {}).items():
        if vname in low:
            return bid, "village"
    return None, None


def analyze_report(
    text: str,
    block_names: dict[str, str],
    aliases: dict[str, str] | None = None,
    villages: dict[str, str] | None = None,
) -> Triage:
    low = (text or "").lower()
    place, source = extract_place(low, block_names, aliases, villages)
    hazards = [h for h in HAZARD_ORDER if any(has_term(low, s) for s in HAZARDS[h])]
    needs = [n for n in NEED_ORDER if any(has_term(low, s) for s in NEEDS[n])]

    severity = 2 if hazards else 1
    for word, sev in DEPTH_WORDS:
        if has_term(low, word):
            severity = max(severity, sev)
    if "rescue" in needs:
        severity = max(severity, 4)
    if has_term(low, "injured") or "cut_off" in hazards:
        severity = max(severity, 4)

    people = None
    m = PEOPLE_RE.search(low)
    if m:
        people = int(m.group(1)) * (4 if m.group(2) == "famil" else 1)
        severity = min(5, severity + 1)

    confidence = 0.35 + (0.2 if place else 0.0) + 0.15 * len(hazards) + 0.1 * len(needs)
    confidence = round(max(0.0, min(0.97, confidence)), 2)

    return Triage(
        language=detect_language(text or ""),
        place=place,
        place_source=source,
        hazards=hazards,
        severity=severity,
        needs=needs,
        people_count=people,
        confidence=confidence,
    )
