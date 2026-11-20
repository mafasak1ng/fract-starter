---
node_id: "note-template"
title: "Note Template"
type: "template"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the general note template for the blank starter."
review_status: "needs_review"
tags:
  - "template"
  - "note"
aliases: []
---

# Note Template

Copy the block below into a new note, then replace every value in angle brackets. The fields and their allowed values are defined in [[00-system/Metadata Standard|Metadata Standard]]. Choose `type` by what the note does, and keep the note within the size range of that type (see [[00-system/Agent Instructions|Agent Instructions]]).

```markdown
---
node_id: "<lowercase-kebab-case-id>"
title: "<Title matching the filename>"
type: "<index | hub | contract | operations | data-model | template | record | policy | guide>"
parent: "[[<folder>/<Parent Note>|<Parent Note>]]"
status: "draft"
version: "0.1.0"
revision: 1
created: "<YYYY-MM-DD>"
updated: "<YYYY-MM-DD>"
change_type: "minor"
change_summary: "<One sentence: what this version adds.>"
review_status: "needs_review"
tags:
  - "<domain>"
aliases: []
---
# <Title>

## Purpose

<Why this note exists, in two or three sentences.>

## Content

<The substance. Use headings that a reader can scan.>

## Related

- <Path-qualified wikilinks to the notes this one depends on or feeds.>
```

## After you fill it in

1. Link the new note from its parent (an index or hub), so it is not an orphan.
2. Run `python -B code/validation/validate.py` and fix every error it reports.
3. Leave `review_status: needs_review` until the owner approves the note.
