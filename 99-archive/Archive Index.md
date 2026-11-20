---
node_id: "archive-index"
title: "Archive Index"
type: "index"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the archive domain index for the blank starter."
review_status: "needs_review"
tags:
  - "archive"
  - "index"
aliases: []
previous: "[[90-assets/Assets Index|Assets Index]]"
---
# Archive Index

## Purpose

The archive domain keeps notes that are no longer active but still worth keeping: retired policies, finished projects and superseded designs. Archived notes stay readable and linkable, but no agent treats them as current instructions.

## What belongs here

- Notes whose `status` is `deprecated`, moved here with their links updated.
- Closed project summaries kept for reference.
- Superseded versions of a design, when the reasoning matters and Git history is not enough.

## What does not

- Backup copies of active notes: Git is the recovery layer.
- Notes that are merely unfinished (keep them as `draft` in their domain).
- Anything you would delete if it were not for fear: delete it, Git remembers.

## Naming

Keep the original filename when you archive a note, so its history stays easy to trace. Add a short line at the top saying what replaced it, with a link.

## Example

`99-archive/Old Review Checklist.md`, type `policy`, status `deprecated`: the checklist used before the current one, with a first line linking to its replacement.

## Navigation

- Parent: [[00-system/System Hub|System Hub]]
- Previous: [[90-assets/Assets Index|Assets Index]]
