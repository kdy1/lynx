#!/usr/bin/env python3
"""Build two revisions with one harness and report Gungraun instruction counts."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import shutil

from suite import load_suite, resolve

CASES = ("push", "reserve", "erase")


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def read_counts(directory, cases=CASES):
    counts = {}
    for path in Path(directory).rglob("summary.json"):
        data = json.loads(path.read_text())
        if str(data["version"]) != "7":
            raise ValueError(f"Unsupported summary schema: {data['version']}")
        case = data["id"]
        if case not in cases or case in counts:
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
    if set(counts) != set(cases):
        raise ValueError("Missing benchmark cases")
    return counts


def report(counts, frequencies=None):
    frequencies = frequencies or {name: 1 for name in counts}
    base = sum(c["base"] * frequencies[name] for name, c in counts.items())
    head = sum(c["head"] * frequencies[name] for name, c in counts.items())
    # Frequencies are frozen in the suite. Use integers at gate boundaries.
    passed = head * 100 <= base * 99 and all(
        c["head"] * 100 < c["base"] * 101 for c in counts.values()
    )
    return {"metric": "Ir", "cases": counts, "frequencies": frequencies,
            "portfolio_improvement_percent": (1 - head / base) * 100,
            "performance_gate": "pass" if passed else "not_passed"}


def main():
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    harness = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Results directory must be empty; stale profiles are not comparable")
    refs = {k: os.environ[k.upper() + "_SHA"] for k in ("base", "head")}
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in refs.values()):
        raise ValueError("base/head must be full lowercase commit SHAs")
    suite_name = os.environ.get("SUITE", "vector")
    suite = load_suite(harness, suite_name, os.environ.get("CASES", ""))
    cases = [case["id"] for case in suite["cases"]]
    metadata = {
        "suite": suite_name, "workload": suite,
        "dhat": os.environ.get("LYNX_DHAT", "false"),
        "repository": "kdy1/lynx", "comparison": refs,
        "workflow_sha": os.environ["GITHUB_SHA"],
        "run_url": f"https://github.com/kdy1/lynx/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        "host_compiler": run("clang++", "--version"),
        "rust": run("rustc", "--version"), "gungraun": "0.20.0",
        "valgrind": run("valgrind", "--version"), "architecture": run("uname", "-m"),
        "runner_image": os.environ.get("ImageVersion"),
        "harness_sha256": {str(p.relative_to(harness)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(harness.rglob("*"))
                           if p.is_file() and "target" not in p.parts and "__pycache__" not in p.parts},
        "boundary": "Callgrind: instrumented cases use client requests; others count the whole process. DHAT: whole process",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    env = dict(os.environ, LYNX_CASES=str(output / "cases.json"), GUNGRAUN_COLOR="never")
    base_outputs = None
    for label, sha in refs.items():
        run("git", "-C", str(source), "fetch", "--no-tags", "origin", sha)
        run("git", "-C", str(source), "checkout", "--detach", sha)
        if run("git", "-C", str(source), "rev-parse", "HEAD") != sha:
            raise ValueError("Checkout SHA mismatch")
        build = output / "build"
        if build.exists():
            shutil.rmtree(build)
        build.mkdir()
        workload = resolve(suite, {"source": source, "harness": harness, "build": build})
        with (output / f"{label}-build.log").open("w") as log:
            for command in workload["build"]:
                subprocess.run(command, cwd=source, env=env, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
        resolved_cases = []
        outputs = {}
        for case in workload["cases"]:
            case = dict(case, args=case.get("args", []), cwd=case.get("cwd", str(source)),
                        env=case.get("env", {}))
            case_env = dict(env, **case["env"])
            actual = run(case["binary"], *case["args"], cwd=case["cwd"], env=case_env)
            expected = (run(*case["reference"], cwd=case["cwd"], env=case_env)
                        if "reference" in case else case["expected_stdout"].strip())
            if actual != expected:
                raise ValueError(f"Output validation failed: {label}/{case['id']}")
            outputs[case["id"]] = actual
            resolved_cases.append(case)
        if base_outputs is not None and outputs != base_outputs:
            raise ValueError("Workload outputs differ across revisions")
        base_outputs = outputs
        (output / f"{label}-validation.json").write_text(json.dumps(outputs, indent=2) + "\n")
        (output / "cases.json").write_text(json.dumps(resolved_cases, indent=2) + "\n")
        baseline = "--save-baseline=base" if label == "base" else "--baseline=base"
        with (output / f"{label}.log").open("w") as log:
            subprocess.run(["cargo", "bench", "--locked", "--manifest-path", str(harness / "Cargo.toml"),
                            "--bench", "native", "--", f"--home={output / 'profiles'}",
                            baseline, "--save-summary=json"], env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
        shutil.copytree(build, output / f"{label}-build")
    result = report(read_counts(output / "profiles", cases),
                    {c["id"]: c.get("frequency", 1) for c in suite["cases"]})
    (output / "metrics.json").write_text(json.dumps([
        json.loads(p.read_text()) for p in sorted((output / "profiles").rglob("summary.json"))
    ], indent=2) + "\n")
    result["same_sha_check"] = refs["base"] == refs["head"]
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["## Gungraun instruction counts", "", "| Case | Base Ir | Head Ir | Change |",
             "| --- | ---: | ---: | ---: |"]
    for name, values in result["cases"].items():
        delta = (values["head"] / values["base"] - 1) * 100
        lines.append(f"| {name} | {values['base']} | {values['head']} | {delta:+.3f}% |")
    lines += ["", f"Performance gate: **{result['performance_gate']}** (reporting only).",
              f"Same-SHA check: {result['same_sha_check']}.",
              "Not wall-clock speed. See metadata and artifacts for collection boundaries and exact revisions."]
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write("\n".join(lines) + "\n")
    # A same-SHA run checks reproducibility, not optimization acceptance.
    if result["same_sha_check"] and any(c["base"] != c["head"] for c in result["cases"].values()):
        raise ValueError("Same-SHA instruction counts differ; inspect profiles before optimization")


if __name__ == "__main__":
    main()
