---
node_id: "project-vaults"
title: "Project Vaults"
type: "operations"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the operations note for linked project vaults: what they are, how to create and check one, and the registry."
review_status: "needs_review"
tags:
  - "system"
  - "projects"
aliases:
  - "Linked Project Vaults"
previous: "[[00-system/Layer Guard|Layer Guard]]"
---
# Project Vaults

A **linked project vault** is a separate Git repository and Obsidian vault for one project. It sits next to this vault, follows this vault's rules, and is listed in this vault's registry. Use one when a project needs its own history, its own collaborators or its own publishing, but should still run under the same rules.

## What a project vault is

- **Its own repository.** Commits, branches and remotes stay separate from this vault.
- **Linked, not nested.** It lives beside this vault (by default in the same parent folder), never inside it.
- **Same rules.** Its `AGENTS.md` defers to this vault's `AGENTS.md`, which wins on any conflict. It only adds the project's own write boundaries.
- **Same guard, same passkey.** It carries byte-identical copies of the commit guard (`code/git-hooks/`) and of `code/setup/kernel_commit.py`. Its `_atlas/layers.json` carries this vault's passkey record, so one passkey unlocks both. See [[00-system/Layer Guard|Layer Guard]].

| File | Purpose |
| --- | --- |
| `README.md` | The project's hub note; its own parent |
| `AGENTS.md` | Loader that defers to this vault's `AGENTS.md` |
| `.gitattributes` | Copy of this vault's line-ending rules |
| `.gitignore` | Obsidian state, caches, the audit log |
| `.obsidian/app.json`, `.obsidian/core-plugins.json` | This vault's Obsidian settings |
| `_atlas/layers.json` | The project's layer policy, with this vault's passkey record |
| `code/git-hooks/pre-commit`, `code/git-hooks/layer-guard.mjs` | The commit guard |
| `code/setup/kernel_commit.py` | The passkey helper for kernel commits |

Its kernel is `AGENTS.md`, `README.md`, `.gitattributes`, `_atlas/layers.json` and `code/git-hooks/**`. Notes added to it follow the [[00-system/Metadata Standard|Metadata Standard]].

## Create one

From this vault's root:

```
python -B code/setup/new_project.py create <id> --title "Title"
python -B code/setup/new_project.py create <id> --title "Title" --projects-root <folder>
```

- `<id>` is lowercase kebab-case (letters, digits, single hyphens), 2 to 40 characters. It becomes the folder name.
- `--title` is 2 to 60 printable characters without quotes, backslashes, `[`, `]` or `|`.
- `--projects-root` defaults to this vault's parent folder.

The script builds the vault in a temporary folder, makes its first commit, and then turns its guard on. The guard needs a committed policy, so that first commit has to come before it. The script then moves the folder into place and only then adds the registry row. If any step fails, the temporary folder is removed and the registry stays as it was. It refuses an id that is already registered or a folder that already exists. It never commits in this vault, never pushes and never adds a remote.

Set the passkey in this vault ([[00-system/Layer Guard|Layer Guard]], first-time setup) **before** creating project vaults. A project created without one has a locked kernel until its record is set.

Then commit the registry row in this vault with a normal commit (the registry is an `ops` file, not kernel):

```
git add _atlas/registry/projects.json
git commit -m "projects: register <id>"
```

## Check one

```
python -B code/setup/new_project.py check <id>
```

`check` is read-only. It prints one line per check, `PASS|FAIL  <check>: <finding>`, then a count, and exits 0 when everything passes and 1 otherwise. It checks:

- the folder and every required file exist;
- `README.md` and `AGENTS.md` carry the required metadata fields;
- the JSON files parse;
- the guard copies match this vault's committed files byte for byte;
- the passkey record matches this vault's;
- it is a Git repository with a first commit, `core.hooksPath` set to `code/git-hooks`, an executable `pre-commit`, no remote, and a clean worktree;
- the id is in the registry.

A failed copy or passkey check usually means this vault's guard or passkey changed after the project was created. Copy the new files or record into the project and commit them there as a kernel change, using the passkey that project's committed record still holds.

## The registry

`_atlas/registry/projects.json` lists every linked project vault:

```json
{
  "version": 1,
  "projects": [
    {
      "id": "demo-project",
      "title": "Demo Project",
      "path": "<projects root>/demo-project",
      "created": "2026-11-20",
      "status": "active",
      "bootstrap_commit": "<sha of the project's first commit>",
      "guard_sha256": { "code/git-hooks/layer-guard.mjs": "<sha256>" }
    }
  ],
  "note": "..."
}
```

`guard_sha256` records the hash of each copied guard file at creation, so a later change in either vault can be traced. To retire a project, set its `status` to `retired` and keep the row; do not delete history.
