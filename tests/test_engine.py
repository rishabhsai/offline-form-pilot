from formpilot.engine import analyze_form, detect_fields, parse_user_facts


def test_detect_fields_from_underlined_form() -> None:
    form = """
    Full name: ____________
    Email: ________________
    Emergency contact: ____
    """
    assert detect_fields(form) == ["Full name", "Email", "Emergency contact"]


def test_parse_user_facts_key_values_and_free_text() -> None:
    facts = parse_user_facts(
        """
        Name: Jordan Lee
        jordan.lee@example.com
        Phone: 555-0137
        """
    )
    assert facts["name"] == "Jordan Lee"
    assert facts["email"] == "jordan.lee@example.com"
    assert facts["phone"] == "555-0137"


def test_analyze_form_marks_missing_fields() -> None:
    payload = analyze_form("Full name: ____\nEmail: ____\nSignature: ____", "Full name: Jordan Lee")
    rows = {row["field"]: row for row in payload["rows"]}
    assert rows["Full name"]["status"] == "ready"
    assert rows["Email"]["status"] == "missing"
    assert rows["Signature"]["status"] == "missing"
    assert payload["questions"]
