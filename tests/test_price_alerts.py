"""Unit tests for the alert bot's pure logic (no DB needed)."""
from rpa.alerts.price_alert_bot import build_email

DROP = {"type": "price_drop", "brand_name": "Crocin", "profile_label": "self",
        "old_price": 18.0, "new_price": 14.4, "drop_pct": 20.0}
JAN = {"type": "jan_aushadhi", "brand_name": "Glycomet", "profile_label": "Papa",
       "brand_price": 28.5, "ja_name": "Metformin (Jan Aushadhi)", "ja_price": 6.74,
       "save_rupees": 21.76, "save_pct": 76.4, "caution": True}


def test_drop_email_subject_and_body():
    subject, html, text = build_email([DROP])
    assert "Crocin" in subject and "14.40" in subject and "20.0%" in subject
    assert "18.00" in text and "14.40" in text and "doctor or pharmacist" in text


def test_jan_aushadhi_only_email_and_caution():
    subject, html, text = build_email([JAN])
    assert subject.startswith("Save Rs.21.76")
    assert "for Papa" in text and "CAUTION" in text and "consult your doctor" in html


def test_html_escapes_brand_names():
    _, html, _ = build_email([{**DROP, "brand_name": "<script>x</script>"}])
    assert "<script>" not in html
