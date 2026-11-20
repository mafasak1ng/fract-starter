---
node_id: "layer-guard"
title: "Layer Guard"
type: "policy"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the layer guard policy: layers, the commit check, the trigger and passkey flow, the audit log and passkey recovery."
review_status: "needs_review"
tags:
  - "system"
  - "security"
  - "layers"
aliases:
  - "Kernel Guard"
  - "Commit Guard"
next: "[[00-system/Project Vaults|Project Vaults]]"
---
# Layer Guard

Every path in the vault belongs to one layer. The layer decides who may change it. A small set of rule files, the **kernel**, changes only when the owner unlocks it with a trigger word **and** a passkey. A Git pre-commit hook enforces this, so the rule holds whether an agent or a person made the edit.

## The layers

The policy lives in `_atlas/layers.json`. It is itself a kernel file.

| Layer | Order | Who may change it | Paths |
| --- | --- | --- | --- |
| `provenance` | 0 | Nobody, ever, not even with the unlock | None by default. Add paths for records that must never change. |
| `kernel` | 1 | The owner, with the trigger word and the passkey | `AGENTS.md`, `README.md`, `.gitattributes`, `_atlas/layers.json`, `code/git-hooks/**` |
| `docs` | 2 | Agents, with the owner's permission for the write | Everything not listed elsewhere (the default layer): the notes in the numbered domains |
| `ops` | 3 | Agents, openly | `.agents/**`, `code/**`, `_atlas/**`, except the kernel paths above |

**The most specific pattern wins.** `code/git-hooks/**` is longer than `code/**`, so the hooks are kernel while the rest of `code/` is ops. To move a folder to another layer, edit its pattern in `_atlas/layers.json` (a kernel commit).

Patterns take four shapes: `dir/**` (everything under a folder), `dir/*` (its direct children only), an exact path, or a bare folder name.

The commit guard only checks the kernel and provenance layers. The `docs` and `ops` rules are working rules for agents, set out in [[00-system/Agent Instructions|Agent Instructions]]; Git does not block those commits.

## How the guard decides

`code/git-hooks/pre-commit` runs on every commit once setup has set `core.hooksPath`. It collects the staged paths and the policy from Git and passes them to `code/git-hooks/layer-guard.mjs`, which needs Node.js 18 or newer and nothing else.

For each staged path:

1. `_atlas/layers.json` and `code/git-hooks/**` are always kernel, whatever the policy says.
2. Otherwise the most specific matching pattern decides the layer; no match means the default layer, `docs`.
3. A provenance path is refused.
4. A kernel path is refused unless all three hold:
   - the policy has a passkey record (otherwise the refusal says to run `init_vault.py`);
   - `ATLAS_TRIGGER` contains a trigger word from `kernel.triggers` (by default `KERNEL-UNLOCK`);
   - `ATLAS_PASSKEY` verifies against the scrypt record in constant time.
5. Every other path passes without a check.

If any path is refused, the whole commit is refused and the message names each path and the missing piece.

**The guard judges by the last commit, not the working tree.** It runs the copy of `layer-guard.mjs` committed at `HEAD` and reads the policy committed at `HEAD`. An edit to the guard or the policy, staged or not, cannot loosen the check on its own commit. Only a repository with no committed policy falls back to the staged files.

**First passkey exception.** While the committed policy has no passkey, a commit whose staged `_atlas/layers.json` differs from the committed one **only** by the new passkey record is checked against that new record. That is how the passkey from setup gets committed. Any other edit in the same policy change is refused.

## First-time setup

```
python -B code/setup/init_vault.py
git add _atlas/layers.json
python -B code/setup/kernel_commit.py -m "kernel: set the passkey"
```

`init_vault.py` asks twice for a passkey at a hidden prompt (at least 12 characters). It stores only a salted scrypt hash (N=16384, r=8, p=1, 32-byte key, random 16-byte salt) in `kernel.passkey`, and turns the guard on with `git config core.hooksPath code/git-hooks`. The vault must be the root of its own Git repository. Run `git init` first if it is not. It refuses to replace an existing passkey unless you pass `--reset`, which first asks for the current one.

After a `--reset`, commit the new record with the **old** passkey: the guard checks the record that is already committed.

## Committing a kernel change

1. The owner's own message carries the trigger word `KERNEL-UNLOCK`. Without it, an agent does not prepare kernel edits.
2. The agent makes and stages the kernel edits, and nothing else.
3. The owner runs `python -B code/setup/kernel_commit.py -m "kernel: <what changed>"`. It shows what is staged, lists the kernel paths, and asks for the passkey at a hidden prompt.
4. The helper passes the trigger and passkey only to that one `git commit` process. It prints `Committed.` or `Commit refused.`

An agent never asks for, reads, types or echoes the passkey. If nothing staged is a kernel path, the helper refuses without asking, so the passkey is never typed for nothing.

## The audit log

Every kernel or provenance decision, allowed or refused, appends one JSON line to `_atlas/audit/<YYYY-MM>.jsonl`:

```json
{"time": "2026-11-20T10:00:00.000Z", "path": "AGENTS.md", "layer": "kernel", "allowed": true, "reason": "Trigger accepted and passkey verified.", "via": "git-pre-commit"}
```

The passkey is never written there. Git ignores `_atlas/audit/` (see `.gitignore`), so the log is a local record on each machine. Read it to see who tried to change what, and when.

## Limits

- `git commit --no-verify`, or changing `core.hooksPath`, skips any hook. The guard stops accidents and agents that respect the repository. It is not a sandbox against someone with full control of the machine.
- The `pre-commit` launcher itself runs from the working tree. It is a kernel file, so changing it still needs the unlock.
- Without Node.js the hook refuses every commit and says why. Set `ATLAS_NODE` to point at a Node executable. From WSL, a Windows `node.exe` works.

## If the passkey is lost

The passkey cannot be recovered; only its hash is stored. To set a new one, the owner bypasses the guard once, on purpose:

1. Edit `_atlas/layers.json` and set `kernel.passkey` back to `null`. Change nothing else.
2. Commit only that file, skipping the hook: `git commit --no-verify -m "kernel: clear the lost passkey" -- _atlas/layers.json`.
3. Run `python -B code/setup/init_vault.py` and commit the new record as in First-time setup above.
4. Copy the new record into every linked project vault (see [[00-system/Project Vaults|Project Vaults]]).

Do this only yourself, never through an agent. The `--no-verify` commit leaves no audit line, so note the reason in the session journal.
