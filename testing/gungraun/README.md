# Gungraun comparisons on the fork

`.github/workflows/gungraun.yml` runs only in `kdy1/lynx`, on a GitHub-hosted
Ubuntu 24.04 x86-64 runner. Pushes that change the harness or workflow run the
complete native suite against the same SHA. Dispatch compares two full SHAs:

```sh
gh workflow run gungraun.yml --repo kdy1/lynx --ref <workflow-branch> \
  -f base_ref=<40-character-base-sha> -f head_ref=<40-character-head-sha> \
  -f suite=native -f dhat=true
```

Both commits must be fetchable from the fork. The dispatch branch selects the
frozen harness, not the measured production revision. Keep the workflow SHA fixed
for related comparisons. All run reads and downloads must use `--repo kdy1/lynx`.
The workflow must exist on the fork's default branch to enable dispatch.

## Included workloads

`suites/native.json` includes 16 representative cases using real Lynx code:

- Base: Vector push, reserved push, and range erase.
- Layout: Starlight Flex, Grid, and cached Flex layout of 64 children. Each case
  performs 100 layout requests and checks root and child geometry.
- Styling: class and descendant selector matching, CSS variable resolution,
  sparse Fiber invalidation, and legacy/new sparse descendant restyles.
- Runtime: Lepus value copying, array insertion, table insertion, and deep value
  conversion, from the existing telemetry benchmarks.

These cases cover specific paths, not every Lynx function. Device UI, platform
code, and JavaScript engine paths absent from these workloads need separate
fixtures and appropriate platform runners. To profile another path, add a suite
or case as described below. A successful suite does not validate unrelated code.

The native suite uses Habitat and GN to build the renderer/runtime dependencies.
It overlays only frozen benchmark plumbing from the workflow revision. Production
sources remain those of each measured SHA. Both revisions must support the same
fixtures and dependencies. Different compile commands or dependency revisions
require investigation before accepting a comparison.

`suites/vector.json` retains the lightweight, directly compiled Vector push,
reserved-push, and range-erase cases. Each runs 200 iterations with 1,024 elements
and compares its checksum with an independently compiled `std::vector` reference.
Use `-f suite=vector` to select it.

Select a frozen subset with comma-separated case IDs:

```sh
gh workflow run gungraun.yml --repo kdy1/lynx --ref <workflow-branch> \
  -f base_ref=<base-sha> -f head_ref=<head-sha> \
  -f suite=native -f cases=layout_flex,layout_grid,runtime_array
```

Unknown or duplicate IDs fail before building. Freeze the suite, selected cases,
frequencies, and tools before comparing an optimization. Do not remove regressing
cases after inspecting results. Selecting cases also limits the native module executables that are built.
Each selected executable still links its production dependency graph.

## Measurement boundary and correctness

Native cases use Callgrind client requests in the custom reporter. Collection
starts after Google Benchmark's context/system discovery and stops before report
validation/output. It includes fixture setup, execution, destruction, and the
benchmark runner between these boundaries. Vector cases count the whole process.
DHAT always measures the whole process. `PauseTiming` does not pause Valgrind.
Instruction counts are not wall-clock speedups.

A same-SHA check builds once and profiles that binary independently twice. It
checks measurement reproducibility, not build reproducibility. Comparisons of
different SHAs always build each revision from clean outputs.

The repository pins Google Benchmark to a version whose runner starts with one
iteration. `--benchmark_min_time=0 --benchmark_repetitions=1` stops adaptive
iteration growth. A custom reporter requires exactly one successful benchmark
report with exactly one iteration, rejects skipped/error cases, and prints a
stable `ok` instead of timing-dependent output. Nonfatal engine logging is
disabled to exclude address/timestamp formatting. Fixture errors, fatal logs,
and GTest assertion failures still fail validation. Existing fixture validation is
preserved. Timer-control calls are removed from the frozen telemetry copies;
they do not define the Callgrind boundary, and some legacy fixtures leave the
timer paused at loop exit. A selected benchmark with explicit iterations other
than one fails
this reporter; add a dedicated fixed-work fixture for such a case.

This execution/fixture validation does not replace relevant unit tests. The
native profiling fixtures are discovery workloads; each optimization still needs
the correctness coverage required by `testing/README_UT.md`.

## Register another native executable or GN target

Add `suites/<name>.json` to the frozen workflow branch. Build commands are argv
arrays. `{source}`, `{harness}`, and `{build}` expand to absolute paths. No shell
expansion occurs. Use a harness-owned script for multi-step GN/Habitat setup.
For example:

```json
{
  "build": [
    ["python3", "{harness}/build_component.py", "{source}", "{build}"]
  ],
  "cases": [
    {
      "id": "component_parse",
      "binary": "{build}/parse_fixture",
      "args": ["--iterations=1000"],
      "cwd": "{source}",
      "env": {"LANG": "C"},
      "expected_stdout": "validated-checksum",
      "frequency": 1
    }
  ]
}
```

Dispatch with `-f suite=<name>`. IDs must be unique ASCII identifiers of at most
120 characters. Frequencies are positive integers and default to one. Every case
must have either `expected_stdout` or a `reference` argv array. Both revisions
must produce the validated output. Set `instrumented: true` only for binaries that explicitly start and stop
Callgrind instrumentation; other binaries count the whole process.
Use deterministic fixtures, fixed iteration
counts, and observable outputs. Link the production implementation rather than a
copy or simplified replacement. Build each revision from clean build outputs.

The common runner supports arbitrary Linux native executables. Platform-specific
components still require their SDKs and matching runners; registering a target
does not make it portable to Linux.

## Evidence and gates

Gungraun and its runner are pinned to 0.20.0; Cargo.lock pins dependencies. The
reader accepts schema 7 and requires exactly the selected cases with positive
base/head `Ir` counts. Missing, unexpected, duplicate, or incomplete cases fail.
The results directory must be empty to prevent reuse of stale profiles.

Callgrind always enables cache and branch simulation. `dhat=true` adds allocation
profiles. Raw profiles, all tool metrics (`metrics.json`), logs, validation
outputs, and binaries from both revisions are retained. Native builds retain unstripped ELF binaries with source/debug symbols,
GN arguments, compile commands, and the actual compiler version. The compiler
cache checks compiler contents and normal ccache inputs; it does not reuse
objects for changed inputs. Cache entries are saved on failed builds too. `metadata.json`
records exact production/workflow SHAs, run URL, suite selection, frequencies,
tools, runner image, architecture, and frozen harness/telemetry hashes.

`comparison.json` uses `sum(frequency * head Ir) / sum(frequency * base Ir)`.
The automatic gate requires at least 1% portfolio improvement and less than 1%
regression in every selected case. Cache and DHAT results are retained for
inspection; this gate evaluates only `Ir`. Use metric-specific claims and a
separate frozen portfolio calculation for cache or allocation investigations.
Performance rejection is reporting-only. Build/validation failures, invalid
summaries, and unequal same-SHA instruction counts fail CI. A green job alone
does not authorize an optimization PR.

Local validation (not comparative performance evidence):

```sh
python3 -m unittest discover -s testing/gungraun -p 'test_*.py'
cargo check --locked --manifest-path testing/gungraun/Cargo.toml --benches
```

Use the repository's `gungraun-optimize` skill for experiments. After correctness
and performance gates pass, obtain explicit approval for each upstream draft PR
and publish through `$create-pr`. Keep this fork's skill, CI, and measurement
plumbing out of upstream production patches.
