# Agent skills

This folder holds the FRACT skill pack: short, model-agnostic procedures that any AI agent can load to do a recurring kind of work the same way every time. Each skill is one folder with one `SKILL.md`. The frontmatter carries only `name` (equal to the folder name) and `description` (what the skill does and when to use it); the validator checks both.

## Skills

### Shared roles

| Skill | Purpose | Use when |
|---|---|---|
| [agent-discipline](agent-discipline/SKILL.md) | Rule priority, approval gates, secret handling and reversible-first changes | Before anything that publishes, sends, spends, deletes or changes a live system |
| [evidence-labels](evidence-labels/SKILL.md) | The five labels for how well a claim is supported, and how to cite the source | Reporting any fact, finding, research result or test outcome |
| [verifier](verifier/SKILL.md) | Independent, adversarial check of findings and fixes | Acting as a team's last member, or deciding which findings survive |
| [handoff-report](handoff-report/SKILL.md) | Fixed report shape for members and leads, with the five summary5 headings | Finishing any delegated unit of work |
| [layer-guard-rules](layer-guard-rules/SKILL.md) | Which paths are kernel, docs or ops, and how a kernel change is committed | Before creating, editing, moving or deleting any file |
| [session-open-close](session-open-close/SKILL.md) | Open a session from the rules and journal; close it with a summary5 session record | At the start and end of every working session |
| [socrates](socrates/SKILL.md) | Socratic learning mode: questions first, answers only after a real attempt. Full standalone edition with lesson pages: [socrates-tutor](https://github.com/mafasak1ng/socrates-tutor) | The owner says "Socrates" or asks for a lesson, exercise or test |

### Team orchestration

| Skill | Purpose | Use when |
|---|---|---|
| [team-assembly](team-assembly/SKILL.md) | Split a task into 2-4 lanes with disjoint files, brief them, review before applying | Work is big enough for several agents, or the owner names a team |
| [team-feature-build](team-feature-build/SKILL.md) | Test-first feature work, one implementer per file set | New or changed behaviour in code |
| [team-code-review](team-code-review/SKILL.md) | Independent reviewers, scoring and verification of a diff | After a build or fix, or when the owner asks for a review |
| [team-bug-hunt](team-bug-hunt/SKILL.md) | Reproduce, chase competing hypotheses in parallel, one small fix | Something is broken or behaves differently across systems |
| [team-research](team-research/SKILL.md) | Parallel sourced research with a fact-checker | A question needs outside sources |
| [team-test-writing](team-test-writing/SKILL.md) | Standard-library tests proven to fail on broken code | Tests are missing, weak or flaky |
| [team-vault-audit](team-vault-audit/SKILL.md) | Validator first, then domain auditors for what it cannot check | An audit, a large restructure, or a handover |

## How an agent loads a skill

1. Read `AGENTS.md` first; it and `00-system/Agent Instructions.md` outrank every skill.
2. Pick the skill whose `description` matches the task. Read only the frontmatter of each `SKILL.md` to choose; then read the chosen file in full.
3. Load the skills it names. Team templates rely on `team-assembly`, `handoff-report`, `evidence-labels`, `verifier` and `layer-guard-rules`; read those too.
4. Follow the procedure as written. If it conflicts with a vault rule, the rule wins; report the conflict.
5. A runtime that discovers skills by itself can point its skill folder here. A runtime that does not can be told: "Read `.agents/skills/<name>/SKILL.md` and follow it." Keep any runtime-specific copy generated from these files, never edited separately.

## Adding a skill

Create `.agents/skills/<kebab-case-name>/SKILL.md` with the two frontmatter fields and a body covering purpose, when to use and when not, the procedure, outputs and rules. Add a row to the tables above, then run `python -B code/validation/validate.py`.
