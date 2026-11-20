---
node_id: "session-record-template"
title: "Session Record Template"
type: "template"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the session record template for the blank starter."
review_status: "needs_review"
tags:
  - "template"
  - "journal"
  - "session"
aliases: []
---

# Session Record Template

Every working session ends with a record in `80-journal`, named `Session Record - YYYY-MM-DD - Topic.md`. Copy the block below, replace the values in angle brackets, and write the `summary5` as described in [[80-journal/Summary5 Guide|Summary5 Guide]]. Link the new record from [[80-journal/Journal Index|Journal Index]].

```markdown
---
node_id: "session-<yyyy-mm-dd>-<topic>"
title: "Session Record - <YYYY-MM-DD> - <Topic>"
type: "record"
parent: "[[80-journal/Journal Index|Journal Index]]"
status: "active"
version: "1.0.0"
revision: 1
created: "<YYYY-MM-DD>"
updated: "<YYYY-MM-DD>"
change_type: "minor"
change_summary: "Recorded the session on <topic>."
review_status: "needs_review"
tags:
  - "journal"
  - "session"
aliases: []
---
# Session Record - <YYYY-MM-DD> - <Topic>

## Session

- Date: <YYYY-MM-DD>
- Topic: <short topic>
- Participants: <the owner and the agents, by role>
- Prompts used: <n> of 25

## Log

1. <What happened, in order, with the files touched.>

## summary5

1. **Intent and active scope:** <...>
2. **Work performed:** <...>
3. **Result or approved output:** <...>
4. **Validation, risk and unresolved information:** <...>
5. **Next action or completion declaration:** <...>
```

## Rules

- A record is append-only. Correct a fact with a dated note at the end, never by rewriting the log.
- No secrets, passkeys, tokens or personal data in a record.
- See [[80-journal/Session Record - Example|Session Record - Example]] for a finished record.
