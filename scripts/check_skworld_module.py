#!/usr/bin/env python3
"""Validate SKWorld examples and the v1.1 to v1.3 compatibility boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[1] / "reference/skworld-module"


def main() -> int:
    schema = json.loads((ROOT / "skworld.module.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    legacy = json.loads((ROOT / "skworld.module.example.json").read_text(encoding="utf-8"))
    pack = json.loads((ROOT / "skworld.module.pack-example.json").read_text(encoding="utf-8"))
    profile = json.loads(
        (ROOT / "skworld.module.control-plane.example.json").read_text(encoding="utf-8")
    )
    for document in (legacy, pack, profile):
        validator.validate(document)
    for version in ("1.1", "1.2"):
        compatible = copy.deepcopy(legacy)
        compatible["schemaVersion"] = version
        validator.validate(compatible)
    _must_fail(validator, profile, ("schemaVersion",), "1.2")
    _must_fail(validator, profile, ("controlPlane", "openapi"), "https://other.test/x")
    _must_fail(validator, profile, ("controlPlane", "openapi"), "/api/v1/../private")
    _must_fail(validator, profile, ("auth", "scopes"), ["secret material"])
    print("SKWorld module schema and compatibility checks passed")
    return 0


def _must_fail(
    validator: Draft202012Validator,
    source: dict,
    path: tuple[str, ...],
    value: object,
) -> None:
    changed = copy.deepcopy(source)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    if not list(validator.iter_errors(changed)):
        raise AssertionError(f"negative control unexpectedly passed: {'.'.join(path)}")


if __name__ == "__main__":
    raise SystemExit(main())
