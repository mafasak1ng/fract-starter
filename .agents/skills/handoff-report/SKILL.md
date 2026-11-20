---
name: handoff-report
description: The fixed report shape every team member and every team lead returns - a status value, findings with location, severity, confidence and evidence label, and for a whole team the five-part summary5. Load at the end of any delegated unit of work, before handing results back to a lead, an orchestrator or the owner.
---

# Hand-off report

## Purpose

A fixed shape lets a lead merge reports from agents on different models and runtimes without re-reading their work, and lets the owner see at a glance what was done, what was found and what is still open.

## When to use

- A team member finishing its brief: the member report.
- A lead closing a team: the team report.
- A single agent handing delegated work back to the session that started it.

## When not to use

- The session's own journal record. That uses the Session Record Template and `summary5` (see `session-open-close`), although the team report's five headings are the same.

## Member report

```text
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
ROLE: <role name from the team skill>
SCOPE: <files, paths or question this member covered>
OS: <operating system> ; TOOLS: <tool and version for each check run>

FINDINGS
- id: <short id, e.g. BH-3>
  location: <path:line, or path + section, or URL>
  severity: critical | high | medium | low | info
  confidence: <0-100>
  evidence: verified | observed | unverified | unknown | needs_review
  claim: <one sentence>
  proof: <command + key output, or a short quote + source>
  fix: <smallest correct change, or "none proposed">

FILES CHANGED: <path list, or "none">
NOT CHECKED: <what was in scope but not covered, and why>
```

Status meanings:

- `DONE`: the scope is covered and every check you were asked to run ran.
- `DONE_WITH_CONCERNS`: covered, but something looks wrong outside your scope or a result is borderline.
- `NEEDS_CONTEXT`: you cannot continue without information only the lead or owner has. Say exactly what.
- `BLOCKED`: a rule, a missing tool or a failed precondition stops you. Name it. Do not work around it.

## Severity

- `critical`: data loss, a secret exposed, the kernel guard bypassed, or a change that would damage a live system.
- `high`: wrong behaviour on a normal path, a gate that silently passes, or a broken contract.
- `medium`: wrong behaviour on an edge path, or a rule broken without immediate harm.
- `low`: style, clarity or a small inconsistency.
- `info`: an observation with no defect.

## Team report

The lead closes the team with the five `summary5` headings (see `80-journal/Summary5 Guide.md`), in this order and with these names:

1. Intent and active scope
2. Work performed
3. Result or approved output
4. Validation, risk, and unresolved information
5. Next action or completion declaration

Under heading 3, list the findings that survived the `verifier`, in member format. Under heading 4, list every refuted or downgraded finding with its reason, every `NOT CHECKED` item and every `needs_review` item. Under heading 5, state what the owner must decide.

## Procedure

1. Fill every field. A field with nothing to report says `none`, never blank.
2. Give each finding a location and an evidence label (`evidence-labels`).
3. Run `git diff --stat` and list exactly the files you changed.
4. Re-read the report once against your brief: every requested check either has a result or is listed under `NOT CHECKED`.

## Rules

- No finding without a location and an evidence label.
- Quote at most 15 words from any third-party source.
- Do not paste whole files or long logs; give the command and the lines that matter.
- Report what failed as plainly as what passed.
- Never claim a commit, push or kernel change happened unless the owner did it or asked for it and you saw it succeed.
