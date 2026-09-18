from pathlib import Path
import re
from typing import Any

import pandas as pd
from rapidfuzz.fuzz import token_set_ratio
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Company

COLUMN_ALIASES = {
    "name": {"name", "company", "company_name", "buyer", "buyer_name", "business_name"},
    "country": {"country", "nation", "location_country"},
    "city": {"city", "town", "location_city"},
    "website": {"website", "web", "url", "company_website"},
    "email": {"email", "email_address", "contact_email"},
    "phone": {"phone", "telephone", "mobile", "whatsapp"},
    "buyer_type": {"buyer_type", "type", "category", "industry"},
}


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def map_columns(columns: list[Any]) -> dict[str, str]:
    normalized = {normalize_key(column): str(column) for column in columns}
    mapping: dict[str, str] = {}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[target] = normalized[alias]
                break
    return mapping


def import_excel(file_path: str | Path, session: Session) -> tuple[int, int, list[str]]:
    frame = pd.read_excel(file_path)
    mapping = map_columns(list(frame.columns))
    if "name" not in mapping:
        raise ValueError("Excel file must contain a company, buyer, or name column")

    imported = skipped = 0
    errors: list[str] = []
    existing = list(session.scalars(select(Company)).all())

    for row_number, row in frame.iterrows():
        raw = {str(key): _json_value(value) for key, value in row.to_dict().items()}
        name = str(raw.get(mapping["name"]) or "").strip()
        normalized_name = normalize_name(name)
        if not normalized_name:
            skipped += 1
            errors.append(f"Row {row_number + 2}: missing company name")
            continue
        duplicate = find_duplicate_company(
            name=name,
            country=_value(raw, mapping, "country"),
            website=_value(raw, mapping, "website"),
            companies=existing,
        )
        if duplicate:
            skipped += 1
            if duplicate.normalized_name != normalized_name:
                errors.append(
                    f"Row {row_number + 2}: possible duplicate of '{duplicate.name}', skipped for review"
                )
            continue

        company = Company(
            name=name,
            normalized_name=normalized_name,
            country=_value(raw, mapping, "country"),
            city=_value(raw, mapping, "city"),
            website=_value(raw, mapping, "website"),
            email=_value(raw, mapping, "email"),
            phone=_value(raw, mapping, "phone"),
            buyer_type=_value(raw, mapping, "buyer_type"),
            source="excel",
            source_row=raw,
            lead_score=calculate_lead_score(raw, mapping),
            lead_score_components=calculate_lead_score_breakdown(raw, mapping),
        )
        session.add(company)
        existing.append(company)
        imported += 1

    session.commit()
    return imported, skipped, errors


def _value(raw: dict[str, Any], mapping: dict[str, str], key: str) -> str | None:
    if key not in mapping:
        return None
    value = raw.get(mapping[key])
    return str(value).strip() if value is not None and str(value).strip() else None


def find_duplicate_company(
    name: str,
    country: str | None,
    website: str | None,
    companies: list[Company],
) -> Company | None:
    """Find an exact or high-confidence duplicate without merging records."""
    normalized_name = normalize_name(name)
    domain = normalize_domain(website)
    for company in companies:
        if company.normalized_name == normalized_name:
            return company
        if country and company.country and normalize_name(country) != normalize_name(company.country):
            continue
        if domain and domain == normalize_domain(company.website):
            return company
        if token_set_ratio(normalized_name, company.normalized_name) >= 90:
            return company
    return None


def normalize_domain(website: str | None) -> str:
    value = (website or "").strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = value.split("/", 1)[0].split(":", 1)[0]
    return value.removeprefix("www.")


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def calculate_lead_score(raw: dict[str, Any], mapping: dict[str, str]) -> float:
    return float(calculate_lead_score_breakdown(raw, mapping)["score"])


def calculate_lead_score_breakdown(raw: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Return the score and auditable reasons for each available signal."""
    components = {
        "base": {"points": 25.0, "reason": "Baseline for a discovered company"},
        "country": _component(15.0, _value(raw, mapping, "country"), "Country is present"),
        "website": _component(15.0, _value(raw, mapping, "website"), "Website is present"),
        "email": _component(20.0, _value(raw, mapping, "email"), "Email is present"),
        "phone": _component(10.0, _value(raw, mapping, "phone"), "Phone is present"),
        "buyer_type": _component(15.0, _value(raw, mapping, "buyer_type"), "Buyer type is present"),
    }
    score = min(sum(item["points"] for item in components.values()), 100.0)
    return {"score": score, "version": "completeness-v1", "components": components}


def _component(max_points: float, value: str | None, positive_reason: str) -> dict[str, Any]:
    if value:
        return {"points": max_points, "max_points": max_points, "reason": positive_reason}
    return {"points": 0.0, "max_points": max_points, "reason": "Signal is missing"}
