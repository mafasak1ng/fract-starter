---
node_id: "summary5-guide"
title: "Summary5 Guide"
type: "guide"
parent: "[[80-journal/Journal Index|Journal Index]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Defined the five-part session close for the blank starter."
review_status: "needs_review"
tags:
  - "journal"
  - "session"
  - "summary5"
aliases:
  - "summary5"
---

# Summary5 Guide

`summary5` is the five-part close every session ends with. It is short on purpose: a reader who opens only this block should know what the session was for, what changed, whether it can be trusted, and what happens next. Write it at the end of the session record (see [[00-system/templates/Session Record Template|Session Record Template]]) and show it to the owner when the session closes.

## The five parts

1. **Intent and active scope.** What the session set out to do, in one or two sentences, and the boundary of the work: which folders, notes or features were in scope, and what was explicitly left out.
2. **Work performed.** What was actually done, as a short list of actions. Name the files created, changed or removed. Do not list intentions or attempts that left nothing behind, unless the failure itself matters.
3. **Result or approved output.** What exists now that did not before, and its state: approved by the owner, or still `needs_review`. Link the notes that carry the result.
4. **Validation, risk and unresolved information.** The checks that ran and their outcome (for example the validator's summary line), the risks you see, and every open question. Mark uncertain facts `unknown`, `unverified` or `needs_review` instead of guessing.
5. **Next action or completion declaration.** Either the single next step and who owns it, or a plain statement that the task is complete and nothing is pending.

## Rules

- Keep each part to a few lines. Detail belongs in the record's body, not in the summary.
- Report facts, not effort. "The validator reports 0 errors, 2 warnings" is useful; "worked hard on validation" is not.
- Never claim a check passed if it did not run. Say it did not run and why.
- Use the exact five headings, in order, so that agents and scripts can find them.

## Example

```text
1. Intent and active scope: add a review checklist to 10-core; scope 10-core only.
2. Work performed: created 10-core/Review Checklist.md; linked it from Core Index.
3. Result or approved output: checklist exists, review_status needs_review.
4. Validation, risk and unresolved information: validator 0 errors, 0 warnings;
   whether the checklist should cover code reviews is unknown.
5. Next action or completion declaration: owner reviews the checklist.
```

## Related

- [[00-system/Agent Instructions|Agent Instructions]] sets when a session must close.
- [[80-journal/Session Record - Example|Session Record - Example]] shows a full record.
