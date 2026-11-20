---
name: team-bug-hunt
description: Team template for finding and fixing a defect - reproduce it first, investigate competing hypotheses in parallel read-only lanes, let one writer make the smallest fix with a regression test, and have an independent verifier confirm it before it is applied. Load when something is broken, a test or the validator fails, or behaviour differs between operating systems.
---

# Bug hunt team

## Purpose

Find the real root cause instead of the first plausible one, by having separate agents each chase a different hypothesis, and fix it with one small, tested change.

## When to use

- A test, the validator or the commit guard fails.
- A script behaves differently on Windows, Linux or macOS.
- A note or link structure is broken in a way the validator reports but the cause is unclear.

## When not to use

- The cause is already obvious from the error message: one agent fixes it with a regression test.
- New behaviour is wanted: use `team-feature-build`.

## Roles

| Role | Count | Tier | Access | Produces |
|---|---|---|---|---|
| Lead | 1 | strong | read-only | Reproduction, hypothesis list, arbitration, team report |
| Mapper | 1 | small | read-only | Map of the failing path: entry point, calls, data, config, recent commits |
| Investigator | 2-3 | mid | read-only | Evidence for and against one hypothesis each |
| Writer | 1 | mid | writes the agreed file set | The smallest fix plus a regression test |
| Verifier | 1 | independent | read-only | Verdict on root cause and fix (`verifier`) |

## Procedure

1. **Reproduce first.** The lead writes down the exact failing command, its working directory, the operating system and the output. No reproduction, no fix: report `NEEDS_CONTEXT` and stop.
2. **Map.** The mapper traces the failing path and lists the files involved, the last commits that touched them (`git log -n 20 -- <paths>`), and the inputs and config read.
3. **Hypotheses.** The lead writes 3-6 competing hypotheses, each from a different category:
   - logic error in the code;
   - data mismatch (note frontmatter against `00-system/Metadata Standard.md`, malformed JSON);
   - environment or operating system (paths, line endings, encoding, shell, letter case, tool version);
   - order or state (stale working tree, run order, leftover files);
   - policy or configuration (`_atlas/layers.json`, `.gitattributes`, `core.hooksPath`).
4. **Investigate in parallel.** Brief 2-3 investigators (`team-assembly` step 6), one hypothesis each, plus the reproduction, but not the lead's favourite. Each returns labelled evidence for and against (`evidence-labels`) and a distinguishing prediction: a command whose output differs if the hypothesis is true.
5. **Arbitrate.** The lead runs the distinguishing commands and ranks hypotheses by evidence: reproduction > trace or log > code reading > inference. Pick one root cause, or report that two remain.
6. **Fix.** The writer makes the smallest change that removes the root cause, and adds a regression test that fails before the fix and passes after it (locations in `team-test-writing`). No unrelated clean-up.
7. **Review and verify.** The lead reads the diff; the verifier checks root cause and fix, including another operating system's behaviour if the environment category was in play.
8. **Report** with `handoff-report`.

## Done when

- The original failing command now passes on the system where it failed.
- The regression test fails with the fix reverted and passes with it.
- `python -B code/validation/validate.py` exits 0.
- `git diff --stat` shows only the declared file set and no kernel path.
- The verifier verdict is `confirmed`, or `plausible` with confidence of at least 80.

## Failure handling

- The root cause is in a kernel file (for example `code/git-hooks/layer-guard.mjs`): write the proposed change into the report; the owner applies it through `kernel_commit.py`.
- Two hypotheses survive: report both with their evidence; do not fix on a guess.
- The fix loop fails twice: stop and report what was tried.

## Cross-OS notes

- Line endings: compare with `git diff --ignore-all-space` and check `.gitattributes` before blaming code.
- Paths: Python must use `pathlib`; a hard-coded separator is a common one-system bug.
- Encoding: Python on Windows reads files in the locale encoding unless told otherwise; a missing `encoding="utf-8"` is a frequent cause.
- Shell: `code/git-hooks/pre-commit` is POSIX sh; bash-only syntax works on one system and fails on another.
