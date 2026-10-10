"""Dataset-specific seizure parsers and half-open time intervals in seconds."""

from __future__ import annotations
from dataclasses import dataclass
import re
import numpy as np
from eeg_dataset_explorer.signals import signal_array, sampling_rate


@dataclass(frozen=True, order=True)
class Interval:
    start: float
    stop: float

    def __post_init__(self) -> None:
        if not np.isfinite([self.start, self.stop]).all() or self.start < 0 or self.stop <= self.start:
            raise ValueError("Require finite 0 <= start < stop")


def parse_chbmit(text: str) -> dict[str, list[Interval]]:
    """Parse summary text, including zero-seizure records; reject incomplete blocks."""
    result = {}
    for block in re.split(r"(?=File Name:)", text):
        name = re.search(r"File Name:\s*(\S+)", block)
        if not name:
            continue
        count = re.search(r"Number of Seizures in File:\s*(\d+)", block)
        starts = re.findall(r"Seizure(?:\s+\d+)? Start Time:\s*(\d+(?:\.\d+)?)\s*seconds", block)
        stops = re.findall(r"Seizure(?:\s+\d+)? End Time:\s*(\d+(?:\.\d+)?)\s*seconds", block)
        if count is None or len(starts) != int(count[1]) or len(stops) != int(count[1]):
            raise ValueError(f"Incomplete annotation block: {name[1]}")
        if name[1] in result:
            raise ValueError("Duplicate recording block")
        result[name[1]] = [Interval(float(a), float(b)) for a, b in zip(starts, stops)]
    if not result:
        raise ValueError("No CHB-MIT file blocks found")
    return result


def clock_seconds(value: str) -> int:
    """Accept HH.MM.SS or HH:MM:SS, including hours >=24 in dataset text."""
    match = re.fullmatch(r"(\d{1,3})[.:](\d{2})[.:](\d{2})", value.strip())
    if not match:
        raise ValueError("Invalid clock value")
    h, m, s = map(int, match.groups())
    if m >= 60 or s >= 60:
        raise ValueError("Invalid minutes or seconds")
    return h * 3600 + m * 60 + s


@dataclass(frozen=True)
class AnnotationAudit:
    """Accepted intervals and explicit rejected blocks; rejected data is never negative."""

    events: dict[str, list[Interval]]
    issues: list[dict[str, str]]


def _siena_clock(block: str, fields: list[str]) -> int | None:
    for field in fields:
        found = re.search(r"^\s*" + re.escape(field) + r":[ \t]*(.*)$", block, re.I | re.M)
        if found:
            # Siena contains mixed separators and a split-hour typo ("1 6.49.25").
            matches = re.findall(r"\d[\d ]*[.:]\d{2}[.:]\d{2}", found[1])
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous " + field + "; explicit source review required")
            return clock_seconds(matches[0].replace(" ", ""))
    return None


def audit_siena(text: str) -> AnnotationAudit:
    """Parse Siena variants while returning invalid/ambiguous events as issues.

    Reuse recording clocks for repeated events in the same named file. Accept
    PN01-style shared recording headers and abbreviated Start time/End time fields.
    Multiple proposed onset/end clocks are never selected silently. Preserve file
    names verbatim: reconcile any annotation/EDF alias explicitly before labeling.
    """
    events: dict[str, list[Interval]] = {}
    issues: list[dict[str, str]] = []
    registration: dict[str, tuple[int, int]] = {}
    current: str | None = None
    blocks = re.split(r"(?=Seizure\s+n\s*\d+)", text, flags=re.I)
    for index, block in enumerate(blocks):
        name = re.search(r"File name:\s*(\S+)", block, re.I)
        if name:
            current = name[1]
        seizure = re.search(r"Seizure\s+n\s*(\d+)", block, re.I)
        if current is None:
            if seizure:
                issues.append(
                    {"block": str(index), "recording": "unknown", "error": "Missing recording context"}
                )
            continue
        try:
            origin = _siena_clock(block, ["Registration start time"])
            finish = _siena_clock(block, ["Registration end time"])
            if (origin is None) != (finish is None):
                raise ValueError("Incomplete registration clocks")
            if origin is not None:
                if current in registration and registration[current] != (origin, finish):
                    raise ValueError("Conflicting registration clocks for the same recording")
                registration[current] = (origin, finish)
            if not seizure:
                continue
            if current not in registration:
                raise ValueError("Missing registration context")
            origin, finish = registration[current]
            begin = _siena_clock(block, ["Seizure start time", "Start time"])
            end = _siena_clock(block, ["Seizure end time", "End time"])
            if begin is None or end is None:
                raise ValueError("Missing seizure clocks")
            duration = (finish - origin) % 86400
            start = (begin - origin) % 86400
            stop = start + (end - begin) % 86400
            if duration == 0 or stop > duration:
                raise ValueError("Seizure falls outside stated recording duration")
            interval = Interval(float(start), float(stop))
            events.setdefault(current, []).append(interval)
        except ValueError as error:
            issues.append(
                {"block": seizure[1] if seizure else str(index), "recording": current, "error": str(error)}
            )
    if not events and not issues:
        issues.append({"block": "0", "recording": "unknown", "error": "No Siena seizure blocks found"})
    return AnnotationAudit(events, issues)


def parse_siena(text: str) -> dict[str, list[Interval]]:
    """Strict parser: reject the complete input if any event requires source review.

    Use audit_siena for partial ingestion with an explicit list of rejected blocks.
    Recording durations over 24 hours require external date-aware interpretation.
    """
    result = audit_siena(text)
    if result.issues:
        raise ValueError("; ".join(issue["recording"] + ": " + issue["error"] for issue in result.issues))
    return result.events


def window_labels(
    starts: np.ndarray, duration: float, events: list[Interval], minimum_overlap: float = 0.0
) -> np.ndarray:
    """Label windows by seizure overlap fraction; zero means any positive overlap."""
    starts = np.asarray(starts, dtype=float)
    if starts.ndim != 1 or not np.isfinite(starts).all() or np.any(starts < 0):
        raise ValueError("Expected finite nonnegative one-dimensional starts")
    if not np.isfinite(duration) or duration <= 0 or not 0 <= minimum_overlap <= 1:
        raise ValueError("Invalid duration or overlap fraction")
    ordered = sorted(events)
    if any(a.stop > b.start for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Merge overlapping events before labeling")
    overlap = np.zeros(len(starts))
    for event in ordered:
        overlap += np.maximum(0, np.minimum(starts + duration, event.stop) - np.maximum(starts, event.start))
    return (overlap > 0) & (overlap / duration >= minimum_overlap)


def segment(
    data: np.ndarray, fs: float, seconds: float = 2.0, stride: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """Return complete (windows, channels, samples) windows and start times; drop tail."""
    x = signal_array(data)
    sampling_rate(fs)
    if not np.isfinite([seconds, stride]).all() or min(seconds, stride) <= 0:
        raise ValueError("Positive window and stride required")
    width, step = round(seconds * fs), round(stride * fs)
    if min(width, step) < 1 or width > x.shape[1]:
        raise ValueError("Window or stride incompatible with recording")
    indices = np.arange(0, x.shape[1] - width + 1, step)
    return np.stack([x[:, i : i + width] for i in indices]), indices / fs
