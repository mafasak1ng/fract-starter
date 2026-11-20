#!/usr/bin/env python3
"""FRACT project vaults: create or check a linked project vault.

A project vault is a separate Git repository and Obsidian vault for one
project. It sits next to this vault (by default in the same parent folder),
defers to this vault's AGENTS.md, runs the same commit guard with the same
passkey, and is listed in this vault's `_atlas/registry/projects.json`.

Usage (always with -B so Python writes no bytecode caches):
    python -B code/setup/new_project.py create <id> --title "Title" [--projects-root PATH]
    python -B code/setup/new_project.py check <id> [--projects-root PATH]

Commands:
    create <id>   Builds the vault in a temporary folder next to the target,
                  makes its bootstrap commit, then turns its commit guard on
                  (core.hooksPath), moves it into place, and only then adds a
                  row to this vault's registry. On any failure the temporary
                  folder is removed and the registry is untouched.
    check <id>    Read-only. Prints `PASS|FAIL  <check>: <finding>` for each
                  check and exits 0 when all pass, 1 when any fails.

Ids are lowercase kebab-case (a-z, 0-9, single hyphens), 2 to 40 characters.
Titles are 2 to 60 printable characters without quotes, backslashes, `[`, `]`
or `|`, so they are safe inside YAML and wikilinks.

What a project vault contains:
    AGENTS.md                      Loader that defers to this vault's AGENTS.md.
    README.md                      The project's hub note, its own parent.
    .gitattributes                 Copy of this vault's line-ending rules.
    .gitignore                     Obsidian state, caches, the audit log.
    .obsidian/                     This vault's Obsidian settings.
    _atlas/layers.json             The project's layer policy, carrying this
                                   vault's passkey record, so one passkey
                                   unlocks both.
    code/git-hooks/                Byte-identical copies of the commit guard.
    code/setup/kernel_commit.py    Byte-identical copy of the passkey helper.

Bootstrap: the guard needs a committed policy, so the first commit is made
before core.hooksPath is set; every later commit goes through the guard.
The registry is not a kernel file: commit the new row with a normal commit.

It writes only inside the projects root and this vault's registry; it never
commits in this vault, never pushes and never adds a remote. The standard
library only; Python 3.11 or newer.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

MAIN = Path(__file__).resolve().parents[2]
REGISTRY_REL = "_atlas/registry/projects.json"
POLICY_REL = "_atlas/layers.json"
ID_PATTERN = re.compile(r"(?=.{2,40}\Z)[a-z0-9]+(?:-[a-z0-9]+)*")
RESERVED = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(10)), *(f"lpt{n}" for n in range(10))}
TITLE_PATTERN = re.compile(r"[A-Za-z0-9][ -~]{1,59}")
TITLE_FORBIDDEN = set('"\\[]|')
COPIED = (
    ".gitattributes",
    "code/git-hooks/pre-commit",
    "code/git-hooks/layer-guard.mjs",
    "code/setup/kernel_commit.py",
)
EXECUTABLE = ("code/git-hooks/pre-commit",)
NOTES = ("README.md", "AGENTS.md")
REQUIRED = (*NOTES, ".gitignore", ".obsidian/app.json", ".obsidian/core-plugins.json", POLICY_REL, *COPIED)
JSON_FILES = (POLICY_REL, ".obsidian/app.json", ".obsidian/core-plugins.json")
FRONTMATTER_KEYS = (
    "node_id", "title", "type", "parent", "status", "version", "revision", "created", "updated",
    "change_type", "change_summary", "review_status", "tags",
)
DEFAULT_APP = {"alwaysUpdateLinks": True, "newFileLocation": "root", "useMarkdownLinks": False,
               "userIgnoreFilters": ["code/", "_atlas/audit/"]}
DEFAULT_CORE_PLUGINS = ["file-explorer", "global-search", "switcher", "graph", "backlink",
                        "outgoing-link", "tag-pane", "page-preview", "templates", "outline"]
GITIGNORE = b".obsidian/workspace*.json\n.trash/\n__pycache__/\n*.pyc\n_atlas/audit/\n"


class SourceError(Exception):
    """A file of this vault that a project vault needs is missing."""


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}")
    return result


def main_is_own_repo() -> bool:
    result = git(MAIN, "rev-parse", "--show-toplevel", check=False)
    return result.returncode == 0 and Path(result.stdout.strip()).resolve() == MAIN.resolve()


def main_blob(rel: str) -> bytes:
    """A file of this vault as last committed, or the working file when it is not committed."""
    if main_is_own_repo():
        result = subprocess.run(["git", "-C", str(MAIN), "show", f"HEAD:{rel}"], capture_output=True)
        if result.returncode == 0:
            return result.stdout
    path = MAIN / rel
    if path.is_file():
        return path.read_bytes()
    raise SourceError(f"{rel} is missing in {MAIN}")


def optional_blob(rel: str, fallback: bytes) -> bytes:
    try:
        return main_blob(rel)
    except SourceError:
        return fallback


def read_registry() -> dict:
    path = MAIN / REGISTRY_REL
    if not path.is_file():
        return {"version": 1, "projects": []}
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry.setdefault("projects", [])
    return registry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in value)
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def note_fields(pid: str, suffix: str, title: str, kind: str, parent_title: str, today: str, summary: str,
                extra: dict) -> dict:
    fields = {
        "node_id": f"{pid}-{suffix}", "title": title, "type": kind, "parent": f"[[README|{parent_title}]]",
        "status": "active", "version": "1.0.0", "revision": 1, "created": today, "updated": today,
        "change_type": "minor", "change_summary": summary, "review_status": "needs_review",
        "tags": ["project-vault", pid],
    }
    fields.update(extra)
    return fields


def render(pid: str, title: str, target: Path, today: str) -> dict[str, bytes]:
    readme = frontmatter(note_fields(
        pid, "readme", title, "hub", title, today, "Created the project vault, linked to its main vault.",
        {"aliases": [f"{title} project vault"], "next": "[[AGENTS|AGENTS.md]]"},
    )) + f"""# {title}

This is the {title} project vault: its own Git repository and Obsidian vault, linked to the main vault at `{MAIN}`. This README is the vault's root note, so it is its own parent.

## Links

- Loader for agents: [[AGENTS|AGENTS.md]]
- Main vault: `{MAIN}`
- Registry row: id `{pid}` in the main vault's `{REGISTRY_REL}`.

## How to work here

Notes for this project live in this vault and follow the main vault's metadata standard. New and changed notes stay `needs_review` until the owner approves them.

## Check

From the main vault: `python -B code/setup/new_project.py check {pid}`.
"""
    agents = frontmatter(note_fields(
        pid, "agents", f"{title} Agent Loader", "contract", title, today,
        "Created the project loader, which defers to the main vault's AGENTS.md.",
        {"previous": f"[[README|{title}]]"},
    )) + f"""# AGENTS.md

## Root

`{target}` is the root of the {title} project: its own Git repository and Obsidian vault. It is a linked project vault of the main vault at `{MAIN}`, registered in that vault's `{REGISTRY_REL}` under id `{pid}`.

## Precedence

The main vault's `AGENTS.md` applies here in full and wins over this file. This file only adds project rules. Read it first, then the main vault's `AGENTS.md`.

## Write boundaries

- Every write for this project stays inside `{target}`.
- Agents do not write to the main vault from here. A change the main vault needs is proposed to the owner there.
- Never store credentials or private values in this vault.

## Layers

`{POLICY_REL}` is this vault's policy. `AGENTS.md`, `README.md`, `.gitattributes`, `{POLICY_REL}` and `code/git-hooks/**` are the kernel: they change only with the trigger word `KERNEL-UNLOCK` and the owner's passkey, committed through `code/setup/kernel_commit.py`.
"""
    main_policy = json.loads(main_blob(POLICY_REL))
    main_kernel = main_policy.get("kernel") or {}
    layers = {
        "version": 1,
        "default": "docs",
        "note": f"Layer policy of the {title} project vault. The most specific pattern wins. This file is itself kernel.",
        "layers": {
            "kernel": {"label": "Layer 1 - the project kernel", "order": 1, "writable": "kernel",
                       "paths": ["AGENTS.md", "README.md", ".gitattributes", POLICY_REL, "code/git-hooks/**"]},
            "docs": {"label": "Layer 2 - project notes", "order": 2, "writable": "permission", "paths": []},
            "ops": {"label": "Layer 3 - project code and tooling", "order": 3, "writable": "open",
                    "paths": [".agents/**", "code/**", "_atlas/**"]},
            "provenance": {"label": "Provenance - never written, by anyone", "order": 0, "writable": "never",
                           "paths": []},
        },
        "kernel": {"triggers": main_kernel.get("triggers") or ["KERNEL-UNLOCK"],
                   "passkey": main_kernel.get("passkey")},
    }
    files = {
        "README.md": readme.encode("utf-8"),
        "AGENTS.md": agents.encode("utf-8"),
        ".gitignore": GITIGNORE,
        ".obsidian/app.json": optional_blob(".obsidian/app.json", (json.dumps(DEFAULT_APP, indent=2) + "\n").encode()),
        ".obsidian/core-plugins.json": optional_blob(".obsidian/core-plugins.json",
                                                     (json.dumps(DEFAULT_CORE_PLUGINS, indent=2) + "\n").encode()),
        POLICY_REL: (json.dumps(layers, indent=2) + "\n").encode("utf-8"),
    }
    for rel in COPIED:
        files[rel] = main_blob(rel)
    return files


def remove_tree(path: Path) -> None:
    def make_writable(func, failed, _info):
        os.chmod(failed, stat.S_IWRITE)
        func(failed)
    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=make_writable)
    else:
        shutil.rmtree(path, onerror=make_writable)


def create(pid: str, title: str, root: Path) -> int:
    target = root / pid
    staging = root / f".{pid}.creating"
    if target.exists() or staging.exists():
        print(f"{target} (or a leftover {staging.name}) already exists; nothing was changed.", file=sys.stderr)
        return 1
    try:
        registry = read_registry()
    except ValueError as error:
        print(f"{REGISTRY_REL} does not parse ({error}); nothing was changed.", file=sys.stderr)
        return 1
    if any(row.get("id") == pid for row in registry["projects"]):
        print(f"{pid} is already registered in {REGISTRY_REL}; nothing was changed.", file=sys.stderr)
        return 1

    today = datetime.date.today().isoformat()
    try:
        files = render(pid, title, target, today)
    except (SourceError, ValueError) as error:
        print(f"Cannot build the project vault: {error}. Nothing was changed.", file=sys.stderr)
        return 1
    if not (json.loads(files[POLICY_REL])["kernel"]["passkey"]):
        print("Note: this vault has no passkey yet, so the project vault's kernel stays locked until "
              "you run init_vault.py here and copy the record (see 00-system/Project Vaults.md).")

    root.mkdir(parents=True, exist_ok=True)
    try:
        for rel, data in files.items():
            path = staging / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for rel in EXECUTABLE:
            (staging / rel).chmod(0o755)
        git(staging, "init", "-q")
        git(staging, "symbolic-ref", "HEAD", "refs/heads/main")
        git(staging, "add", "--all")
        for rel in EXECUTABLE:
            git(staging, "update-index", "--chmod=+x", rel)
        git(staging, "commit", "-q", "--no-verify", "-m",
            f"project: create the {title} vault (bootstrap, before the guard is on)")
        git(staging, "config", "core.hooksPath", "code/git-hooks")
        commit = git(staging, "rev-parse", "HEAD").stdout.strip()
        staging.rename(target)
    except BaseException as error:
        remove_tree(staging)
        print(f"Creating the vault failed and was rolled back; the registry is unchanged. ({error})", file=sys.stderr)
        return 1

    registry["version"] = registry.get("version", 1)
    registry["projects"].append({
        "id": pid,
        "title": title,
        "path": str(target),
        "created": today,
        "status": "active",
        "bootstrap_commit": commit,
        "guard_sha256": {rel: sha256(files[rel]) for rel in COPIED},
    })
    registry_path = MAIN / REGISTRY_REL
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print(f"Created {target} (bootstrap commit {commit[:7]}); its commit guard is on.")
    print(f"Added {pid} to {REGISTRY_REL}. Commit that with a normal commit:")
    print(f'    git add {REGISTRY_REL} && git commit -m "projects: register {pid}"')
    return 0


def parse_frontmatter(text: str) -> dict | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    fields: dict = {}
    current = None
    for line in match.group(1).split("\n"):
        item = re.match(r"^  - (.+)$", line)
        if item and current is not None and isinstance(fields[current], list):
            fields[current].append(json.loads(item.group(1)))
            continue
        pair = re.match(r"^([a-z_]+):(?: (.+))?$", line)
        if not pair:
            raise ValueError(f"unexpected line: {line!r}")
        current, raw = pair.group(1), pair.group(2)
        if raw is None:
            fields[current] = []
        elif raw.isdigit():
            fields[current] = int(raw)
        else:
            fields[current] = json.loads(raw)
    return fields


def check(pid: str, root: Path) -> int:
    target = root / pid
    results: list[tuple[bool, str, str]] = []

    def report(ok: bool, name: str, finding: str) -> None:
        results.append((ok, name, finding))

    report(target.is_dir(), "folder", str(target))
    if not target.is_dir():
        return finish(results)
    missing = [rel for rel in REQUIRED if not (target / rel).is_file()]
    report(not missing, "required files", "all present" if not missing else "missing: " + ", ".join(missing))

    for rel in NOTES:
        path = target / rel
        if not path.is_file():
            continue
        try:
            fields = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            report(False, f"metadata {rel}", f"frontmatter does not parse: {error}")
            continue
        if fields is None:
            report(False, f"metadata {rel}", "no frontmatter")
            continue
        absent = [key for key in FRONTMATTER_KEYS if key not in fields]
        report(not absent, f"metadata {rel}", "complete" if not absent else "missing: " + ", ".join(absent))

    policy = None
    for rel in JSON_FILES:
        path = target / rel
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                report(True, f"json {rel}", "parses")
                if rel == POLICY_REL:
                    policy = data
            except ValueError as error:
                report(False, f"json {rel}", str(error))

    for rel in COPIED:
        path = target / rel
        if path.is_file():
            try:
                same = path.read_bytes() == main_blob(rel)
                report(same, f"copy {rel}", "matches the main vault" if same else "differs from the main vault")
            except SourceError as error:
                report(False, f"copy {rel}", str(error))

    if policy is not None:
        try:
            main_record = (json.loads(main_blob(POLICY_REL)).get("kernel") or {}).get("passkey")
            same = (policy.get("kernel") or {}).get("passkey") == main_record
            report(same, "passkey record", "same as the main vault" if same else "differs from the main vault")
        except (SourceError, ValueError) as error:
            report(False, "passkey record", f"cannot read the main vault's policy: {error}")

    is_repo = (target / ".git").exists()
    report(is_repo, "git repository", "present" if is_repo else "no .git folder")
    if is_repo:
        has_commit = git(target, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0
        report(has_commit, "bootstrap commit", "present" if has_commit else "no commits")
        hooks = git(target, "config", "--get", "core.hooksPath", check=False).stdout.strip()
        report(hooks == "code/git-hooks", "core.hooksPath", hooks or "not set")
        mode = git(target, "ls-files", "-s", "code/git-hooks/pre-commit", check=False).stdout.split(" ")[0]
        report(mode == "100755", "pre-commit mode", mode or "not tracked")
        remotes = git(target, "remote", check=False).stdout.split()
        report(not remotes, "no remote", "none" if not remotes else "has: " + ", ".join(remotes))
        dirty = git(target, "status", "--porcelain", check=False).stdout.strip()
        report(not dirty, "clean worktree", "clean" if not dirty else "uncommitted changes")

    try:
        registered = any(row.get("id") == pid for row in read_registry()["projects"])
        report(registered, "registry row",
               f"{pid} is in {REGISTRY_REL}" if registered else f"{pid} is not in {REGISTRY_REL}")
    except ValueError as error:
        report(False, "registry row", f"{REGISTRY_REL} does not parse: {error}")
    return finish(results)


def finish(results: list[tuple[bool, str, str]]) -> int:
    for ok, name, finding in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {finding}")
    failed = sum(1 for ok, _, _ in results if not ok)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or check a linked project vault.")
    parser.add_argument("command", choices=("create", "check"))
    parser.add_argument("id", help="lowercase kebab-case, 2-40 characters")
    parser.add_argument("--title", help="display title (create only; default: the id)")
    parser.add_argument("--projects-root", type=Path, default=MAIN.parent,
                        help="folder that holds project vaults (default: this vault's parent folder)")
    args = parser.parse_args(argv)
    if not ID_PATTERN.fullmatch(args.id) or args.id in RESERVED:
        parser.error("the id must be 2-40 characters of lowercase kebab-case (a-z, 0-9, single hyphens) "
                     "and not a reserved device name")
    title = args.title or args.id
    if not TITLE_PATTERN.fullmatch(title) or TITLE_FORBIDDEN.intersection(title):
        parser.error('the title must be 2-60 printable ASCII characters, start with a letter or digit, and '
                     'contain no quotes, backslashes, "[", "]" or "|"')
    root = args.projects_root.expanduser().resolve()
    if args.command == "create":
        return create(args.id, title, root)
    return check(args.id, root)


if __name__ == "__main__":
    sys.exit(main())
