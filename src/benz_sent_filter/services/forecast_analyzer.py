"""Far-future forecast detection using pattern matching.

This module provides functions to detect far-future forecasts (>1 year) in headlines
by matching multi-year timeframe patterns and excluding near-term indicators.
"""

import re


def matches_multi_year_timeframe(text: str) -> tuple[bool, str | None]:
    """Detect multi-year timeframe patterns in text.

    Patterns detected:
    - "over X years" / "over X-year"
    - "X-year" (e.g., "5-year plan")
    - "by YYYY" (year reference)
    - "through YYYY" (year range)

    Args:
        text: Text to analyze (typically headline or summary)

    Returns:
        Tuple of (match_found: bool, extracted_timeframe: str | None)
    """
    text_lower = text.lower()

    # Pattern: "over X years" or "over X-year"
    match = re.search(r"over\s+(\d+)[- ]years?", text_lower)
    if match:
        return True, f"over {match.group(1)} years"

    # Pattern: "X-year" (e.g., "5-year", "3-year")
    match = re.search(r"(\d+)-years?", text_lower)
    if match:
        return True, f"{match.group(1)}-year"

    # Pattern: "by YYYY" or "through YYYY" (year reference)
    # Match years from 2024-2099 (far-future threshold)
    match = re.search(r"(?:by|through)\s+(20\d{2})", text_lower)
    if match:
        year = match.group(1)
        return True, f"by {year}"

    return False, None


def matches_quarterly_language(text: str) -> bool:
    """Detect near-term quarterly indicators in text.

    Patterns detected:
    - Q1, Q2, Q3, Q4
    - "quarterly", "quarter"
    - "fiscal YYYY" (near-term fiscal year guidance)

    Args:
        text: Text to analyze (typically headline or summary)

    Returns:
        True if near-term quarterly language detected, False otherwise
    """
    text_lower = text.lower()

    # Pattern: Q1, Q2, Q3, Q4 (with word boundaries)
    if re.search(r"\bq[1-4]\b", text_lower):
        return True

    # Pattern: "quarterly" or "quarter"
    if re.search(r"\bquarter(?:ly)?\b", text_lower):
        return True

    # Pattern: "fiscal YYYY" (near-term guidance)
    if re.search(r"\bfiscal\s+20\d{2}\b", text_lower):
        return True

    return False


def is_far_future(text: str) -> tuple[bool, str | None]:
    """Determine if text describes a far-future forecast (>1 year).

    Uses simple boolean logic:
    - If multi-year timeframe present AND no quarterly language -> far-future
    - Otherwise -> NOT far-future

    Args:
        text: Text to analyze (typically headline or summary)

    Returns:
        Tuple of (is_far_future: bool, timeframe: str | None)
    """
    has_multi_year, timeframe = matches_multi_year_timeframe(text)
    has_quarterly = matches_quarterly_language(text)

    # Far-future if multi-year timeframe present and no quarterly exclusions
    if has_multi_year and not has_quarterly:
        return True, timeframe

    return False, None
