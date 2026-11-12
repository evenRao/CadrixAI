from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


UNIT_ALIASES = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
    '"': 25.4,
}

MEASUREMENT_RE = re.compile(
    r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|millimeters?|cm|centimeters?|in|inch|inches|\")\b",
    re.IGNORECASE,
)
TRIPLE_RE = re.compile(
    r"(?P<a>-?\d+(?:\.\d+)?)\s*[xX]\s*(?P<b>-?\d+(?:\.\d+)?)\s*[xX]\s*(?P<c>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|millimeters?|cm|centimeters?|in|inch|inches|\")\b",
    re.IGNORECASE,
)
PAIR_RE = re.compile(
    r"(?P<a>-?\d+(?:\.\d+)?)\s*[xX]\s*(?P<b>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|millimeters?|cm|centimeters?|in|inch|inches|\")\b",
    re.IGNORECASE,
)
ANGLE_RE = re.compile(r"(?P<value>-?\d+(?:\.\d+)?)\s*(?:deg|degree|degrees)\b", re.IGNORECASE)
INTEGER_RE = re.compile(r"(?P<value>-?\d+)\b")


@dataclass(frozen=True)
class Measurement:
    value_mm: float
    raw_value: float
    unit: str
    start: int
    end: int


def normalize_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.strip().lower())


def unit_to_mm(value: float, unit: Optional[str]) -> float:
    if not unit:
        return value
    return value * UNIT_ALIASES.get(unit.lower(), 1.0)


def extract_measurements(prompt: str) -> list[Measurement]:
    measurements: list[Measurement] = []
    for match in MEASUREMENT_RE.finditer(prompt):
        raw_value = float(match.group("value"))
        unit = match.group("unit")
        measurements.append(
            Measurement(
                value_mm=unit_to_mm(raw_value, unit),
                raw_value=raw_value,
                unit=unit.lower(),
                start=match.start(),
                end=match.end(),
            )
        )
    return measurements


def extract_dimension_pair_mm(prompt: str) -> Optional[tuple[float, float]]:
    match = PAIR_RE.search(prompt)
    if not match:
        return None
    unit = match.group("unit")
    return (
        unit_to_mm(float(match.group("a")), unit),
        unit_to_mm(float(match.group("b")), unit),
    )


def extract_dimension_triple_mm(prompt: str) -> Optional[tuple[float, float, float]]:
    match = TRIPLE_RE.search(prompt)
    if not match:
        return None
    unit = match.group("unit")
    return (
        unit_to_mm(float(match.group("a")), unit),
        unit_to_mm(float(match.group("b")), unit),
        unit_to_mm(float(match.group("c")), unit),
    )


def extract_angle_degrees(prompt: str, labels: Sequence[str] | None = None) -> Optional[float]:
    prompt = normalize_prompt(prompt)
    if labels:
        label_re = "|".join(re.escape(label) for label in labels)
        patterns = (
            rf"(?P<value>-?\d+(?:\.\d+)?)\s*(?:deg|degree|degrees)\s*(?:{label_re})",
            rf"(?:{label_re})[^\d-]{{0,20}}(?P<value>-?\d+(?:\.\d+)?)\s*(?:deg|degree|degrees)",
        )
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return float(match.group("value"))
    match = ANGLE_RE.search(prompt)
    if match:
        return float(match.group("value"))
    return None


def extract_labeled_length_mm(prompt: str, labels: Sequence[str]) -> Optional[float]:
    prompt = normalize_prompt(prompt)
    label_re = "|".join(re.escape(label) for label in labels)
    patterns = (
        rf"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|millimeters?|cm|centimeters?|in|inch|inches|\")?\s*(?:{label_re})\b",
        rf"(?:{label_re})\b[^\d-]{{0,20}}(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|millimeters?|cm|centimeters?|in|inch|inches|\")?",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            value = float(match.group("value"))
            unit = match.groupdict().get("unit")
            if unit:
                return unit_to_mm(value, unit)
            return value
    return None


def extract_labeled_integer(prompt: str, labels: Sequence[str]) -> Optional[int]:
    prompt = normalize_prompt(prompt)
    label_re = "|".join(re.escape(label) for label in labels)
    patterns = (
        rf"(?P<value>-?\d+)\s*(?:{label_re})\b",
        rf"(?:{label_re})\b[^\d-]{{0,20}}(?P<value>-?\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return int(match.group("value"))
    return None


def has_any(prompt: str, keywords: Iterable[str]) -> bool:
    normalized = normalize_prompt(prompt)
    return any(keyword.lower() in normalized for keyword in keywords)


def extract_size_word(prompt: str) -> Optional[str]:
    normalized = normalize_prompt(prompt)
    for word in ("small", "medium", "large"):
        if re.search(rf"\b{word}\b", normalized):
            return word
    return None


def coerce_bool_feature(prompt: str, positive: Sequence[str], negative: Sequence[str] | None = None) -> Optional[bool]:
    normalized = normalize_prompt(prompt)
    if negative and has_any(normalized, negative):
        return False
    if has_any(normalized, positive):
        return True
    return None
