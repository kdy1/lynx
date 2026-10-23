---
name: gungraun-optimize
description: Profile and optimize Lynx native code using Gungraun comparisons in kdy1/lynx GitHub Actions, then obtain human approval for each PR before publishing passing production changes as draft PRs to lynx-family/lynx. Use for requested instruction-count, cache, or allocation optimization and Gungraun regression investigations.
---

# Gungraun Optimize for Lynx

Use profiles to select one focused optimization, measure it without an experiment
PR, and publish only after correctness and performance gates pass and a human
approves that specific PR. This workflow adapts the [SWC Gungraun optimization skill](https://github.com/swc-project/swc-next/tree/main/.agents/skills/gungraun-optimize)
to Lynx's native code and fork/upstream split.

## Repository boundaries

- Run and inspect all Gungraun CI in **kdy1/lynx**. Specify `--repo kdy1/lynx`
  for workflow dispatch, run lookup, logs, and artifact downloads.
- Push measurement and publication branches only to the verified fork remote.
  Never push either repository's default branch.
- Obtain explicit human approval for each upstream PR before creating it, including
  draft PRs. Passing performance gates or approval for another PR is not approval
  to publish this PR.
- Publish approved optimization PRs to **lynx-family/lynx**, with a head branch
  in **kdy1/lynx**, and `draft: true`. Resolve the upstream default branch through
  GitHub (currently `develop`). Do not let `origin` determine the PR destination.
- Repository-skill and benchmark infrastructure maintenance belongs in the fork.
  It is not an upstream optimization PR. Creating or editing this skill does not
  start optimization or authorize additional publication.
- Use the installed `$create-pr` skill for every authorized publication. Resolve
  and read it before publishing; if unavailable, report the missing dependency.
  Do not substitute `gh stack submit` or `gh pr create` for that workflow.

## Establish the comparison

1. Read root and affected-path `AGENTS.md`, relevant `agents/` documents,
   `CONTRIBUTING.md`, and [the harness guide](../../../testing/gungraun/README.md).
   From this skill directory, repository paths start three levels above it.
2. Inspect the requested target, remotes, current work, and exact upstream base.
   Keep unrelated changes and PRs outside this task. Record the starting upstream
   SHA. A fork's default branch may contain patches absent upstream.
3. Inspect `.github/workflows/gungraun.yml` and `testing/gungraun/`. The initial
   harness covers only Vector push/reserve/erase. Do not claim it validates an
   unrelated optimization. Extend the fork-only harness for the requested target
   before editing production code; read [the CI reference](references/gungraun-ci.md).
4. Confirm GitHub authentication, fork Actions access, dispatch availability, and
   a successful same-SHA check with the chosen harness. Local runs establish
   correctness or harness startup only, never comparative performance.
5. Freeze the benchmark cases, primary metric, target portfolio, related cases,
   protected cases, and frequencies before measuring a hypothesis. Default to
   Callgrind `Ir` and equal case frequencies. Use cache or DHAT metrics for an
   explicitly relevant investigation, with matching harness/report support.
   Do not change weights or remove regressing cases after seeing results.

## Optimize and measure

- Inspect the retained profiles for expensive functions, repeated work, allocation,
  or locality problems. Choose a profile-supported hypothesis. Prefer fixing a
  shared helper at its definition instead of copying it into callers.
- Preserve semantics and public compatibility. Keep production changes portable
  unless the user requests a named architecture. The Linux runner does not grant
  permission to specialize production code for its CPU. For architecture-specific
  work, require matching-architecture CI that executes that path and scope claims
  to that target.
- Keep one focused production optimization commit per upstream PR. Read the
  affected code and run relevant correctness tests; use `testing/README_UT.md`
  for C++/RTF tests. The fixture checksum alone is not full correctness coverage.
- Keep measurement branches separate from publication branches. Start publication
  branches from the upstream base, without fork-only commits. Supply the same
  external harness to both production revisions; never copy optimized source
  into the base. If the target API does not exist on base, stop that comparison.
- Push provisional commits to the fork without a PR. Dispatch exact base/head
  SHAs. Compare against both the previous accepted production revision and the
  frozen starting base; one run suffices when these bases coincide.
- Match run event, workflow SHA, run ID, artifact SHAs, and harness hashes. Never
  select an unverified latest run. Ignore cancelled or superseded results.
  Retain metadata, logs, exact counts, and profile evidence.

## Apply the publication gate

A successful CI job is necessary, but is not the performance gate. The workflow
reports performance without failing the job for a regression.

- Require complete comparable cases and passing relevant correctness checks.
- For each incremental and cumulative comparison, compute
  `score = sum(frequency * head) / sum(frequency * base)` and improvement
  `1 - score`. Inspect individual target and related cases as well as the score.
- Automatically pass the performance gate only if both portfolios improve by at
  least 1% and every target and related case regresses by less than 1%. The initial CI report uses
  these thresholds for its three equal-frequency cases. Recompute for an expanded
  frozen portfolio; do not reuse its result for unmeasured cases.
- If a result is near a threshold or conflicts with profile evidence, repeat the
  same comparison once. Inconsistent results are inconclusive. Do not publish
  when counts are missing, workloads differ, a protected case fails, or the gate
  does not pass. Report the tradeoff; do not silently weaken thresholds.
- State Ir changes as executed-instruction changes, not elapsed-time speedups.
  Cache simulation and DHAT counts also require metric-specific claims.

## Publish and continue

For each accepted change, transfer only its production optimization and relevant
correctness tests to a clean upstream-based branch. Check the entire diff and
ancestry: fork-only skill, CI, benchmark plumbing, and rejected commits must not
be included. Verify measured and published production changes match. Record both
SHAs. If transfer changes production content or its base, remeasure before
publication.

Before invoking `$create-pr`, prepare the complete proposed diff, title, and body.
Show the human the target repository and base branch, head branch and exact SHA,
change summary, correctness results, both CI comparison links, metric changes,
and any regressions or limitations. Ask for approval to publish that specific
upstream draft PR, then wait. Explain that this skill requires approval for each
upstream PR. Silence, an earlier general optimization request, and approval of a
previous PR do not satisfy this step. If approval is declined or still pending,
keep the prepared branch on the fork without creating the upstream PR. If the
proposed diff, base, or head SHA changes after approval, present the revised
proposal and obtain approval again before creating it.

After that approval, hand `$create-pr` the approval and its exact scope along with
the explicit target `lynx-family/lynx`, head repository
`kdy1/lynx`, verified fork push remote and head branch, upstream base branch,
`draft: true`, exact intended commit, correctness results, both comparison URLs,
metrics, and measured/published SHA mapping. Include the repository-required AI
contribution disclosure and commit trailer. Link the returned PR to the thread.
Do not open a fork optimization PR as a substitute for the upstream draft.

A fork head branch cannot serve as the base branch of an upstream stacked PR.
Publish independent optimizations separately against upstream. If an optimization
depends on an unmerged predecessor, retain it on the fork and report that dependency
instead of publishing a multi-optimization diff or creating upstream branches
without authorization. Rebase and remeasure after its prerequisite lands.

Continue within the user's requested scope while safe profile-supported targets
remain. After two failed ideas on one hot path, inspect another profile-supported
target. Stop when scope is complete, no supported hypothesis remains, correctness
cannot be preserved, or measurement is blocked. Retry a transient Actions failure
once; report repeated failures. Do not replace CI evidence with local timings.

Report accepted draft PRs, exact metric changes and run links, rejected or
inconclusive attempts, correctness coverage, and blockers. Preserve accepted head
branches and evidence. Remove only task-owned temporary experiment branches after
recording their results; retain the permanent fork harness and workflow.
