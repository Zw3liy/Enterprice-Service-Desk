import re

def extract_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()
