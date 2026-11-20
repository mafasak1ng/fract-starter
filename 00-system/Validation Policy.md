---
node_id: "validation-policy"
title: "Validation Policy"
type: "policy"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Documented what the read-only validator checks and when to run it."
review_status: "needs_review"
tags:
  - "system"
  - "validation"
  - "policy"
aliases:
  - "Validator"
previous: "[[00-system/Metadata Standard|Metadata Standard]]"
next: "[[00-system/Layer Guard|Layer Guard]]"
---
# Validation Policy

The validator is the vault's single structural check. It is a Python script that uses only the standard library, reads the vault and reports what is wrong. It never changes a file and never leaves a cache behind.

## Command

From the vault root:

```bash
python -B code/validation/validate.py
```

Options:

- `--root PATH` checks a different vault, such as a linked project vault.
- `--quiet` prints only the findings and the summary.

Each finding is one line, `ERROR <path>: <message>` or `WARN  <path>: <message>`, and the run ends with a summary line: `N errors, M warnings, K notes checked`. The exit code is `0` when there are no errors and `1` when there is at least one. Warnings never change the exit code.

The validator's own tests run with:

```bash
python -B -m unittest discover -s code/validation/tests
```

## Errors

An error means the vault is broken and must be fixed before work is called done.

- **Metadata.** A note without frontmatter, or with a missing or invalid required field: an unknown `type`, `status`, `change_type` or `review_status`; a `version` that is not semver; a date that is not `YYYY-MM-DD`; `updated` before `created`; `revision` below 1; a `node_id` that is not lowercase kebab-case; an empty `tags` list. The fields are defined in [[00-system/Metadata Standard|Metadata Standard]].
- **Duplicate `node_id`.** Two notes with the same id.
- **Broken links.** A wikilink in the body, or in `parent`, `previous` or `next`, that does not resolve to an existing file. Labels after `|` and headings after `#` are ignored when resolving. Links inside fenced code blocks and inline code are not checked, so templates and examples may show sample links.
- **Skills.** A `.agents/skills/<name>/SKILL.md` without `name` or `description`, or whose `name` differs from its folder.
- **Residue.** Zero-byte files; forbidden names such as `Untitled*`, `* copy*`, `*.bak`, `*.orig`, `*~` and numbered copies like `Note (1).md`; any `__pycache__` folder or `*.pyc` file.
- **Code and data.** Every `*.json` must parse, and every `*.py` must compile. Compilation runs in memory and writes no bytecode.

## Warnings

A warning points at something worth a look but does not block work.

- **Size.** A note outside the character range of its `type`, frontmatter included. The ranges are listed in [[00-system/Agent Instructions|Agent Instructions]]. A note far over its range is a signal to split it into a hub and children.
- **Orphans.** A note that no other note links to, except the root `README.md`. Link it from its parent index or hub.

## What is not scanned

`.git/`, `.obsidian/`, `_atlas/audit/` and `LICENSE` are skipped. Skill files are exempt from the note metadata and checked only for their two fields.

## When to run it

- After every structural change: a new, moved, renamed or deleted note; a changed link or `parent`; any edit to frontmatter.
- Before a commit, and always before a kernel commit.
- At the end of a session, so the record can quote the summary line in its `summary5`.
- When opening an unfamiliar vault, to see its state before changing anything.

## How to respond to findings

1. Fix every error the current change introduced.
2. Report errors that were already there, with their paths, instead of silently changing files outside the task's scope.
3. Treat warnings with judgment: link orphans, split oversized notes, and leave a short reason in the report when a warning stays.
4. Never edit the validator to make a finding disappear. A rule changes only by an owner-approved change to this policy and the script together.

## Completion gate

A task is complete only when the validator reports zero errors that the task introduced, the full Git diff has been reviewed, and no residue was left behind. Passing validation does not approve anything: `review_status` moves to `approved` only by the owner's decision.
