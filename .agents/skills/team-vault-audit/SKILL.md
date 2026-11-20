---
name: team-vault-audit
description: Team template for auditing the notes of the vault - the validator runs first, then 2-4 section auditors check by domain what the validator cannot (link meaning, navigation, truthfulness, layer placement, file names, residue), and a verifier re-checks every finding. Load when the owner asks for a vault audit, after a large restructure, or before declaring a migration or handover complete.
---

# Vault audit team

## Purpose

A read-only health check of the knowledge base that goes beyond what the validator can detect. Fixes are a separate, owner-approved task.

## When to use

- The owner asks for an audit.
- After moving, renaming or splitting many notes.
- Before handing the vault, or a linked project vault, to someone else.

## When not to use

- A single failing validator error: fix it directly.
- Reviewing a code change: use `team-code-review`.

## Rule sources

Audit against these files, read fresh each time, not from memory:

- `AGENTS.md` and `00-system/Agent Instructions.md`
- `00-system/Metadata Standard.md`
- `00-system/Validation Policy.md`
- `00-system/Layer Guard.md` and the committed `_atlas/layers.json` (`git show HEAD:_atlas/layers.json`)
- `00-system/Project Vaults.md` and `_atlas/registry/projects.json`, if project vaults are in scope

## Roles

| Role | Count | Tier | Covers |
|---|---|---|---|
| Lead / consolidator | 1 | strong | Runs the validator, splits sections, merges and ranks findings |
| Section auditor | 2-4 | mid | A group of domains each, for example `00-system` and `10-core`; `20` to `50`; `60` to `80`; `90-assets` and `99-archive` |
| Verifier | 1 | independent | Re-checks every finding (`verifier`) |

## Procedure

1. **Validator first.** The lead runs `python -B code/validation/validate.py` and records every error and warning. Auditors cite these; they do not re-report them.
2. **Split** the domains into 2-4 groups, one per auditor, and brief each (`team-assembly` step 6). All auditors are read-only. Fixes to kernel files (`AGENTS.md`, `README.md`) are written as proposed text.
3. **Audit.** Each auditor checks its domains for what the validator cannot:
   - **Link meaning:** a link that resolves but points to the wrong note, or contradicts its target.
   - **Navigation:** `parent`, `previous` and `next` agree with the note's place in its domain index; every note is reachable from its domain index.
   - **Placement:** each note sits in the domain whose index says it belongs there; the `type` fits its content.
   - **Truth:** unknowns kept as `unknown`; no invented facts; open decisions marked `needs_review`.
   - **Review state:** changed notes at `review_status: "needs_review"`, versions and revisions bumped, `change_summary` meaningful.
   - **Language:** English text in maintained notes.
   - **Cross-OS names:** no `< > : " | ? *`, no trailing dot or space, no reserved names (`CON`, `NUL`, `COM1` and the rest), no case-only collisions, paths well under 260 characters.
   - **Residue and privacy:** no placeholders, empty sections, backups, numbered copies, caches, temp files, secrets or personal data.
4. **Verify.** The verifier re-checks each finding against the note and the rule source.
5. **Report** with `handoff-report`: findings grouped by domain and by rule, with counts per severity, then refuted items.

## Done when

- The validator result is recorded.
- Every in-scope domain has an auditor report.
- Every finding cites the rule it breaks (file and section) and has a verifier verdict.

## Rules

- No file is changed during the audit.
- A finding without a rule source is an opinion; label it `needs_review`, not as a defect.
