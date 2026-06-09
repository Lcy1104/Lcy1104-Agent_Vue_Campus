"""
Input sanitization utilities.
Based on need.md: backend/app/utils/sanitizer.py
"""
from html import escape
from typing import Any


def sanitize_text(value: str) -> str:
    return escape(value.strip(), quote=True)


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_payload(item) for key, item in value.items()}
    return value
