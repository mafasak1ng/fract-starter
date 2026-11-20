---
node_id: "cognitive-index"
title: "Cognitive Index"
type: "index"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the cognitive domain index for the blank starter."
review_status: "needs_review"
tags:
  - "cognitive"
  - "index"
aliases: []
previous: "[[10-core/Core Index|Core Index]]"
next: "[[30-infrastructure/Infrastructure Index|Infrastructure Index]]"
---
# Cognitive Index

## Purpose

The cognitive domain holds how you and your agents think and learn: prompting patterns, reasoning methods, learning plans, evaluation of answers and the memory your agents load to stay consistent across sessions.

## What belongs here

- Prompt patterns and the reason each one works.
- Agent memory notes: standing preferences, lessons learned, recurring mistakes and their fixes.
- Learning plans and study notes, including Socratic learning sessions.

## What does not

- The skill files agents execute (those live in `.agents/skills/`).
- Session logs (those live in `80-journal`).
- Tool installation and setup (that is `30-infrastructure`).

## Naming

Name notes by the method or the lesson: `Prompt Pattern - Critique Then Revise.md`, `Lesson - Verify Before Claiming.md`. Prefixes group related notes in the file list without extra folders.

## Example

`20-cognitive/Standing Preferences.md`, type `policy`: the short list of preferences every agent should respect, each with the date it was set and why.

## Navigation

- Parent: [[00-system/System Hub|System Hub]]
- Previous: [[10-core/Core Index|Core Index]]
- Next: [[30-infrastructure/Infrastructure Index|Infrastructure Index]]
