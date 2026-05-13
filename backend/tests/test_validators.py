from app.utils.validators import validate_cui


def test_validate_cui_valid():
    """Valid CUI should pass mod-11 check."""
    # CUI 14399840 is a known valid Romanian CUI (checksum passes)
    assert validate_cui("14399840") == True


def test_validate_cui_invalid():
    """Invalid CUI should fail."""
    assert validate_cui("00000000") == False
    assert validate_cui("abc") == False
    assert validate_cui("") == False


def test_validate_cui_strips_ro():
    """CUI with RO prefix should be stripped."""
    assert validate_cui("RO14399840") == True
