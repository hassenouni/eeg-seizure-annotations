"""Inspect text seizure annotations, preserving rejected blocks and filename mismatches."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from .intervals import parse_chbmit, audit_siena


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotations", type=Path)
    parser.add_argument("--format", choices=["chbmit", "siena"], required=True)
    parser.add_argument("--recordings-root", type=Path)
    args = parser.parse_args()
    text = args.annotations.read_text(encoding="utf8")
    if args.format == "chbmit":
        events, issues = parse_chbmit(text), []
    else:
        audit = audit_siena(text)
        events, issues = audit.events, audit.issues
    missing = (
        []
        if args.recordings_root is None
        else [name for name in events if not (args.recordings_root / name).is_file()]
    )
    print(
        json.dumps(
            {
                "events": {
                    name: [{"start": e.start, "stop": e.stop} for e in values]
                    for name, values in events.items()
                },
                "rejected_blocks": issues,
                "unresolved_recording_names": missing,
            },
            indent=2,
        )
    )
    if issues or missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
