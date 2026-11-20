"""Read-only validator for a FRACT vault.

Usage (from the vault root):

    python -B code/validation/validate.py [--root PATH] [--quiet]

Options:
    --root PATH   Vault to check. Default: two levels above this script.
    --quiet       Print errors and the summary line only; hide warnings.

Exit status: 0 when no errors were found, 1 when at least one error was
found. Warnings never change the exit status.

Output: one line per finding, ``ERROR <path>: <message>`` or
``WARN  <path>: <message>``, followed by a summary line
``N errors, M warnings, K notes checked``.

What it checks:

Errors
  * Every Markdown note has YAML frontmatter with all required fields, each
    valid: enums, semver ``version``, ISO dates, ``updated >= created``,
    integer ``revision >= 1``, kebab-case ``node_id``, non-empty ``tags``.
    Skill files (``.agents/skills/**/SKILL.md``) are exempt from the note
    metadata and are checked for ``name`` (equal to the folder name) and
    ``description`` instead.
  * ``node_id`` values are unique across the vault.
  * Every wikilink (body, ``parent``, ``previous``, ``next``) resolves to an
    existing file. Links are path-qualified from the vault root; ``.md`` may
    be left out. ``|alias`` and ``#heading`` are stripped. Links inside fenced
    code blocks and inline code are ignored.
  * No zero-byte files, no leftover names (``Untitled*``, ``* copy*``,
    ``*.bak``, ``*.orig``, ``*~``, ``name (1).ext``), no ``__pycache__`` or
    ``*.pyc``.
  * Every ``*.json`` parses and every ``*.py`` compiles (in memory; no
    bytecode is written).

Warnings
  * Note size outside the range for its ``type`` (characters, frontmatter
    included).
  * Orphan notes: no incoming wikilink from any other file (the root
    ``README.md`` is exempt).

Skipped: ``.git/``, ``.obsidian/``, ``_atlas/audit/`` and ``LICENSE``.
The skills index ``.agents/skills/README.md`` is plain Markdown: it needs no
frontmatter and is not an orphan candidate, but its wikilinks must resolve.

The validator never writes to the vault. It uses the Python standard library
only and parses the small YAML subset FRACT notes use: ``key: value`` scalars
(quoted or plain), integers, booleans, block lists (``- item``), flow lists
(``[a, b]``) and ``#`` comments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

REQUIRED_FIELDS = (
    "node_id", "title", "type", "parent", "status", "version", "revision",
    "created", "updated", "change_type", "change_summary", "review_status",
    "tags",
)
ENUMS = {
    "type": {"index", "hub", "contract", "operations", "data-model",
             "template", "record", "policy", "guide"},
    "status": {"active", "draft", "deprecated"},
    "change_type": {"major", "minor", "patch"},
    "review_status": {"needs_review", "approved"},
}
LINK_FIELDS = ("parent", "previous", "next")

# Size range per note type, in characters, frontmatter included.
SIZE_RANGES = {
    "index": (1_000, 3_000),
    "hub": (2_000, 6_000),
    "contract": (3_000, 8_000),
    "operations": (3_000, 10_000),
    "data-model": (2_000, 10_000),
    "template": (1_000, 10_000),
    "record": (1_000, 12_000),
    "policy": (3_000, 12_000),
    "guide": (1_000, 10_000),
}

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WIKILINK_VALUE = re.compile(r"^\[\[[^\[\]\n]+\]\]$")
WIKILINK = re.compile(r"!?\[\[([^\[\]\n]+?)\]\]")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")

# Leftover names produced by editors, sync clients and file managers.
FORBIDDEN_NAMES = (
    (re.compile(r"^untitled", re.I), "untitled file name"),
    (re.compile(r" copy", re.I), "copy in file name"),
    (re.compile(r"\.(bak|orig)$", re.I), "backup file"),
    (re.compile(r"~$"), "editor backup file"),
    (re.compile(r" \(\d+\)(\.[^.]*)?$"), "numbered copy"),
    (re.compile(r"\.pyc$", re.I), "compiled Python file"),
)

SKIP_DIRS = {".git", ".obsidian", "_atlas/audit"}
SKIP_FILES = {"LICENSE"}
# Markdown files that are plain documents, not notes: no frontmatter, no
# orphan check, but their wikilinks (if any) must still resolve.
PLAIN_MARKDOWN = {".agents/skills/README.md"}
ROOT_NOTE = "README.md"


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

class Results:
    """Collects findings as (level, path, message) tuples."""

    def __init__(self) -> None:
        self.findings: list[tuple[str, str, str]] = []
        self.notes_checked = 0

    def error(self, path: str, message: str) -> None:
        self.findings.append(("ERROR", path, message))

    def warn(self, path: str, message: str) -> None:
        self.findings.append(("WARN", path, message))

    @property
    def errors(self) -> list[tuple[str, str, str]]:
        return [f for f in self.findings if f[0] == "ERROR"]

    @property
    def warnings(self) -> list[tuple[str, str, str]]:
        return [f for f in self.findings if f[0] == "WARN"]


# --------------------------------------------------------------------------
# Frontmatter parsing (YAML subset)
# --------------------------------------------------------------------------

class FrontmatterError(ValueError):
    """Raised when frontmatter is missing or outside the supported subset."""


def strip_comment(raw: str) -> str:
    """Remove a trailing ``# comment`` that sits outside quotes."""
    quote, escaped = None, False
    for i, ch in enumerate(raw):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\" and quote == '"':
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or raw[i - 1] in " \t"):
            return raw[:i].rstrip()
    return raw.rstrip()


def split_flow_list(inner: str) -> list[str]:
    """Split the inside of ``[a, "b, c"]`` on commas outside quotes."""
    items, current, quote = [], "", None
    for ch in inner:
        if quote:
            current += ch
            if ch == quote and not current.endswith("\\" + quote):
                quote = None
        elif ch in "\"'":
            quote = ch
            current += ch
        elif ch == ",":
            items.append(current)
            current = ""
        else:
            current += ch
    if current.strip() or items:
        items.append(current)
    return [item.strip() for item in items]


def parse_scalar(raw: str):
    """Turn one YAML scalar into a Python value."""
    raw = raw.strip()
    if raw.startswith('"'):
        if len(raw) < 2 or not raw.endswith('"'):
            raise FrontmatterError(f"unterminated string {raw!r}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FrontmatterError(f"bad double-quoted string {raw!r}") from exc
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'"):
            raise FrontmatterError(f"unterminated string {raw!r}")
        return raw[1:-1].replace("''", "'")
    if raw.startswith("["):
        if not raw.endswith("]"):
            raise FrontmatterError(f"unterminated list {raw!r}")
        return [parse_scalar(item) for item in split_flow_list(raw[1:-1])]
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if raw in ("true", "false"):
        return raw == "true"
    if raw in ("", "null", "~"):
        return None
    return raw


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (fields, body). Raise FrontmatterError."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("missing frontmatter (file must start with '---')")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise FrontmatterError("frontmatter is not closed with '---'") from None

    data: dict = {}
    bare_keys: set[str] = set()  # "key:" with no inline value
    current_list: str | None = None
    for number in range(1, end):
        line = strip_comment(lines[number]) if lines[number].strip() else ""
        if not line.strip():
            continue
        item = re.match(r"^\s+-\s*(.*)$", line) or re.match(r"^-\s+(.*)$", line)
        if item:
            if current_list is None:
                raise FrontmatterError(f"line {number + 1}: list item without a key")
            data[current_list].append(parse_scalar(item.group(1)))
            continue
        pair = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*)|\s*)$", line)
        if not pair:
            raise FrontmatterError(f"line {number + 1}: unsupported YAML {line.strip()!r}")
        key, raw = pair.group(1), (pair.group(2) or "").strip()
        if key in data:
            raise FrontmatterError(f"line {number + 1}: duplicate key '{key}'")
        if raw:
            data[key] = parse_scalar(raw)
            current_list = None
        else:
            data[key] = []  # becomes a block list if items follow
            bare_keys.add(key)
            current_list = key
    # A bare key with no list items is empty (None), not an empty list.
    for key in bare_keys:
        if data[key] == []:
            data[key] = None
    return data, "\n".join(lines[end + 1:])


# --------------------------------------------------------------------------
# Wikilinks
# --------------------------------------------------------------------------

def strip_code(body: str) -> str:
    """Blank out fenced code blocks and inline code so links there are ignored."""
    out, fence = [], None
    for line in body.split("\n"):
        match = FENCE.match(line)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
            out.append("")
            continue
        if match:
            fence = match.group(1)
            out.append("")
            continue
        out.append(INLINE_CODE.sub("", line))
    return "\n".join(out)


def link_target(raw: str) -> str:
    """``path/Note#Heading|Alias`` -> ``path/Note``."""
    target = raw.replace("\\|", "|").split("|", 1)[0]
    return target.split("#", 1)[0].strip()


def resolve(target: str, files: set[str]) -> str | None:
    """Resolve a path-qualified link target to a vault-relative file path."""
    if target in files:
        return target
    if target + ".md" in files:
        return target + ".md"
    return None


def collect_links(text: str) -> list[str]:
    return [m.group(1) for m in WIKILINK.finditer(strip_code(text))]


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def walk(root: Path, results: Results) -> list[str]:
    """List vault files (posix, root-relative); report cache directories."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        keep = []
        for name in sorted(dirnames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if rel in SKIP_DIRS:
                continue
            if name == "__pycache__":
                results.error(rel + "/", "__pycache__ directory (run Python with -B)")
                continue
            check_name(rel + "/", name, results)
            keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if rel not in SKIP_FILES:
                files.append(rel)
    return files


def check_name(rel: str, name: str, results: Results) -> None:
    for pattern, label in FORBIDDEN_NAMES:
        if pattern.search(name):
            results.error(rel, f"forbidden name ({label})")
            return


def check_file(root: Path, rel: str, results: Results) -> None:
    """Name, size and syntax checks that apply to every file."""
    path = root / rel
    check_name(rel, path.name, results)
    if path.stat().st_size == 0:
        results.error(rel, "zero-byte file")
        return
    if path.suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            results.error(rel, f"invalid JSON ({exc})")
    elif path.suffix == ".py":
        try:
            compile(path.read_text(encoding="utf-8"), rel, "exec")
        except (UnicodeDecodeError, SyntaxError, ValueError) as exc:
            results.error(rel, f"Python does not compile ({exc})")


def is_skill(rel: str) -> bool:
    return rel.startswith(".agents/skills/") and rel.endswith("/SKILL.md")


def check_skill(rel: str, meta: dict, results: Results) -> None:
    folder = rel.split("/")[-2]
    name, description = meta.get("name"), meta.get("description")
    if not isinstance(name, str) or not name.strip():
        results.error(rel, "skill is missing 'name'")
    elif name != folder:
        results.error(rel, f"skill name '{name}' does not match folder '{folder}'")
    elif not KEBAB.match(name):
        results.error(rel, f"skill name '{name}' is not kebab-case")
    if not isinstance(description, str) or not description.strip():
        results.error(rel, "skill is missing 'description'")
    extra = sorted(set(meta) - {"name", "description"})
    if extra:
        results.warn(rel, f"skill has extra metadata: {', '.join(extra)}")


def parse_date(value) -> dt.date | None:
    if not isinstance(value, str) or not ISO_DATE.match(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def check_note_fields(rel: str, meta: dict, results: Results) -> None:
    """Validate the required note metadata from the shared standard."""
    for field in REQUIRED_FIELDS:
        if meta.get(field) in (None, "", []):
            results.error(rel, f"missing required field '{field}'")
    for field, allowed in ENUMS.items():
        value = meta.get(field)
        if value not in (None, "") and value not in allowed:
            results.error(rel, f"{field} '{value}' is not one of: {', '.join(sorted(allowed))}")

    node_id = meta.get("node_id")
    if node_id not in (None, "") and not (isinstance(node_id, str) and KEBAB.match(node_id)):
        results.error(rel, f"node_id '{node_id}' is not lowercase kebab-case")
    title = meta.get("title")
    if title not in (None, "") and not isinstance(title, str):
        results.error(rel, "title must be a string")
    version = meta.get("version")
    if version not in (None, "") and not (isinstance(version, str) and SEMVER.match(version)):
        results.error(rel, f"version '{version}' is not semver (MAJOR.MINOR.PATCH)")
    revision = meta.get("revision")
    if revision not in (None, "") and (type(revision) is not int or revision < 1):
        results.error(rel, f"revision '{revision}' must be an integer >= 1")

    dates = {}
    for field in ("created", "updated"):
        value = meta.get(field)
        if value in (None, ""):
            continue
        dates[field] = parse_date(value)
        if dates[field] is None:
            results.error(rel, f"{field} '{value}' is not a valid YYYY-MM-DD date")
    if dates.get("created") and dates.get("updated") and dates["updated"] < dates["created"]:
        results.error(rel, "updated is before created")

    summary = meta.get("change_summary")
    if summary not in (None, "") and not isinstance(summary, str):
        results.error(rel, "change_summary must be a string")
    tags = meta.get("tags")
    if tags not in (None, "", []) and not (
        isinstance(tags, list) and all(isinstance(t, str) and t.strip() for t in tags)
    ):
        results.error(rel, "tags must be a list of non-empty strings")
    aliases = meta.get("aliases")
    if "aliases" in meta and aliases is not None and not isinstance(aliases, list):
        results.error(rel, "aliases must be a list")
    for field in LINK_FIELDS:
        value = meta.get(field)
        if value in (None, ""):
            continue
        if not (isinstance(value, str) and WIKILINK_VALUE.match(value)):
            results.error(rel, f"{field} must be a single wikilink like \"[[path/Note|Title]]\"")


def check_markdown(root: Path, md_files: list[str], all_files: set[str],
                   results: Results) -> None:
    """Frontmatter, skill metadata, unique ids, links, sizes and orphans."""
    node_ids: dict[str, str] = {}
    incoming: dict[str, set[str]] = {rel: set() for rel in md_files}
    notes: list[str] = []
    sizes: dict[str, tuple[int, object]] = {}

    for rel in md_files:
        path = root / rel
        if path.stat().st_size == 0:
            continue  # already reported as zero-byte
        try:
            text = path.read_text(encoding="utf-8").lstrip("﻿")
        except UnicodeDecodeError as exc:
            results.error(rel, f"not valid UTF-8 ({exc})")
            continue
        skill = is_skill(rel)
        if rel in PLAIN_MARKDOWN:
            meta, body = None, text  # no metadata; links are still checked
        else:
            try:
                meta, body = parse_frontmatter(text)
            except FrontmatterError as exc:
                results.error(rel, f"{'skill ' if skill else ''}frontmatter: {exc}")
                meta, body = None, text

        if rel in PLAIN_MARKDOWN:
            pass
        elif skill:
            if meta is not None:
                check_skill(rel, meta, results)
        else:
            notes.append(rel)
            results.notes_checked += 1
            if meta is not None:
                check_note_fields(rel, meta, results)
                node_id = meta.get("node_id")
                if isinstance(node_id, str) and node_id:
                    if node_id in node_ids:
                        results.error(rel, f"duplicate node_id '{node_id}' (also in {node_ids[node_id]})")
                    else:
                        node_ids[node_id] = rel
                sizes[rel] = (len(text), meta.get("type"))

        # Links from metadata fields, then from the body.
        raw_links = []
        if meta is not None:
            for field in LINK_FIELDS:
                value = meta.get(field)
                if isinstance(value, str):
                    raw_links += [m.group(1) for m in WIKILINK.finditer(value)]
        raw_links += collect_links(body)
        for raw in raw_links:
            target = link_target(raw)
            if not target:
                continue  # same-note heading link: [[#Heading]]
            found = resolve(target, all_files)
            if found is None:
                results.error(rel, f"unresolved wikilink [[{raw}]]")
            elif found in incoming and found != rel:
                incoming[found].add(rel)

    for rel, (length, note_type) in sizes.items():
        if note_type in SIZE_RANGES:
            low, high = SIZE_RANGES[note_type]
            if not low <= length <= high:
                results.warn(rel, f"size {length:,} chars outside {note_type} range {low:,}-{high:,}")
    for rel in notes:
        if rel != ROOT_NOTE and not incoming[rel]:
            results.warn(rel, "orphan note (no incoming wikilinks)")


def validate(root: Path) -> Results:
    """Run every check on the vault at ``root`` and return the findings."""
    results = Results()
    root = root.resolve()
    files = walk(root, results)
    for rel in files:
        check_file(root, rel, results)
    md_files = [rel for rel in files if rel.endswith(".md")]
    linkable = set(files) | {f for f in SKIP_FILES if (root / f).is_file()}
    check_markdown(root, md_files, linkable, results)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a FRACT vault (read-only).")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="vault root (default: two levels above this script)")
    parser.add_argument("--quiet", action="store_true", help="hide warnings")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"ERROR {args.root}: vault root is not a directory")
        return 1

    results = validate(args.root)
    for level, path, message in sorted(results.findings, key=lambda f: (f[0] != "ERROR", f[1])):
        if args.quiet and level == "WARN":
            continue
        print(f"{level:<5} {path}: {message}")
    print(f"{len(results.errors)} errors, {len(results.warnings)} warnings, "
          f"{results.notes_checked} notes checked")
    return 1 if results.errors else 0


if __name__ == "__main__":
    sys.exit(main())
