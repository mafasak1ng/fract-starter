---
name: team-test-writing
description: Team template for writing or strengthening automated tests - a designer inventories the behaviours worth testing, one writer per test folder writes deterministic standard-library tests, and a weakness checker proves each test fails when the code is broken. Load when tests are missing, weak or flaky, or before a risky change.
---

# Test writing team

## Purpose

Tests that guard real behaviour and can be shown to fail, written with no extra dependencies and leaving no residue in the vault.

## When to use

- A script in `code/` has no tests or weak ones.
- A test is flaky.
- Before a risky change, to pin current behaviour.

## When not to use

- As part of a feature build: there the test writer is a lane of `team-feature-build`.
- For one missing test: one agent writes it and shows it failing against broken code.

## Test locations

| Suite | Folder | Framework |
|---|---|---|
| Validator | `code/validation/tests/` | Python `unittest` |
| Setup tools and guard | `code/setup/tests/` | Python `unittest` (the guard is driven through Git in a temporary repository) |
| Node scripts, if any are added | a `tests/` folder beside the script | `node:test` |

Tests use only the standard library: no pytest, no third-party property-testing package. Tests that need Git create their own repository with `tempfile` and clean it up; they never touch the vault's own repository.

## Roles

| Role | Count | Tier | Access | Produces |
|---|---|---|---|---|
| Test designer (lead) | 1 | strong | read-only | Behaviour inventory and test plan |
| Writer | 1-3, one per test folder | mid | writes its test folder only | Tests |
| Weakness checker | 1 | small | read-only; throw-away edits in the temp directory only | Proof that each test fails when the code is broken |

## Procedure

1. **Inventory.** The designer lists the behaviours worth testing from the code and from `00-system/Validation Policy.md` and `00-system/Layer Guard.md`. Each is marked unit, integration or end-to-end; most should be unit tests.
2. **Invariants.** For functions that take structured input, test invariants as well as examples: valid input never errors, a round-trip returns the input, a rule rejects every listed bad case.
3. **Brief and write.** Brief each writer (`team-assembly` step 6) with its folder and its behaviours. Tests are deterministic: fixed inputs or seeds, no network, no clock dependence, no dependence on the path separator.
4. **Prove they can fail.** For each new test, the weakness checker copies the code under test into the temp directory, breaks it the way the test claims to catch, and shows the test failing. Tests that still pass are rewritten or dropped.
5. **Run on more than one system** when possible, or state which was used.
6. **Review and report.** The lead reads the tests, confirms the writers stayed in their folders, and reports with `handoff-report`, listing every test and the behaviour it guards.

## How to run

From the vault root:

```text
python -B -m unittest discover -s code/validation/tests -t .
python -B -m unittest discover -s code/setup/tests -t .
node --test <folder>
```

`-B` stops Python writing bytecode caches. If a needed interpreter is missing (for example Node for the guard tests), the tests skip with a clear reason; report the skip, do not install anything without the owner's yes.

## Done when

- Every new test was shown failing against broken code and passing against the real code.
- All suites pass, and `git status` shows only the new or changed test files: no `__pycache__`, `.pyc` or temporary repositories.
- `python -B code/validation/validate.py` exits 0.

## Rules

- Writers change test files only. A defect found while testing is reported, not fixed in the same task.
- Never weaken an assertion to make a test pass.
