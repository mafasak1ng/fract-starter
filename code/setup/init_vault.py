#!/usr/bin/env python3
"""FRACT first-time setup: set the owner's passkey and turn the commit guard on.

What it does:
    1. Asks twice for a passkey at a hidden prompt (at least 12 characters).
    2. Hashes it with scrypt (N=16384, r=8, p=1, 32-byte key, random 16-byte
       salt) and writes only the salt and hash into `_atlas/layers.json`
       under `kernel.passkey`. The passkey itself is never printed, logged or
       written anywhere.
    3. Sets `git config core.hooksPath code/git-hooks` in this vault's own Git
       repository, so every commit goes through the layer guard.
    4. Prints the next steps: commit the new policy through kernel_commit.py.

Usage (run from anywhere; always with -B so Python writes no bytecode caches):
    Windows:        python -B code\\setup\\init_vault.py
    Linux, macOS:   python3 -B code/setup/init_vault.py

Options:
    --reset   Replace an existing passkey. Asks for the current passkey first.

Exit codes: 0 done, 1 refused or failed, 130 cancelled.

The standard library only; Python 3.11 or newer.
"""

import sys

sys.dont_write_bytecode = True

import argparse
import getpass
import hashlib
import hmac
import json
import secrets
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_REL = "_atlas/layers.json"
HOOKS_PATH = "code/git-hooks"
MIN_LENGTH = 12
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LENGTH = 32
SALT_BYTES = 16
SCRYPT_MAXMEM = 64 * 1024 * 1024


def make_record(passkey: str, salt: bytes | None = None) -> dict:
    """The scrypt record layer-guard.mjs verifies. Same parameters, same NFKC normalisation."""
    salt = secrets.token_bytes(SALT_BYTES) if salt is None else salt
    digest = hashlib.scrypt(
        unicodedata.normalize("NFKC", passkey).encode("utf-8"),
        salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_LENGTH, maxmem=SCRYPT_MAXMEM,
    )
    return {
        "algorithm": "scrypt",
        "N": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "keylen": KEY_LENGTH,
        "salt": salt.hex(),
        "hash": digest.hex(),
    }


def verify(passkey: str, record: dict | None) -> bool:
    """True when the passkey matches a stored record (constant-time compare)."""
    if not isinstance(record, dict) or not passkey:
        return False
    try:
        expected = bytes.fromhex(record["hash"])
        salt = bytes.fromhex(record["salt"])
        actual = hashlib.scrypt(
            unicodedata.normalize("NFKC", passkey).encode("utf-8"),
            salt=salt, n=int(record.get("N", SCRYPT_N)), r=int(record.get("r", SCRYPT_R)),
            p=int(record.get("p", SCRYPT_P)), dklen=len(expected), maxmem=SCRYPT_MAXMEM,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def check_passkey(passkey: str) -> str | None:
    """Why a new passkey is not acceptable, or None when it is."""
    if len(passkey) < MIN_LENGTH:
        return f"The passkey must be at least {MIN_LENGTH} characters."
    if passkey != passkey.strip():
        return "The passkey must not start or end with a space."
    return None


def load_policy(root: Path) -> dict:
    return json.loads((root / POLICY_REL).read_text(encoding="utf-8"))


def write_record(root: Path, record: dict) -> None:
    """Store the record in the policy file, leaving every other field as it was."""
    policy = load_policy(root)
    policy.setdefault("kernel", {})["passkey"] = record
    text = json.dumps(policy, indent=2, ensure_ascii=False) + "\n"
    (root / POLICY_REL).write_text(text, encoding="utf-8", newline="\n")


def git_toplevel(root: Path) -> Path | None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def enable_hooks(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", HOOKS_PATH], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set the vault's passkey and turn the commit guard on.")
    parser.add_argument("--reset", action="store_true", help="replace an existing passkey")
    args = parser.parse_args()

    top = git_toplevel(ROOT)
    if top is None:
        print(f"{ROOT} is not a Git repository. Run `git init` there first, then run this again.", file=sys.stderr)
        return 1
    if top != ROOT.resolve():
        print(f"This vault ({ROOT}) is inside another repository ({top}), not its own. "
              "Give the vault its own repository so the guard does not act on the outer one.", file=sys.stderr)
        return 1
    if not sys.stdin.isatty():
        print("Run this in an interactive terminal so the passkey prompt can hide what you type.", file=sys.stderr)
        return 1

    try:
        policy = load_policy(ROOT)
    except (OSError, ValueError) as error:
        print(f"Cannot read {POLICY_REL}: {error}", file=sys.stderr)
        return 1
    current = (policy.get("kernel") or {}).get("passkey")

    try:
        if current and not args.reset:
            print("A passkey is already set. To replace it, run this again with --reset.", file=sys.stderr)
            return 1
        if args.reset:
            if not current:
                print("No passkey is set yet; run this without --reset.", file=sys.stderr)
                return 1
            if not verify(getpass.getpass("Current passkey: "), current):
                print("The current passkey did not match. Nothing was changed.", file=sys.stderr)
                return 1

        print(f"Choose a passkey of at least {MIN_LENGTH} characters. Input is hidden; Ctrl+C cancels.")
        first = getpass.getpass("New passkey: ")
        problem = check_passkey(first)
        if problem:
            print(f"{problem} Nothing was changed.", file=sys.stderr)
            return 1
        if getpass.getpass("Repeat it: ") != first:
            print("The two entries differ. Nothing was changed.", file=sys.stderr)
            return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing was changed.")
        return 130

    write_record(ROOT, make_record(first))
    first = ""
    enable_hooks(ROOT)

    print(f"\nThe passkey's salted hash is in {POLICY_REL}; the passkey itself is stored nowhere.")
    print(f"The commit guard is on (core.hooksPath = {HOOKS_PATH}).")
    print("\nNext steps:")
    print(f"  1. Stage the policy:   git add {POLICY_REL}")
    print('  2. Commit it:          python -B code/setup/kernel_commit.py -m "kernel: set the passkey"')
    if args.reset:
        print("     At the prompt type your OLD passkey: the guard checks the record already committed.")
    else:
        print("     At the prompt type the passkey you just chose.")
    print("  3. Check the vault:    python -B code/validation/validate.py")
    print("Keep the passkey somewhere safe. See 00-system/Layer Guard.md if it is ever lost.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
