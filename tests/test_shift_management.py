from app.application.use_cases.shift_management import detect_shift_type


def test_detect_shift_type_allows_signup_until_21_00() -> None:
    assert detect_shift_type(7, 29) is None
    assert detect_shift_type(7, 30) == "morning"
    assert detect_shift_type(13, 59) == "morning"
    assert detect_shift_type(14, 0) == "evening"
    assert detect_shift_type(20, 59) == "evening"
    assert detect_shift_type(21, 0) is None
