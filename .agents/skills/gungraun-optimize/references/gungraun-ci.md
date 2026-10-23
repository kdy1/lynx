# Fork CI measurement procedure

Use `testing/gungraun/README.md` and `.github/workflows/gungraun.yml` as the
implementation contract. `base_ref` and `head_ref` are required full SHAs;
`--ref` selects the workflow/harness branch. The initial workflow has no filter:
it always runs its three Vector cases.

```sh
gh workflow run gungraun.yml --repo kdy1/lynx --ref <workflow-branch> \
  -f base_ref=<base-sha> -f head_ref=<head-sha>
gh run list --repo kdy1/lynx --workflow gungraun.yml --event workflow_dispatch \
  --branch <workflow-branch> --json databaseId,headSha,createdAt,status,url
gh run view <verified-run-id> --repo kdy1/lynx
gh run download <verified-run-id> --repo kdy1/lynx --dir <evidence-directory>
```

Record the dispatch time and workflow SHA before selecting a run. Check
`metadata.json` for the requested comparison SHAs, repository, workflow SHA, and
harness hashes. Concurrent runs must be distinguished by their artifacts.
Wait only for task-owned runs; use the host's supported wait mechanism.

GitHub requires a manually dispatched workflow to exist on the default branch.
The fork PR that installs this workflow must land before dispatch is available.
Its path-filtered push trigger runs a same-SHA check before landing. Do not create
experiment PRs or push the default branch to bypass this prerequisite.

## Extend for another native target

The included Vector fixture uses only headers, so direct Clang compilation is
sufficient. For layout, styling, or runtime targets, inspect their GN dependencies
and existing telemetry cases. See `testing/telemetry/styling/css/README.md` and
`testing/README_UT.md` for repository build/test entry points. Use Habitat and the
required GN target when linking real Lynx components; do not benchmark a copied
or simplified replacement implementation.

Use a Gungraun binary benchmark around the native executable. Keep its iterations,
fixtures, compiler, flags, dependencies, and measurement boundary fixed across
revisions. The Rust wrapper is a runner, not a rewrite of the C++ implementation.
Use a dedicated small fixture with fixed iteration counts when an existing Google
Benchmark target adapts its work to elapsed time. `PauseTiming` does not pause
Callgrind collection. For region-specific counts, explicitly instrument and verify
the native collection boundary; otherwise describe the whole process being counted.

Copy only harness plumbing from the frozen workflow revision outside the measured
checkout. Reject comparisons whose base cannot compile or execute the same
workload. Protect inputs and outputs from compiler elimination and validate results.
Keep Gungraun library and runner versions equal. Update the locked dependency and
summary reader together when changing versions. Preserve raw profiles and logs
on failure, and reject missing, duplicate, new, or removed cases.

Use a Linux runner with Valgrind. Reuse public GitHub-hosted runners in the fork;
upstream's `lynx-*` runner labels need not be available there. Keep
`contents: read`, `persist-credentials: false`, and a repository guard. Never run
candidate code through `pull_request_target`. Do not introduce write tokens for
benchmark comments. Keep performance reporting separate from build/harness errors.

Official references:

- [Gungraun binary benchmarks](https://gungraun.github.io/gungraun/latest/html/benchmarks/binary_benchmarks/quickstart.html)
- [Gungraun baselines](https://gungraun.github.io/gungraun/latest/html/cli_and_env/baselines.html)
- [Manual Actions dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
