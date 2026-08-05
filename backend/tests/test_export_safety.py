from app.main import xlsx_text


def test_excel_formula_like_text_is_escaped() -> None:
    for value in ("=1+1", "+1", "-1", "@SUM(A1)"):
        assert xlsx_text(value).startswith("'")


def test_regular_excel_text_is_unchanged() -> None:
    assert xlsx_text("normal title") == "normal title"
