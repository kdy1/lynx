"""Load frozen native workloads. Commands are argv arrays, never shell strings."""

import json
from pathlib import Path
import re


def load_suite(harness, name, selected=""):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        raise ValueError("Invalid suite name")
    suite = json.loads((Path(harness) / "suites" / f"{name}.json").read_text())
    cases = suite["cases"]
    ids = [case["id"] for case in cases]
    if not ids or len(set(ids)) != len(ids) or any(
        not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,119}", i) for i in ids
    ):
        raise ValueError("Invalid or duplicate case IDs")
    for case in cases:
        if type(case.get("frequency", 1)) is not int or case.get("frequency", 1) <= 0:
            raise ValueError("Case frequencies must be positive integers")
        if ("reference" in case) == ("expected_stdout" in case):
            raise ValueError("Each case needs reference or expected_stdout validation")
    if selected:
        wanted = selected.split(",")
        if len(set(wanted)) != len(wanted) or set(wanted) - set(ids):
            raise ValueError("Unknown or duplicate selected cases")
        suite["cases"] = [case for case in cases if case["id"] in wanted]
    return suite


def resolve(value, paths):
    if isinstance(value, str):
        for key, path in paths.items():
            value = value.replace("{" + key + "}", str(path))
        return value
    if isinstance(value, list):
        return [resolve(v, paths) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v, paths) for k, v in value.items()}
    return value
