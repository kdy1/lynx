# Gungraun comparisons on the fork

`.github/workflows/gungraun.yml` runs only in `kdy1/lynx`, on a GitHub-hosted
Ubuntu 24.04 runner. Pushes that change this harness or workflow run a same-SHA
reproducibility check. Once the workflow exists on the fork's default branch,
compare two full commit SHAs without opening an experiment PR:

```sh
gh workflow run gungraun.yml --repo kdy1/lynx --ref <workflow-branch> \
  -f base_ref=<40-character-base-sha> -f head_ref=<40-character-head-sha>
```

Both commits must be fetchable from the fork. The dispatch branch selects the
harness; it does not select either measured production revision. Keep that
branch revision fixed for related comparisons. All Actions reads and downloads
must also use `--repo kdy1/lynx`.

The initial suite measures `lynx::base::Vector<uint64_t>` push, reserved push,
and range erase. Each process runs 200 iterations with 1,024 input elements.
The C++ fixture is compiled directly with Clang because these Vector operations
are header-only. It does not need Habitat or GN. This is not a measurement of
all Lynx, styling, JavaScript, or a device UI. For other components, add an
appropriate fixture and use their documented GN targets and dependencies.

The harness, compiler options, case definitions, and runner stay identical for
base and head. Both executables use the production headers from their respective
commits. Each revision's result must match a separately compiled `std::vector`
reference before profiling. The compiler barrier prevents removal of repeated
work. Callgrind counts include process startup, allocation, setup, iteration,
checksum calculation, output, and destruction. Google Benchmark timer controls
do not define this measurement boundary.

Gungraun and its runner are pinned to 0.20.0; Cargo.lock pins harness dependencies.
The comparison reader accepts summary schema 7 and requires all three cases and
both sides of every instruction count. Missing data fails the job. Artifacts
contain metadata, logs, JSON summaries, native binaries, and raw Callgrind
profiles. `metadata.json` records exact SHAs, tool versions, flags, architecture,
harness hashes, and the run URL.

`comparison.json` reports the equal-frequency portfolio score using total head
Ir divided by total base Ir. The automatic performance gate requires at least
1% portfolio improvement and less than 1% regression in every case. Performance
rejection is reporting-only; it does not fail CI. Build failures, checksum
failures, invalid summaries, and unequal same-SHA counts fail CI. A green job
alone never authorizes an optimization PR. A same-SHA check is not a speedup.

Local validation (not performance evidence):

```sh
python3 -m unittest discover -s testing/gungraun -p 'test_*.py'
cargo check --locked --manifest-path testing/gungraun/Cargo.toml --benches
```

Use the repository's `gungraun-optimize` skill for profile-driven experiments
and publication. Accepted production patches go through `$create-pr` as draft
PRs to `lynx-family/lynx`, with the head branch in `kdy1/lynx`. Keep this fork's
skill and measurement infrastructure out of those upstream patches.
