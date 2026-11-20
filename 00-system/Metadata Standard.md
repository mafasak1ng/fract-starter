---
node_id: "metadata-standard"
title: "Metadata Standard"
type: "policy"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Documented the note metadata standard the validator enforces."
review_status: "needs_review"
tags:
  - "system"
  - "metadata"
  - "policy"
aliases:
  - "Frontmatter Standard"
previous: "[[00-system/Agent Instructions|Agent Instructions]]"
next: "[[00-system/Validation Policy|Validation Policy]]"
---
# Metadata Standard

Every Markdown note in the vault starts with YAML frontmatter that follows this standard. It is what lets agents find, trust and update notes without guessing, and it is exactly what [[00-system/Validation Policy|the validator]] checks.

## Scope

The standard applies to every `.md` file in the vault, with two exceptions:

- Skill files, `.agents/skills/<name>/SKILL.md`, carry only `name` (kebab-case, equal to the folder name) and `description` (one or two sentences on when to use the skill).
- The skills index, `.agents/skills/README.md`, and `LICENSE` carry no frontmatter.

The validator does not read `.git/`, `.obsidian/` or `_atlas/audit/`.

## Fields

| Field | Required | Rule |
| --- | --- | --- |
| `node_id` | yes | Lowercase kebab-case (`a-z`, `0-9`, single hyphens), unique in the vault, never reused |
| `title` | yes | Human title; matches the filename |
| `type` | yes | One of `index`, `hub`, `contract`, `operations`, `data-model`, `template`, `record`, `policy`, `guide` |
| `parent` | yes | Path-qualified wikilink to the note this one belongs under |
| `status` | yes | `active`, `draft` or `deprecated` |
| `version` | yes | Semantic version, quoted: `"1.2.0"` |
| `revision` | yes | Integer, at least 1, incremented on every change |
| `created` | yes | `YYYY-MM-DD` |
| `updated` | yes | `YYYY-MM-DD`, never before `created` |
| `change_type` | yes | `major`, `minor` or `patch` |
| `change_summary` | yes | One non-empty sentence describing the latest change |
| `review_status` | yes | `needs_review` or `approved`; only the owner approves |
| `tags` | yes | List with at least one tag |
| `aliases` | no | List of other names for the note |
| `previous` | no | Wikilink to the previous note in a reading sequence |
| `next` | no | Wikilink to the next note in a reading sequence |

Other fields are allowed when a domain needs them, but agents must not invent fields to carry facts that belong in the body.

## Types

- `index`: routes a domain or folder.
- `hub`: introduces a topic and routes to its child notes.
- `contract`: binds a component or role to inputs, outputs and limits.
- `operations`: a procedure someone can follow.
- `data-model`: fields, entities and their relationships.
- `template`: a reusable structure to copy.
- `record`: evidence of what happened, such as a session record or a decision.
- `policy`: a rule that applies across domains.
- `guide`: an explanation written for people.

## Links

Wikilinks are path-qualified from the vault root, without the `.md` extension, with an optional label: `[[00-system/Metadata Standard|Metadata Standard]]`. A link may point to a heading with `#`. Every wikilink, in the body or in `parent`, `previous` and `next`, must resolve to a file that exists. The root `README.md` is its own parent: `parent: "[[README|FRACT]]"`. Files without frontmatter, such as `.agents/skills/README.md`, are linked with a normal Markdown link.

## Versioning

- **MAJOR** changes structure, identity or meaning: a renamed contract, a removed rule.
- **MINOR** adds a capability, rule or field.
- **PATCH** fixes wording, links, dates or small errors.

Every change, whatever its size, increments `revision`, sets `updated` to the day of the change, and rewrites `change_type` and `change_summary` to describe it. A changed note returns to `needs_review`.

## Example note

```markdown
---
node_id: "review-checklist"
title: "Review Checklist"
type: "policy"
parent: "[[10-core/Core Index|Core Index]]"
status: "active"
version: "1.1.0"
revision: 3
created: "2026-11-20"
updated: "2026-11-22"
change_type: "minor"
change_summary: "Added a check for broken links."
review_status: "needs_review"
tags:
  - "core"
  - "review"
aliases:
  - "Checklist"
---
# Review Checklist

The checks every change passes before it is called done.
```

## Common mistakes

- An unquoted version such as `version: 1.0`: it is not semver and may be read as a number.
- A bare link such as `[[Core Index]]`: always qualify it with the folder.
- Raising `version` without raising `revision`, or the reverse.
- An agent setting `review_status: approved`: only the owner does that.
