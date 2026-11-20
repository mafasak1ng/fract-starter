---
name: team-code-review
description: Team template for reviewing a local diff or branch - independent reviewers for correctness, vault conventions and silent failures, a history reader, and a consolidator that scores each issue and keeps only well-supported ones after verification. Works from Git alone, no hosted pull request needed. Load after a feature build or bug fix, or when the owner asks for a review of changes.
---

# Code review team

## Purpose

Catch real defects in a change before it is committed, with reviewers who do not see each other's work and a consolidator who keeps only issues that survive scoring and verification. The team is read-only.

## When to use

- After `team-feature-build` or `team-bug-hunt`.
- When the owner asks for a review of uncommitted work, a branch or a commit range.

## When not to use

- A diff of a few lines in one file: one reviewer is enough.
- Auditing notes across the whole vault: use `team-vault-audit`.

## Input

The lead fixes the range before anyone starts and records it in the report:

```text
git diff --stat <base>...<head>
git diff <base>...<head>
```

For uncommitted work use `git diff` and `git diff --staged`. A diff far above about 400 changed lines is split by file group into several reviews.

## Roles (lanes)

| Role | Count | Tier | Looks for |
|---|---|---|---|
| Correctness reviewer | 1 | mid | Wrong logic, unhandled cases, off-by-one, wrong types, broken interfaces between scripts |
| Conventions reviewer | 1 | independent | Breaks of `AGENTS.md`, `00-system/Agent Instructions.md`, `00-system/Metadata Standard.md`, `00-system/Validation Policy.md` and `layer-guard-rules` |
| Silent-failure hunter | 1 | mid | Errors swallowed by broad `except`, fallbacks that hide failure, checks that pass when nothing ran, missing exit codes |
| History reader | 1 | small | `git log` and `git blame` on touched lines: does the change undo an earlier deliberate fix or contradict a commit message or journal record? |
| Consolidator (lead) | 1 | strong | Deduplication, scoring, the final list |

Four read-only lanes plus the lead. For a small diff, merge the history reader into the correctness reviewer.

## Procedure

1. Brief each reviewer (`team-assembly` step 6) with the diff, the touched files and its focus, but not the other reviewers' output.
2. Each returns findings with `path:line`, severity, a one-line claim and a proof (`handoff-report`).
3. **Consolidate.** Merge duplicates, keep the clearest wording, note which reviewers found each issue.
4. **Score** each issue from 0 to 100: is it real, is it introduced or made worse by this diff, does it matter? Issues that already existed and are untouched by the diff are listed as `info`.
5. **Keep issues scoring 80 or more** and send them to the `verifier`. Keep those that survive.
6. **Report** with `handoff-report`: surviving issues first, then dropped ones with their scores and reasons.

## What reviewers check in this vault

- Python: `pathlib`, `encoding="utf-8"`, no `shell=True`, standard library only, runs with `-B`; the validator stays read-only.
- Node: built-ins only; the guard fails closed when a check cannot run.
- Notes: complete frontmatter, version and revision bumped, `review_status: "needs_review"`, path-qualified wikilinks that resolve, English text.
- Layers: no kernel path changed by an agent.
- Cross-OS: no Windows-illegal file names, no case-only renames without `git mv`, no shell-specific syntax in `code/git-hooks/pre-commit` beyond POSIX sh.
- Privacy: no secrets, passkey data, personal paths or personal data.

## Done when

- The range, the reviewers' tiers and every issue's score are in the report.
- Every reported issue has a verifier verdict.
- `python -B code/validation/validate.py` result on the reviewed state is recorded.

## Rules

- Reviewers change no file. Fixes are a separate task.
- A reviewer that finds nothing says so, with what it checked.
