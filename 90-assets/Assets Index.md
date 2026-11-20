---
node_id: "assets-index"
title: "Assets Index"
type: "index"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the assets domain index for the blank starter."
review_status: "needs_review"
tags:
  - "assets"
  - "index"
aliases: []
previous: "[[80-journal/Journal Index|Journal Index]]"
next: "[[99-archive/Archive Index|Archive Index]]"
---
# Assets Index

## Purpose

The assets domain stores the files that notes point to: images, diagrams, canvases, PDFs and exports. Notes in other domains explain an asset; this domain keeps it in one predictable place.

## What belongs here

- Images, diagrams and screenshots, in subfolders by type or topic.
- Obsidian canvases that map a domain or a project.
- Registers that list what each asset is, where it came from and which note uses it.

## What does not

- Large binaries better kept outside Git, such as raw video or model weights.
- Files with personal data or secrets.
- Unused files: every asset should be linked from at least one note.

## Naming

Use lowercase kebab-case filenames with a meaningful stem: `planning-loop-diagram.png`, `workstation-wiring.jpg`. Never keep numbered or `copy` variants; Git keeps the history.

## Example

`90-assets/Asset Register.md`, type `record`: a table of every asset with its path, source, licence and the notes that link to it.

## Navigation

- Parent: [[00-system/System Hub|System Hub]]
- Previous: [[80-journal/Journal Index|Journal Index]]
- Next: [[99-archive/Archive Index|Archive Index]]
