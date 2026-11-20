---
node_id: "system-hub"
title: "System Hub"
type: "hub"
parent: "[[README|FRACT]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the system hub that routes to every rule, standard and template."
review_status: "needs_review"
tags:
  - "system"
  - "hub"
aliases:
  - "System"
previous: "[[README|FRACT]]"
next: "[[10-core/Core Index|Core Index]]"
---
# System Hub

`00-system` holds the rules of the vault: how agents operate, what every note must contain, how the vault is checked and protected, and the templates new notes start from. Everything here applies to every other domain. Agents load the first three notes below on every session, after `AGENTS.md` and `README.md`.

## Rules and standards

| Note | Type | What it settles |
| --- | --- | --- |
| [[00-system/Agent Instructions|Agent Instructions]] | contract | Authority order, file rules, note sizes, review, session control, completion reports |
| [[00-system/Metadata Standard|Metadata Standard]] | policy | The frontmatter every note carries, field by field |
| [[00-system/Validation Policy|Validation Policy]] | policy | What the validator checks, errors versus warnings, when to run it |
| [[00-system/Layer Guard|Layer Guard]] | policy | The protected kernel, the commit guard, the passkey and the audit log |
| [[00-system/Project Vaults|Project Vaults]] | operations | Linked project vaults, how to create and check them, the registry |

## Templates

- [[00-system/templates/Note Template|Note Template]]: the starting point for any note.
- [[00-system/templates/Contract Template|Contract Template]]: for a note that binds a component or agent role.
- [[00-system/templates/Session Record Template|Session Record Template]]: for the record that closes each session.

## Domains

| Domain | Index | Holds |
| --- | --- | --- |
| `10-core` | [[10-core/Core Index|Core Index]] | Principles, definitions, reusable models |
| `20-cognitive` | [[20-cognitive/Cognitive Index|Cognitive Index]] | Prompting, reasoning, learning, agent memory |
| `30-infrastructure` | [[30-infrastructure/Infrastructure Index|Infrastructure Index]] | Machines, environments, services |
| `40-technical` | [[40-technical/Technical Index|Technical Index]] | Reusable technical knowledge, code design |
| `50-creative` | [[50-creative/Creative Index|Creative Index]] | Creative work and generation workflows |
| `60-business` | [[60-business/Business Index|Business Index]] | Offers, processes, decisions |
| `70-human` | [[70-human/Human Index|Human Index]] | Goals, routines, skills |
| `80-journal` | [[80-journal/Journal Index|Journal Index]] | Session records and `summary5` |
| `90-assets` | [[90-assets/Assets Index|Assets Index]] | Images, canvases, files notes link to |
| `99-archive` | [[99-archive/Archive Index|Archive Index]] | Retired notes |

## Tooling outside the notes

- Agent skills: the [skills README](../.agents/skills/README.md) lists every skill and how to load it.
- Validator: `python -B code/validation/validate.py`.
- Setup and kernel commits: `code/setup/init_vault.py`, `code/setup/kernel_commit.py`, `code/setup/new_project.py`.
- Layer policy and project registry: `_atlas/layers.json`, `_atlas/registry/projects.json`.

## Navigation

- Parent: [[README|FRACT]]
- Next: [[10-core/Core Index|Core Index]]
