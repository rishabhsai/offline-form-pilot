"""Structured form analysis for Offline Form Pilot."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


COMMON_FIELDS = [
    "full name",
    "first name",
    "last name",
    "date of birth",
    "email",
    "phone",
    "address",
    "city",
    "state",
    "postal code",
    "zip code",
    "country",
    "employer",
    "school",
    "student id",
    "account number",
    "policy number",
    "emergency contact",
    "relationship",
    "signature",
    "date",
]

SENSITIVE_TERMS = {
    "ssn",
    "social security",
    "passport",
    "bank",
    "routing",
    "account",
    "card",
    "credit",
    "medical",
    "diagnosis",
    "tax",
    "visa",
    "immigration",
}

STOPWORDS = {
    "the",
    "a",
    "an",
    "your",
    "you",
    "of",
    "for",
    "and",
    "or",
    "to",
    "in",
    "on",
    "with",
    "please",
    "enter",
    "provide",
}


@dataclass(frozen=True)
class FieldMatch:
    field: str
    proposed_value: str
    status: str
    confidence: int
    source: str
    note: str


def normalize_label(text: str) -> str:
    """Normalize labels for fuzzy matching."""

    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> set[str]:
    return {token for token in normalize_label(text).split() if token not in STOPWORDS}


def parse_user_facts(raw_facts: str) -> dict[str, str]:
    """Parse key-value facts from pasted user notes."""

    facts: dict[str, str] = {}
    free_lines: list[str] = []
    for line in raw_facts.splitlines():
        cleaned = line.strip().strip("-*")
        if not cleaned:
            continue
        match = re.match(r"^([^:=]{2,60})\s*[:=]\s*(.+)$", cleaned)
        if match:
            key = normalize_label(match.group(1))
            value = match.group(2).strip()
            facts[key] = value
        else:
            free_lines.append(cleaned)

    inferred = infer_facts_from_free_text("\n".join(free_lines))
    for key, value in inferred.items():
        facts.setdefault(key, value)
    return facts


def infer_facts_from_free_text(text: str) -> dict[str, str]:
    """Extract a small set of common facts from unstructured text."""

    facts: dict[str, str] = {}
    email = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
    if email:
        facts["email"] = email.group(0)

    phone = re.search(r"(?:\+?\d[\d .()-]{7,}\d)", text)
    if phone:
        facts["phone"] = phone.group(0).strip()

    zip_code = re.search(r"\b\d{5}(?:-\d{4})?\b", text)
    if zip_code:
        facts["zip code"] = zip_code.group(0)
        facts["postal code"] = zip_code.group(0)

    dob = re.search(r"\b(?:dob|date of birth)\s*[:=]?\s*([A-Za-z0-9, /.-]{6,20})", text, re.I)
    if dob:
        facts["date of birth"] = dob.group(1).strip()

    return facts


def detect_fields(form_text: str) -> list[str]:
    """Find likely form fields from pasted form text."""

    candidates: list[str] = []

    for line in form_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        cleaned = re.sub(r"\s+", " ", cleaned)

        label_match = re.match(r"^([A-Za-z][A-Za-z0-9 /'().,-]{1,70})\s*[:_]{1,}\s*(?:\[\s*\])?\s*$", cleaned)
        if label_match:
            candidates.append(label_match.group(1))
            continue

        bracket_match = re.match(r"^([A-Za-z][A-Za-z0-9 /'().,-]{1,70})\s*\[\s*\]\s*$", cleaned)
        if bracket_match:
            candidates.append(bracket_match.group(1))
            continue

        inline_match = re.match(r"^([A-Za-z][A-Za-z0-9 /'().,-]{1,45})\s*:\s+_{2,}", cleaned)
        if inline_match:
            candidates.append(inline_match.group(1))

    lowered_form = normalize_label(form_text)
    for common in COMMON_FIELDS:
        if common in lowered_form:
            candidates.append(common)

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        label = normalize_label(candidate)
        if len(label) < 2 or label in seen:
            continue
        seen.add(label)
        unique.append(candidate.strip(" :_"))
    return unique


def match_field(field: str, facts: dict[str, str]) -> FieldMatch:
    """Match one field label to available user facts."""

    field_norm = normalize_label(field)
    field_tokens = _tokens(field)
    best_key = ""
    best_score = 0.0

    for key in facts:
        key_tokens = _tokens(key)
        overlap = len(field_tokens & key_tokens) / max(1, len(field_tokens | key_tokens))
        ratio = SequenceMatcher(None, field_norm, key).ratio()
        score = max(overlap, ratio * 0.85)
        if score > best_score:
            best_key = key
            best_score = score

    if not best_key:
        return _missing_match(field, "No matching user fact found.")

    value = facts[best_key]
    sensitive = is_sensitive_field(field)
    if best_score >= 0.86 or field_norm == best_key:
        confidence = 95 if not sensitive else 84
        status = "review" if sensitive else "ready"
        note = "Strong label match."
    elif best_score >= 0.58:
        confidence = int(best_score * 100)
        status = "review"
        note = f"Possible match from '{best_key}'."
    else:
        return _missing_match(field, "No close enough user fact found.")

    if sensitive:
        note += " Sensitive field: verify manually before copying."

    return FieldMatch(
        field=field,
        proposed_value=value,
        status=status,
        confidence=confidence,
        source=best_key,
        note=note,
    )


def _missing_match(field: str, note: str) -> FieldMatch:
    return FieldMatch(
        field=field,
        proposed_value="",
        status="missing",
        confidence=0,
        source="",
        note=note,
    )


def is_sensitive_field(field: str) -> bool:
    label = normalize_label(field)
    return any(term in label for term in SENSITIVE_TERMS)


def questions_for_missing(matches: list[FieldMatch]) -> list[str]:
    """Generate plain-English follow-up questions for missing fields."""

    questions = []
    for match in matches:
        if match.status == "missing":
            questions.append(f"What should go in '{match.field}'?")
    return questions


def _risk_summary(matches: list[FieldMatch]) -> list[str]:
    risks = []
    missing = sum(1 for match in matches if match.status == "missing")
    review = sum(1 for match in matches if match.status == "review")
    sensitive = sum(1 for match in matches if is_sensitive_field(match.field))
    if missing:
        risks.append(f"{missing} field(s) still need information.")
    if review:
        risks.append(f"{review} field(s) should be reviewed before copying.")
    if sensitive:
        risks.append(f"{sensitive} sensitive field(s) detected.")
    if not risks:
        risks.append("All detected fields have proposed values, but user review is still required.")
    return risks


def analyze_form(form_text: str, user_facts: str, use_demo_fields: bool = True) -> dict[str, Any]:
    """Analyze form text and facts into reviewable outputs."""

    fields = detect_fields(form_text)
    if not fields and use_demo_fields:
        fields = ["Full name", "Email", "Phone", "Address", "Date", "Signature"]

    facts = parse_user_facts(user_facts)
    matches = [match_field(field, facts) for field in fields]
    rows = [asdict(match) for match in matches]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fields": fields,
        "facts": facts,
        "rows": rows,
        "questions": questions_for_missing(matches),
        "risk_summary": _risk_summary(matches),
        "copy_ready": copy_ready_text(matches),
    }


def copy_ready_text(matches: list[FieldMatch]) -> str:
    """Create a conservative copy-ready field list."""

    lines = []
    for match in matches:
        value = match.proposed_value if match.proposed_value else "[NEEDS USER INPUT]"
        flag = " REVIEW" if match.status == "review" else ""
        lines.append(f"{match.field}: {value}{flag}")
    return "\n".join(lines)


def export_trace(payload: dict[str, Any], directory: Path | str = "traces") -> str:
    """Write one anonymizable JSON trace and return its path."""

    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"formpilot_trace_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """Serialize rows for quick export."""

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["field", "proposed_value", "status", "confidence", "source", "note"],
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
