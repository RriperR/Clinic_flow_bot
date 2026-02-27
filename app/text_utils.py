def normalize_text(value: str | None) -> str:
    return (value or "").strip().casefold()
