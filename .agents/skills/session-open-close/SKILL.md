---
name: session-open-close
description: Open a working session by reading the rules, the recent journal and the repository state, and close it by writing tasks, knowledge and a journal session record with the five-part summary5. Load at the start and end of every working session, and when parallel sessions have lost or overwritten each other's work.
---

# Session open and close

## Purpose

Continuity between sessions. A session that starts must see what is in progress, what is free and what is blocked. A session that ends must write back its results, its durable knowledge and a journal record before it disappears. Without this, "what remains to be done" ends up scattered across many old notes that nobody reads, and parallel sessions collide on the same files.

## When to use

- At the start of every working session in the vault or in a linked project vault.
- At the end of every working session, including a stop forced by the session limits in `00-system/Agent Instructions.md`.
- When a session lost work, two sessions edited the same file, or a continuity setup needs an audit.

## When not to use

- For a single read-only question that changes nothing. Answer it; no journal record is needed unless the owner asks.

## Open procedure

1. Read, in order: `AGENTS.md`, `README.md`, `00-system/Agent Instructions.md`, `00-system/Metadata Standard.md`, `00-system/Validation Policy.md`.
2. Read `80-journal/Journal Index.md` and the latest one to three session records. Note every item under "Next action or completion declaration" that is still open.
3. If the work is in a linked project vault, read that vault's `AGENTS.md` and `README.md`, and check its row in `_atlas/registry/projects.json` (see `00-system/Project Vaults.md`).
4. Run `git status`. List files changed by someone else and leave them untouched. Another session may own them.
5. Run `python -B code/validation/validate.py` and record the error and warning counts as the baseline.
6. State to the owner, in a few lines: the open items found, what looks in progress elsewhere, the validator baseline, and the scope you propose for this session. Wait for the owner's goal if it is not already given.

## During the session

- Keep the prompt count and give the usage status the Agent Instructions require.
- Record decisions as they happen, not from memory at the end.
- Before editing a file another session may be using, check `git status` again.

## Close procedure

Close in this order, because it is the order in which things are easiest to lose:

1. **Tasks.** List what was finished, what is half-done with the exact step reached, and what is blocked and by what.
2. **Knowledge.** Move every durable fact or decision into the note that owns it, with full metadata, `review_status: "needs_review"` and a version bump. Do not leave knowledge only in the journal.
3. **Validate.** Run `python -B code/validation/validate.py`. Compare with the opening baseline; any new error is fixed or reported.
4. **Journal.** Create the session record in `80-journal/` from `00-system/templates/Session Record Template.md`, named as `80-journal/Journal Index.md` describes. Fill the five `summary5` parts from `80-journal/Summary5 Guide.md`:
   1. Intent and active scope
   2. Work performed
   3. Result or approved output
   4. Validation, risk, and unresolved information
   5. Next action or completion declaration
5. Link the new record from the Journal Index and, where the template provides them, set `previous` and `next` between consecutive records.
6. Run the validator once more and report the result to the owner. Do not commit unless the owner asks.

## Audit of a continuity setup

When the open and close keep failing, check:

- the open and close steps are written down where every agent reads them (`AGENTS.md` points at `00-system/Agent Instructions.md`);
- the open and close material contains no hardcoded personal path or project name, so it works in any vault;
- open items live in the latest session record's heading 5, not scattered through old records;
- parallel sessions never stash, reset or move another session's files; isolate your own work by path, never by moving theirs;
- after any automatic stash or rebase, `git status` is checked before continuing.

Repair only what is broken, outside the kernel, and record the audit in the session record.

## Outputs

- One session record per session in `80-journal/`, with the five `summary5` parts.
- Updated knowledge notes, each at `review_status: "needs_review"`.
- A short close message to the owner with the validator result and the next action.

## Rules

- A session record states only what happened in the session; anything else is `unknown` or `unverified` (`evidence-labels`).
- Never record a secret, a passkey, a credential value or personal data in the journal.
- A stop forced by the session limit still writes the journal record, with the half-done step stated exactly.
- Never claim a commit or push happened unless it did.
- Kernel files are never edited as part of a close (`layer-guard-rules`).
