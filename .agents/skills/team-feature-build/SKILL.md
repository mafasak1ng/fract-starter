---
name: team-feature-build
description: Team template for building or changing a feature in code - a planner writes acceptance criteria and a file-ownership manifest, a test writer writes failing tests first, one implementer per disjoint file set makes them pass, and a verifier checks the result before it is applied. Load when the owner asks for new or changed behaviour in code; for a defect use team-bug-hunt instead.
---

# Feature build team

## Purpose

Build new behaviour in small, test-first units, with each file written by exactly one agent and every result checked before it reaches the owner.

## When to use

- New or changed behaviour in `code/` (Python scripts, the Node commit guard, setup tools) or in a linked project's code.

## When not to use

- A defect: use `team-bug-hunt`.
- A change under about 50 lines in one file: one agent with a test is enough.
- Kernel code (`code/git-hooks/**`): the team may only propose the change as text (`layer-guard-rules`).

## Roles

| Role | Count | Tier | Access | Produces |
|---|---|---|---|---|
| Planner (lead) | 1 | strong | writes the plan in the report only | Design, acceptance criteria, manifest, unit order |
| Test writer | 1 | mid | writes test files only | Failing tests that encode the acceptance criteria |
| Implementer | 1-3, one per file set | mid | writes only its manifest paths | Code that makes the tests pass |
| Verifier | 1 | independent | read-only | Verdict on the finished change (`verifier`) |

Lanes: test writer plus 1-3 implementers, so 2-4 writing lanes in total.

## Procedure

1. **Design.** The planner writes: the goal; the acceptance criteria as checkable statements; the files to change; what is out of scope; the risks.
2. **Manifest.** One line per writer, for example:

   ```text
   implementer-1: code/setup/new_project.py
   implementer-2: code/validation/validate.py
   test-writer:   code/setup/tests/test_new_project.py, code/validation/tests/test_validate.py
   ```

   No path appears twice. No kernel path appears at all.
3. **Small units.** Split the work into units of about 200 changed lines or fewer. Each unit is planned, tested, built and checked before the next starts.
4. **Tests first.** The test writer writes tests that fail for the right reason before any implementation exists, and shows the failing run.
5. **Brief and implement.** Brief each implementer (`team-assembly` step 6). Each changes only its manifest paths until the tests pass. An implementer that needs a path it does not own stops and asks the planner.
6. **Self-check per unit.** Run the unit's tests and `python -B code/validation/validate.py`.
7. **Review.** The planner reads the diff, confirms `git diff --stat` matches the manifest, then sends the change to the verifier.
8. **Hand over** to `team-code-review` for a larger change, then report with `handoff-report`.

## Done when

- Every acceptance criterion maps to a passing test.
- The tests failed before the change (shown) and pass after it.
- `git diff --stat` matches the manifest exactly, with no kernel path.
- `python -B code/validation/validate.py` exits 0.
- No `__pycache__`, `.pyc` or other residue appears in `git status`.

## Rules

- Standard library only (Python 3.11+, Node 18+ built-ins). A new dependency needs the owner's yes and a pinned version.
- Python uses `pathlib` and `encoding="utf-8"`, never hard-coded separators, never `shell=True`. Run Python with `-B`.
- Node scripts use `node:path` and `node:fs`; no shell-specific syntax.
- Changed notes stay `review_status: "needs_review"`. Lanes never commit.
