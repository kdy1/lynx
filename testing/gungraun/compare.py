#!/usr/bin/env python3
"""Build two revisions with one harness and report Gungraun instruction counts."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CASES = ("push", "reserve", "erase")
FLAGS = ("-std=c++17", "-O2", "-g", "-DNDEBUG")


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def read_counts(directory):
    counts = {}
    for path in Path(directory).rglob("summary.json"):
        data = json.loads(path.read_text())
        if str(data["version"]) != "7":
            raise ValueError(f"Unsupported summary schema: {data['version']}")
        case = data["id"]
        if case not in CASES or case in counts:
            raise ValueError(f"Unexpected or duplicate case: {case}")
        profiles = [p for p in data["profiles"] if p["tool"] == "Callgrind"]
        if len(profiles) != 1:
            raise ValueError(f"Expected one Callgrind profile: {case}")
        values = profiles[0]["data"]["total"]["metrics"]["Ir"]["values"]
        if set(values) != {"new", "old"}:
            raise ValueError(f"Missing comparison: {case}")
        if any(type(v) is not int or v <= 0 for v in values.values()):
            raise ValueError(f"Invalid instruction counts: {case}")
        counts[case] = {"base": values["old"], "head": values["new"]}
    if set(counts) != set(CASES):
        raise ValueError("Missing benchmark cases")
    return counts


def report(counts):
    base = sum(c["base"] for c in counts.values())
    head = sum(c["head"] for c in counts.values())
    # Equal case frequencies. Use integer arithmetic at gate boundaries.
    passed = head * 100 <= base * 99 and all(
        c["head"] * 100 < c["base"] * 101 for c in counts.values()
    )
    return {"metric": "Ir", "cases": counts, "frequency_per_case": 1,
            "portfolio_improvement_percent": (1 - head / base) * 100,
            "performance_gate": "pass" if passed else "not_passed"}


def main():
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    harness = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    refs = {k: os.environ[k.upper() + "_SHA"] for k in ("base", "head")}
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in refs.values()):
        raise ValueError("base/head must be full lowercase commit SHAs")
    metadata = {
        "repository": "kdy1/lynx", "comparison": refs,
        "workflow_sha": os.environ["GITHUB_SHA"],
        "run_url": f"https://github.com/kdy1/lynx/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        "compiler": run("clang++", "--version"), "flags": FLAGS,
        "rust": run("rustc", "--version"), "gungraun": "0.20.0",
        "valgrind": run("valgrind", "--version"), "architecture": run("uname", "-m"),
        "runner_image": os.environ.get("ImageVersion"),
        "harness_sha256": {str(p.relative_to(harness)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(harness.rglob("*"))
                           if p.is_file() and "target" not in p.parts and "__pycache__" not in p.parts},
        "boundary": "whole native process, including setup and destruction",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    env = dict(os.environ, LYNX_BENCH_BINARY=str(output / "vector"), GUNGRAUN_COLOR="never")
    for label, sha in refs.items():
        run("git", "-C", str(source), "fetch", "--no-tags", "origin", sha)
        run("git", "-C", str(source), "checkout", "--detach", sha)
        if run("git", "-C", str(source), "rev-parse", "HEAD") != sha:
            raise ValueError("Checkout SHA mismatch")
        for reference in (False, True):
            binary = output / ("reference" if reference else "vector")
            run("clang++", *FLAGS, "-I", str(source), str(harness / "vector.cc"),
                *(["-DLYNX_GUNGRAUN_REFERENCE"] if reference else []), "-o", str(binary))
        for case in CASES:
            if run(str(output / "vector"), case) != run(str(output / "reference"), case):
                raise ValueError(f"Checksum differs from std::vector: {label}/{case}")
        baseline = "--save-baseline=base" if label == "base" else "--baseline=base"
        with (output / f"{label}.log").open("w") as log:
            subprocess.run(["cargo", "bench", "--locked", "--manifest-path", str(harness / "Cargo.toml"),
                            "--bench", "native", "--", f"--home={output / 'profiles'}",
                            baseline, "--save-summary=json"], env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
    result = report(read_counts(output / "profiles"))
    result["same_sha_check"] = refs["base"] == refs["head"]
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["## Gungraun instruction counts", "", "| Case | Base Ir | Head Ir | Change |",
             "| --- | ---: | ---: | ---: |"]
    for name, values in result["cases"].items():
        delta = (values["head"] / values["base"] - 1) * 100
        lines.append(f"| {name} | {values['base']} | {values['head']} | {delta:+.3f}% |")
    lines += ["", f"Performance gate: **{result['performance_gate']}** (reporting only).",
              f"Same-SHA check: {result['same_sha_check']}.",
              "Whole-process counts; not wall-clock speed. See artifacts for exact revisions."]
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write("\n".join(lines) + "\n")
    # A same-SHA run checks reproducibility, not optimization acceptance.
    if result["same_sha_check"] and any(c["base"] != c["head"] for c in result["cases"].values()):
        raise ValueError("Same-SHA instruction counts differ; inspect profiles before optimization")


if __name__ == "__main__":
    main()
