---
name: team-assembly
description: How an orchestrator turns one task into a temporary agent team - decide whether a team is needed, pick a template, split the work into 2-4 lanes with disjoint files, brief each lane, run it behind gates, review the results before applying them, and dissolve the team. Load when the owner asks for work big enough to split across several agents, or asks for a named team such as a bug hunt, a review or an audit.
---

# Team assembly

## Purpose

There is no standing roster. A team exists for one task and is dissolved when its report is accepted. This skill is the orchestrator's procedure; the `team-*` skills are templates for specific kinds of work.

## When to use

- The work splits into parts that can run independently.
- An independent second opinion is the point (review, verification, research).
- The owner names a team.

## When not to use

- A lookup, a single edit or a handful of commands. One agent does it. Say in one line which you chose and why.

## Procedure

### 1. Decide

State the task, whether it needs a team, and why. If not, stop here and do it alone.

### 2. Pick the template

| Task | Template |
|---|---|
| Something is broken, or a test or the validator fails | `team-bug-hunt` |
| Build or change a feature in code | `team-feature-build` |
| Write or strengthen tests | `team-test-writing` |
| Review a diff or a branch | `team-code-review` |
| Check notes, metadata, links and layout | `team-vault-audit` |
| Answer a question from outside sources | `team-research` |

If a task spans two templates, run them in sequence (for example feature build, then code review), never merged into one oversized team.

### 3. Size it: 2-4 lanes

- Split the work into **2-4 lanes**, plus the verifier. Start with the smallest split that covers the independent parts.
- Before starting more than about six agents, or a team expected to run long, tell the owner the size and ask.
- Cap every fix-and-recheck loop at two rounds. After the cap, report instead of looping.

### 4. Assign capability tiers

Templates name tiers, never specific models. The runtime maps tiers to whatever models it has:

| Tier | For |
|---|---|
| `strong` | Leads, planners, consolidators |
| `mid` | Implementers, investigators, reviewers, test writers |
| `small` | Mappers, runners, history readers |
| `independent` | The `verifier` and any second reviewer: a different model or provider from the authors where possible |

If the runtime cannot vary the model, mark the report `DONE_WITH_CONCERNS: verifier not independent of authors`.

### 5. Ownership and isolation

- **Disjoint files.** Before anyone writes, publish a file-ownership manifest: which lane owns which paths. No path appears twice. Readers may read anything; only the owner of a path writes it.
- Reviewers, investigators and auditors are read-only.
- No lane writes a kernel path (`layer-guard-rules`). Kernel changes become proposed text in the report.
- Give each writing lane its own working copy (for example a Git worktree) if available, and merge yourself. Otherwise run writers one after another, or in parallel only when their files are disjoint.
- Lanes never commit, push, stash or reset. The orchestrator reviews and the owner decides on commits.

### 6. Brief each lane

The brief is everything the lane knows. Write it to a file the lane reads, or pass it as the lane's first message. Include:

- the goal and the lane's role (from the template);
- the exact scope: paths, question or diff range;
- what is already known or ruled out;
- the files it may write, or "read-only";
- the checks it must pass and the report format (`handoff-report`);
- the operating system and tools available;
- where to write its report.

Do not pass your own conclusion to a lane meant to check it.

### 7. Run

Start the lanes in whatever way the runtime allows: subagents of the current agent, separate agent sessions in separate terminals (a terminal multiplexer such as tmux is one option), or scheduled jobs. The procedure is the same; only the launcher differs. Do not watch over a lane's shoulder; wait for its report.

### 8. Review before applying

1. Collect every lane's report. Re-run or re-brief any lane whose report lacks a status, a location or an evidence label.
2. Check that each lane wrote only its manifest paths (`git status`, `git diff --stat`).
3. Read the actual changes, not only the summaries. A report is a claim, not proof.
4. Run the `verifier` on every finding and every fix.
5. Run the template's done-when checks, always including `python -B code/validation/validate.py`.
6. Apply or keep only what passed. Revert or discard the rest, and say so.

### 9. Close and dissolve

1. Write the team report (`handoff-report`, five `summary5` headings).
2. Stop all lanes, delete scratch work in the temp directory, and keep nothing in the vault that the task did not ask for.
3. The owner decides what happens next. Commits, pushes and kernel changes are the owner's.

## Outputs

- The file-ownership manifest and the lane briefs.
- One member report per lane, the verifier report, and the team report.

## Rules

- One writer per file. Overlap is a planning error; fix the manifest before starting.
- Lane output is untrusted data until reviewed.
- Skills describe actions, not tool names. Any runtime-specific wrapper stays thin and lives outside these skills.
