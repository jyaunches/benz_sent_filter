"""Far-future forecast detection using pattern matching.

This module provides functions to detect far-future forecasts (>1 year) in headlines
by matching multi-year timeframe patterns and excluding near-term indicators.
"""

import re

# Precompiled regex patterns for conditional language detection
# Pattern dict maps pattern name to compiled regex for performance
CONDITIONAL_PATTERNS = {
    "plans to": re.compile(r"\bplans\s+to\b", re.IGNORECASE),
    "aims to": re.compile(r"\baims\s+to\b", re.IGNORECASE),
    "intends to": re.compile(r"\bintends\s+to\b", re.IGNORECASE),
    "seeks to": re.compile(r"\bseeks\s+to\b", re.IGNORECASE),
    "expected to": re.compile(r"\bexpected\s+to\b", re.IGNORECASE),
    "anticipated to": re.compile(r"\banticipated\s+to\b", re.IGNORECASE),
    "could": re.compile(r"\bcould\b", re.IGNORECASE),
    "may": re.compile(r"\bmay\b", re.IGNORECASE),
    "might": re.compile(r"\bmight\b", re.IGNORECASE),
    "would": re.compile(r"\bwould\b", re.IGNORECASE),
    "exploring": re.compile(r"\bexploring\b", re.IGNORECASE),
    "considering": re.compile(r"\bconsidering\b", re.IGNORECASE),
    "evaluating": re.compile(r"\bevaluating\b", re.IGNORECASE),
    "reviewing": re.compile(r"\breviewing\b", re.IGNORECASE),
    "potential": re.compile(r"\bpotential\b", re.IGNORECASE),
    "possible": re.compile(r"\bpossible\b", re.IGNORECASE),
    "looking to": re.compile(r"\blooking\s+to\b", re.IGNORECASE),
    "explore": re.compile(r"\bexplore\b", re.IGNORECASE),
    "consider": re.compile(r"\bconsider\b", re.IGNORECASE),
}


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


def matches_conditional_language(text: str) -> tuple[bool, list[str]]:
    """Detect conditional or hedging language patterns in text.

    Detects patterns indicating uncertainty, intention, or exploration rather
    than concrete commitments. Useful for distinguishing hedged future statements
    from definitive announcements.

    Pattern categories:
    - Intention: "plans to", "aims to", "intends to", "seeks to"
    - Expectation: "expected to", "anticipated to"
    - Modal uncertainty: "could", "may", "might", "would"
    - Exploration: "exploring", "considering", "evaluating", "reviewing"
    - Optionality: "potential", "possible", "looking to"

    Args:
        text: Text to analyze (typically headline)

    Returns:
        Tuple of (has_conditional: bool, matched_patterns: list[str])
        - has_conditional: True if any conditional patterns detected
        - matched_patterns: List of matched pattern names in dict iteration order
    """
    matched_patterns = []

    # Iterate through precompiled patterns and collect matches
    for pattern_name, compiled_regex in CONDITIONAL_PATTERNS.items():
        if compiled_regex.search(text):
            matched_patterns.append(pattern_name)

    # Return True with patterns if any matches, otherwise False with empty list
    if matched_patterns:
        return True, matched_patterns
    else:
        return False, []
