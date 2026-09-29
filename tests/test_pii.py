from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd_credit_card_passport() -> None:
    assert "REDACTED_CCCD" in scrub_text("CCCD 012345678901")
    assert "4111" not in scrub_text("card 4111 1111 1111 1111")
    assert "REDACTED_CREDIT_CARD" in scrub_text("card 4111-1111-1111-1111")
    assert "B1234567" not in scrub_text("passport B1234567")


def test_scrub_address_keyword() -> None:
    assert "Nguyen Trai" not in scrub_text("Tôi ở đường Nguyen Trai")
