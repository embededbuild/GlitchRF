from __future__ import annotations


def normalize_hex(value: str) -> str:
    if value is None:
        return ""
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    return text.upper()


def is_valid_hex(value: str) -> bool:
    text = normalize_hex(value)
    if not text:
        return False
    return all(ch in "0123456789ABCDEF" for ch in text)


def safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print()
        return ""
