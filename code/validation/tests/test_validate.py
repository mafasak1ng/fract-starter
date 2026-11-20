"""Tests for code/validation/validate.py.

Run from the starter root:

    python -B -m unittest discover -s code/validation/tests

Each test builds a tiny vault in a temporary directory, adds one defect, and
checks that the validator reports it. ``test_clean_vault_passes`` checks that a
correct vault produces no errors, both through ``validate()`` and through the
command line.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT = Path(__file__).resolve().parents[1] / "validate.py"
_spec = importlib.util.spec_from_file_location("fract_validate", SCRIPT)
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)

FILLER = "Body text for the note, long enough to sit inside its size range. " * 20


def frontmatter(**overrides) -> str:
    """Build valid note frontmatter; pass field=None to drop a field."""
    fields = {
        "node_id": '"sample-note"',
        "title": '"Sample Note"',
        "type": '"guide"',
        "parent": '"[[README|FRACT]]"',
        "status": '"active"',
        "version": '"1.0.0"',
        "revision": "1",
        "created": '"2026-11-20"',
        "updated": '"2026-11-20"',
        "change_type": '"minor"',
        "change_summary": '"Created the note."',
        "review_status": '"needs_review"',
        "tags": '\n  - "system"',
    }
    fields.update(overrides)
    lines = ["---"]
    for key, value in fields.items():
        if value is not None:
            lines.append(f"{key}: {value}" if not value.startswith("\n") else f"{key}:{value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


class VaultTestCase(unittest.TestCase):
    """Base class: a clean two-note vault plus a helper to run the validator."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write("README.md", frontmatter(
            node_id='"fract-readme"', title='"FRACT"', type='"guide"',
        ) + "# FRACT\n\nSee [[00-system/System Hub|System Hub]].\n" + FILLER)
        self.write("00-system/System Hub.md", frontmatter(
            node_id='"system-hub"', title='"System Hub"', type='"hub"',
            parent='"[[README|FRACT]]"',
        ) + "# System Hub\n\nBack to [[README|FRACT]].\n" + FILLER * 2)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, content: str | bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def note(self, rel: str, body: str = "", **fields) -> None:
        """Write a note linked from the hub, so it is not an orphan."""
        fields.setdefault("node_id", '"' + Path(rel).stem.lower().replace(" ", "-") + '"')
        self.write(rel, frontmatter(**fields) + body + "\n" + FILLER)
        hub = self.root / "00-system/System Hub.md"
        hub.write_text(hub.read_text(encoding="utf-8")
                       + f"\n- [[{rel[:-3]}]]\n", encoding="utf-8")

    def run_validator(self):
        return validate.validate(self.root)

    def assertError(self, results, path: str, fragment: str) -> None:
        hits = [f for f in results.errors if f[1] == path and fragment in f[2]]
        self.assertTrue(hits, f"expected ERROR on {path} containing {fragment!r}; "
                              f"got {results.findings}")


class CleanVaultTest(VaultTestCase):
    def test_clean_vault_passes(self) -> None:
        self.note("10-core/Core Index.md", "Links: [[00-system/System Hub#Top|hub]].",
                  type='"index"', aliases="[]", tags='["core", "index"]')
        self.write(".agents/skills/close-session/SKILL.md",
                   "---\nname: close-session\ndescription: Use when closing a session.\n---\n"
                   "# Close session\n")
        self.write("_atlas/layers.json", '{"layers": []}\n')
        self.write("code/tool.py", "print('ok')\n")
        results = self.run_validator()
        self.assertEqual(results.errors, [], results.findings)
        self.assertEqual(results.notes_checked, 3)

        proc = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--root", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("0 errors", proc.stdout.splitlines()[-1])
        self.assertFalse((SCRIPT.parent / "__pycache__").exists())

    def test_cli_exit_code_on_error_and_quiet(self) -> None:
        self.write("broken.json", "{")
        self.write("lonely.md", frontmatter(node_id='"lonely"') + "short\n")
        proc = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--root", str(self.root), "--quiet"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR broken.json: invalid JSON", proc.stdout)
        self.assertNotIn("WARN", proc.stdout)
        self.assertRegex(proc.stdout.splitlines()[-1], r"^1 errors, \d+ warnings, 3 notes checked$")

    def test_ignored_paths(self) -> None:
        self.write(".git/HEAD", "")
        self.write(".obsidian/workspace.json", "{")
        self.write("_atlas/audit/log.json", "{")
        self.write("LICENSE", "")
        self.assertEqual(self.run_validator().errors, [])


class FrontmatterTest(VaultTestCase):
    def test_missing_frontmatter(self) -> None:
        self.note("plain.md")
        (self.root / "plain.md").write_text("# No metadata\n", encoding="utf-8")
        self.assertError(self.run_validator(), "plain.md", "missing frontmatter")

    def test_unclosed_frontmatter(self) -> None:
        self.write("open.md", "---\nnode_id: open\n# never closed\n")
        self.assertError(self.run_validator(), "open.md", "not closed")

    def test_unsupported_yaml_line(self) -> None:
        self.note("odd.md")
        path = self.root / "odd.md"
        path.write_text(path.read_text().replace("---\n", "---\n{weird}\n", 1))
        self.assertError(self.run_validator(), "odd.md", "unsupported YAML")

    def test_duplicate_key(self) -> None:
        self.note("dup-key.md")
        path = self.root / "dup-key.md"
        path.write_text(path.read_text().replace('title: "Sample Note"',
                                                 'title: "A"\ntitle: "B"'))
        self.assertError(self.run_validator(), "dup-key.md", "duplicate key")

    def test_each_required_field_missing(self) -> None:
        for field in validate.REQUIRED_FIELDS:
            with self.subTest(field=field):
                rel = f"missing-{field.replace('_', '-')}.md"
                self.note(rel, **{field: None})
                self.assertError(self.run_validator(), rel, f"missing required field '{field}'")

    def test_empty_tags(self) -> None:
        self.note("no-tags.md", tags="[]")
        self.assertError(self.run_validator(), "no-tags.md", "'tags'")

    def test_bad_values(self) -> None:
        cases = {
            "type": ('"essay"', "type 'essay'"),
            "status": ('"live"', "status 'live'"),
            "change_type": ('"huge"', "change_type 'huge'"),
            "review_status": ('"done"', "review_status 'done'"),
            "node_id": ('"Bad_Id"', "not lowercase kebab-case"),
            "version": ('"1.0"', "not semver"),
            "revision": ('0', "integer >= 1"),
            "created": ('"2026-13-01"', "not a valid YYYY-MM-DD"),
            "parent": ('"System Hub"', "single wikilink"),
            "tags": ('"system"', "list of non-empty strings"),
        }
        for field, (value, fragment) in cases.items():
            with self.subTest(field=field):
                rel = f"bad-{field.replace('_', '-')}.md"
                self.note(rel, **{field: value})
                self.assertError(self.run_validator(), rel, fragment)

    def test_quoted_revision_is_not_an_integer(self) -> None:
        self.note("str-revision.md", revision='"1"')
        self.assertError(self.run_validator(), "str-revision.md", "integer >= 1")

    def test_updated_before_created(self) -> None:
        self.note("time-travel.md", created='"2026-11-20"', updated='"2026-11-19"')
        self.assertError(self.run_validator(), "time-travel.md", "updated is before created")

    def test_duplicate_node_id(self) -> None:
        self.note("one.md", node_id='"same-id"')
        self.note("two.md", node_id='"same-id"')
        results = self.run_validator()
        self.assertError(results, "two.md", "duplicate node_id 'same-id'")

    def test_comments_and_flow_lists_parse(self) -> None:
        self.note("parsed.md", title='"Hash # inside"  # trailing comment',
                  tags='["a", "b, c"]')
        results = self.run_validator()
        self.assertEqual(results.errors, [], results.findings)
        meta, _ = validate.parse_frontmatter((self.root / "parsed.md").read_text())
        self.assertEqual(meta["title"], "Hash # inside")
        self.assertEqual(meta["tags"], ["a", "b, c"])
        self.assertEqual(meta["revision"], 1)


class WikilinkTest(VaultTestCase):
    def test_unresolved_body_link(self) -> None:
        self.note("linker.md", "See [[10-core/Nowhere|nowhere]].")
        self.assertError(self.run_validator(), "linker.md", "unresolved wikilink [[10-core/Nowhere|nowhere]]")

    def test_unresolved_parent_previous_next(self) -> None:
        for field in ("parent", "previous", "next"):
            with self.subTest(field=field):
                rel = f"link-{field}.md"
                self.note(rel, **{field: '"[[Missing/Note|Missing]]"'})
                self.assertError(self.run_validator(), rel, "unresolved wikilink [[Missing/Note|Missing]]")

    def test_bare_name_is_not_path_qualified(self) -> None:
        self.note("bare.md", "See [[System Hub]].")
        self.assertError(self.run_validator(), "bare.md", "unresolved wikilink [[System Hub]]")

    def test_alias_heading_embed_and_table_pipe_resolve(self) -> None:
        self.write("90-assets/diagram.png", b"\x89PNG")
        self.note("ok-links.md",
                  "[[00-system/System Hub#Section|hub]] ![[90-assets/diagram.png]]\n"
                  "| a | [[README\\|FRACT]] |\n[[#Local heading]]")
        self.assertEqual(self.run_validator().errors, [])

    def test_links_in_code_are_ignored(self) -> None:
        self.note("code-links.md",
                  "Inline `[[Not/A Link]]` and ``[[Also/Not]]``.\n\n"
                  "```markdown\n[[Fenced/Link]]\n```\n\n~~~\n[[Tilde/Link]]\n~~~\n")
        self.assertEqual(self.run_validator().errors, [])

    def test_link_after_fence_is_checked(self) -> None:
        self.note("after-fence.md", "```\ncode\n```\n[[Real/Missing]]\n")
        self.assertError(self.run_validator(), "after-fence.md", "[[Real/Missing]]")


class SkillTest(VaultTestCase):
    def test_skill_missing_name(self) -> None:
        self.write(".agents/skills/alpha/SKILL.md", "---\ndescription: Use it.\n---\nBody\n")
        self.assertError(self.run_validator(), ".agents/skills/alpha/SKILL.md", "missing 'name'")

    def test_skill_missing_description(self) -> None:
        self.write(".agents/skills/alpha/SKILL.md", "---\nname: alpha\n---\nBody\n")
        self.assertError(self.run_validator(), ".agents/skills/alpha/SKILL.md", "missing 'description'")

    def test_skill_name_mismatch(self) -> None:
        self.write(".agents/skills/alpha/SKILL.md", "---\nname: beta\ndescription: Use it.\n---\n")
        self.assertError(self.run_validator(), ".agents/skills/alpha/SKILL.md", "does not match folder")

    def test_skill_without_frontmatter(self) -> None:
        self.write(".agents/skills/alpha/SKILL.md", "# Alpha\n")
        self.assertError(self.run_validator(), ".agents/skills/alpha/SKILL.md", "missing frontmatter")

    def test_skill_links_are_checked(self) -> None:
        self.write(".agents/skills/alpha/SKILL.md",
                   "---\nname: alpha\ndescription: Use it.\n---\nRead [[Gone/Note]].\n")
        self.assertError(self.run_validator(), ".agents/skills/alpha/SKILL.md", "[[Gone/Note]]")

    def test_skills_index_is_plain_markdown(self) -> None:
        self.write(".agents/skills/README.md", "# Skills\n\nSee [alpha](alpha/SKILL.md).\n")
        results = self.run_validator()
        self.assertFalse([f for f in results.findings if f[1] == ".agents/skills/README.md"],
                         results.findings)

    def test_skills_index_links_are_checked(self) -> None:
        self.write(".agents/skills/README.md", "# Skills\n\nRead [[Gone/Note]].\n")
        self.assertError(self.run_validator(), ".agents/skills/README.md", "[[Gone/Note]]")


class FileTest(VaultTestCase):
    def test_zero_byte_file(self) -> None:
        self.write("90-assets/empty.txt", "")
        self.assertError(self.run_validator(), "90-assets/empty.txt", "zero-byte")

    def test_zero_byte_note(self) -> None:
        self.write("empty.md", "")
        self.assertError(self.run_validator(), "empty.md", "zero-byte")

    def test_forbidden_names(self) -> None:
        for rel in ("Untitled.txt", "notes copy.txt", "Notes - Copy.txt", "data.bak",
                    "merge.orig", "draft.txt~", "photo (1).png", "Untitled folder/a.txt"):
            with self.subTest(rel=rel):
                self.write(rel, "x")
                findings = self.run_validator().errors
                flagged = rel.split("/")[0] + ("/" if "/" in rel else "")
                self.assertTrue(any(f[1] == flagged and "forbidden name" in f[2] for f in findings),
                                findings)

    def test_pycache_and_pyc(self) -> None:
        self.write("code/__pycache__/x.cpython-311.pyc", b"\x00")
        self.write("code/stray.pyc", b"\x00")
        results = self.run_validator()
        self.assertError(results, "code/__pycache__/", "__pycache__")
        self.assertError(results, "code/stray.pyc", "compiled Python")

    def test_invalid_json(self) -> None:
        self.write("_atlas/layers.json", '{"a": 1,}')
        self.assertError(self.run_validator(), "_atlas/layers.json", "invalid JSON")

    def test_python_syntax_error(self) -> None:
        self.write("code/broken.py", "def f(:\n    pass\n")
        self.assertError(self.run_validator(), "code/broken.py", "does not compile")


class WarningTest(VaultTestCase):
    def test_size_and_orphan_are_warnings_only(self) -> None:
        self.write("orphan.md", frontmatter(node_id='"orphan"', type='"index"') + "tiny\n")
        results = self.run_validator()
        self.assertEqual(results.errors, [])
        messages = [f[2] for f in results.warnings if f[1] == "orphan.md"]
        self.assertTrue(any("outside index range" in m for m in messages), messages)
        self.assertTrue(any("orphan note" in m for m in messages), messages)
        self.assertFalse(any(f[1] == "README.md" and "orphan" in f[2] for f in results.warnings))


if __name__ == "__main__":
    unittest.main()
