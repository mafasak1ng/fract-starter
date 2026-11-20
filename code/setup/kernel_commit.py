#!/usr/bin/env python3
"""FRACT kernel commit: commit staged kernel changes with the owner's passkey.

Commits what is already staged, with the trigger word and the owner's passkey,
so the layer guard (`code/git-hooks/layer-guard.mjs`) can authorise a kernel
change. The passkey is typed at a hidden prompt and handed only to that one
`git commit` process, in its environment; it is never printed, logged, written
to disk, kept in shell history or left in the calling shell.

An agent may prepare and stage kernel edits after the owner's own message
carries the trigger word, but it never asks for, reads, types or echoes the
passkey: the owner runs this script and types it.

Usage (always with -B so Python writes no bytecode caches):
    Windows:        python -B code\\setup\\kernel_commit.py -m "kernel: <what changed>"
    Linux, macOS:   python3 -B code/setup/kernel_commit.py -m "kernel: <what changed>"

Exit codes: 0 committed, 1 commit refused, 2 nothing to do (nothing staged, no
kernel path staged, not this vault's own repository, or not an interactive
terminal), 130 cancelled.

It commits only what is staged; it stages, pushes and amends nothing. The guard
appends its decision to `_atlas/audit/<YYYY-MM>.jsonl`, which Git ignores.
The standard library only; Python 3.11 or newer.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import getpass
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_REL = "_atlas/layers.json"
TRIGGER = "KERNEL-UNLOCK"
ALWAYS_KERNEL = (POLICY_REL, "code/git-hooks/**")


def git(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], env=env)


def git_out(*args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8")
    return result.stdout if result.returncode == 0 else None


def matches(pattern: str, path: str) -> bool:
    """The guard's pattern shapes: `dir/**`, `dir/*`, an exact path, or a bare folder."""
    rule = pattern.strip().replace("\\", "/").lstrip("/")
    if not rule:
        return False
    if rule.endswith("/**"):
        prefix = rule[:-3]
        return path == prefix or path.startswith(prefix + "/")
    if rule.endswith("/*"):
        prefix = rule[:-2]
        return path.startswith(prefix + "/") and "/" not in path[len(prefix) + 1:]
    return path == rule or path.startswith(rule.rstrip("/") + "/")


def policy() -> dict:
    """The policy the guard will use: committed first, then staged, then the working file."""
    for text in (git_out("show", f"HEAD:{POLICY_REL}"), git_out("show", f":{POLICY_REL}")):
        if text is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {}
    try:
        return json.loads((ROOT / POLICY_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def is_kernel(path: str, manifest: dict) -> bool:
    """Same decision as the guard: always-kernel paths, then the most specific pattern."""
    if any(matches(rule, path) for rule in ALWAYS_KERNEL):
        return True
    best: tuple[int, str] | None = None
    for layer in (manifest.get("layers") or {}).values():
        for pattern in layer.get("paths") or []:
            if matches(pattern, path) and (best is None or len(pattern) > best[0]):
                best = (len(pattern), layer.get("writable", ""))
    if best is None:
        default = (manifest.get("layers") or {}).get(manifest.get("default", "docs"), {})
        return default.get("writable") == "kernel"
    return best[1] == "kernel"


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit staged kernel changes with a hidden passkey prompt.")
    parser.add_argument("-m", "--message", required=True, help="commit message")
    args = parser.parse_args()

    top = git_out("rev-parse", "--show-toplevel")
    if top is None or Path(top.strip()).resolve() != ROOT.resolve():
        print(f"{ROOT} is not the root of its own Git repository; nothing was committed.", file=sys.stderr)
        return 2

    names = [name for name in (git_out("diff", "--cached", "--name-only", "--no-renames", "-z") or "").split("\0") if name]
    if not names:
        print("Nothing is staged. Stage the kernel changes first, then run this again.", file=sys.stderr)
        return 2

    manifest = policy()
    kernel = [name for name in names if is_kernel(name, manifest)]
    if not kernel:
        print("None of the staged files is a kernel path, so the guard does not check a passkey.\n"
              "Do not type your passkey here; commit these files with a normal git commit.", file=sys.stderr)
        return 2

    if not sys.stdin.isatty():
        print("Run this in an interactive terminal so the passkey prompt can hide what you type.", file=sys.stderr)
        return 2

    print(f"Repository: {ROOT}")
    print("Staged for this commit:")
    git("diff", "--cached", "--stat")
    print("Kernel paths that need the passkey:")
    for name in kernel:
        print(f"  {name}")
    print(f"\nMessage: {args.message}")
    print(f"Trigger: {TRIGGER}")
    print("Type your passkey and press Enter (input is hidden). Press Ctrl+C to cancel.")

    try:
        passkey = getpass.getpass("Passkey: ")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing was committed.")
        return 130
    if not passkey:
        print("No passkey entered. Nothing was committed.", file=sys.stderr)
        return 1

    env = dict(os.environ)
    env["ATLAS_TRIGGER"] = TRIGGER
    env["ATLAS_PASSKEY"] = passkey
    try:
        result = git("commit", "-m", args.message, env=env)
    finally:
        env.pop("ATLAS_PASSKEY", None)
        passkey = ""

    if result.returncode == 0:
        print("\nCommitted.")
        git("log", "--oneline", "-1")
        return 0
    print("\nCommit refused. The files stay staged; run this again to retry.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
