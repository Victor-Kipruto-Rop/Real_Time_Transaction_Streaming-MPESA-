#!/usr/bin/env python3
"""Sanity-check service catalog IDs and referenced repository paths."""
from pathlib import Path
import sys
try:
    import yaml
except ImportError:
    print("Install PyYAML: python -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)
root = Path(__file__).resolve().parents[1]
repo = root.parent
catalog = yaml.safe_load((root / "service-catalog.yaml").read_text(encoding="utf-8"))
errors = []
if catalog.get("schemaVersion") != 1:
    errors.append("schemaVersion must equal 1")
for group in ("frontends", "services"):
    items = catalog.get(group, [])
    ids = [item.get("id") for item in items]
    if any(not value for value in ids):
        errors.append(group + ": every entry must have an id")
    if len(ids) != len(set(ids)):
        errors.append(group + ": duplicate IDs")
    for item in items:
        path = item.get("path")
        if path and not (repo / path).exists():
            errors.append("missing path: " + path)
if errors:
    print("\n".join("ERROR: " + error for error in errors), file=sys.stderr)
    raise SystemExit(1)
print("Infrastructure catalog sanity check passed.")
