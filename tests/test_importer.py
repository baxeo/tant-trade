from app.core.models import Company
from app.services.importer import (
    calculate_lead_score,
    calculate_lead_score_breakdown,
    find_duplicate_company,
    map_columns,
    normalize_domain,
    normalize_name,
)


def test_normalize_name():
    assert normalize_name("  Acme Snacks, Ltd. ") == "acme snacks ltd"


def test_map_columns_accepts_buyer_alias():
    assert map_columns(["Buyer Name", "Country", "Email"]) == {
        "name": "Buyer Name",
        "country": "Country",
        "email": "Email",
    }


def test_lead_score_rewards_complete_record():
    raw = {"Company": "Acme", "Country": "TZ", "Website": "acme.example", "Email": "sales@acme.example", "Phone": "+255", "Type": "Importer"}
    mapping = map_columns(raw.keys())
    assert calculate_lead_score(raw, mapping) == 100


def test_lead_score_breakdown_explains_missing_signals():
    raw = {"Company": "Acme", "Country": "TZ"}
    breakdown = calculate_lead_score_breakdown(raw, map_columns(raw.keys()))

    assert breakdown["score"] == 40
    assert breakdown["version"] == "completeness-v1"
    assert breakdown["components"]["email"]["reason"] == "Signal is missing"
    assert breakdown["components"]["country"]["points"] == 15


def test_duplicate_match_uses_domain_and_country():
    company = Company(name="Acme Snacks Ltd", normalized_name="acme snacks ltd", country="Tanzania", website="https://www.acme.example")

    assert normalize_domain("http://www.acme.example/catalog") == "acme.example"
    assert find_duplicate_company("Acme Snack Limited", "Tanzania", "acme.example", [company]) is company


def test_duplicate_match_does_not_cross_country_boundary():
    company = Company(name="Acme Snacks Ltd", normalized_name="acme snacks ltd", country="Tanzania")

    assert find_duplicate_company("Acme Snacks Limited", "Kenya", None, [company]) is None
