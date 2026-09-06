from shared.storage import sanitize_identifier


def test_sanitize_identifier_collapses_whitespace_to_underscores():
    assert sanitize_identifier("ADJ 49297") == "ADJ_49297"


def test_sanitize_identifier_handles_multiple_internal_spaces():
    assert sanitize_identifier("IR - SC - 00001785") == "IR_-_SC_-_00001785"


def test_sanitize_identifier_leaves_clean_identifiers_unchanged():
    assert sanitize_identifier("LCR22904") == "LCR22904"


def test_sanitize_identifier_strips_leading_trailing_whitespace():
    assert sanitize_identifier("  ADJ-00047352  ") == "ADJ-00047352"
