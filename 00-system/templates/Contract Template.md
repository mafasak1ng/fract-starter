---
node_id: "contract-template"
title: "Contract Template"
type: "template"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the contract template for the blank starter."
review_status: "needs_review"
tags:
  - "template"
  - "contract"
aliases: []
---

# Contract Template

A contract states what a component, process or agent role must do, what it may not do, and how you know it is finished. Use it when an agent will be held to the note's terms. Copy the block below and replace the values in angle brackets; the metadata fields are defined in [[00-system/Metadata Standard|Metadata Standard]].

```markdown
---
node_id: "<component>-contract"
title: "<Component> - Contract"
type: "contract"
parent: "[[<folder>/<Component>|<Component>]]"
status: "draft"
version: "0.1.0"
revision: 1
created: "<YYYY-MM-DD>"
updated: "<YYYY-MM-DD>"
change_type: "minor"
change_summary: "<One sentence.>"
review_status: "needs_review"
tags:
  - "contract"
aliases: []
---
# <Component> - Contract

## Role

<What this component is responsible for, in one paragraph.>

## Authority

<Who may change this contract, and what it overrides or defers to.>

## Inputs

| Input | Source | Required |
| --- | --- | --- |
| <name> | <where it comes from> | <yes or no> |

## Outputs

| Output | Destination | Format |
| --- | --- | --- |
| <name> | <where it goes> | <format> |

## Boundaries

- <What the component must never do.>
- <Which files or systems it may not write.>

## Failure handling

<What happens when an input is missing or a check fails: stop, ask, or mark the
result unverified.>

## Completion criteria

- <A check that proves the work is done, such as the validator exiting 0.>
```

## Writing a good contract

- Every rule should be testable: a reader can say whether it was followed.
- Prefer "must" and "must not" over "should" for anything that matters.
- Keep within 3,000 to 8,000 characters; split a larger contract into a hub with children.
