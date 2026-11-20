"""Tests for the layer guard, init_vault and new_project.

Run from the vault root (standard library only):
    python -B -m unittest discover -s code/setup/tests -v

Every test works in its own temporary Git repository and removes it afterwards;
nothing touches the vault the tests live in. The guard tests need Node.js: they
use `node` from PATH, or `node.exe` (a Windows Node reached from WSL), or the
ATLAS_NODE environment variable, and are skipped with a message when none exists.
"""

import sys

sys.dont_write_bytecode = True

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

STARTER = Path(__file__).resolve().parents[3]
PASSKEY = "correct horse battery staple"
OTHER_PASSKEY = "a different long passphrase"
FIXTURE_FILES = (
    ".gitattributes",
    ".gitignore",
    "_atlas/layers.json",
    "_atlas/registry/projects.json",
    "code/git-hooks/pre-commit",
    "code/git-hooks/layer-guard.mjs",
    "code/setup/init_vault.py",
    "code/setup/kernel_commit.py",
    "code/setup/new_project.py",
)


def load_init_vault():
    spec = importlib.util.spec_from_file_location("init_vault", STARTER / "code/setup/init_vault.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init_vault = load_init_vault()


def find_node() -> str | None:
    for candidate in (os.environ.get("ATLAS_NODE"), "node", "node.exe"):
        if candidate and shutil.which(candidate):
            return candidate
    return None


NODE = find_node()
NO_NODE = "Node.js not found (no node, node.exe or ATLAS_NODE), so the commit guard cannot run here."


def git_env(extra: dict | None = None) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "ATLAS_"))}
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test Owner",
        "GIT_AUTHOR_EMAIL": "test-owner",
        "GIT_COMMITTER_NAME": "Test Owner",
        "GIT_COMMITTER_EMAIL": "test-owner",
    })
    if NODE:
        env["ATLAS_NODE"] = NODE
    env.update(extra or {})
    return env


def run_git(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=git_env(env))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_vault(root: Path, record: dict | None) -> Path:
    """A minimal vault repository with the starter's guard, committed, guard on."""
    root.mkdir(parents=True)
    for rel in FIXTURE_FILES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(STARTER / rel, target)
    (root / "code/git-hooks/pre-commit").chmod(0o755)
    write(root / "AGENTS.md", "# AGENTS.md\n")
    write(root / "README.md", "# Vault\n")
    write(root / "10-core/Core Index.md", "# Core\n")
    policy = json.loads((root / "_atlas/layers.json").read_text(encoding="utf-8"))
    policy["kernel"]["passkey"] = record
    write(root / "_atlas/layers.json", json.dumps(policy, indent=2) + "\n")
    for args in (("init", "-q"), ("symbolic-ref", "HEAD", "refs/heads/main"), ("add", "--all"),
                 ("update-index", "--chmod=+x", "code/git-hooks/pre-commit"),
                 ("commit", "-q", "--no-verify", "-m", "bootstrap"),
                 ("config", "core.hooksPath", "code/git-hooks")):
        result = run_git(root, *args)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)}: {result.stderr}")
    return root


def audit_lines(repo: Path) -> list[dict]:
    lines = []
    for file in sorted((repo / "_atlas/audit").glob("*.jsonl")):
        lines.extend(json.loads(line) for line in file.read_text(encoding="utf-8").splitlines() if line)
    return lines


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fract-test-")
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class PasskeyHashingTests(unittest.TestCase):
    def test_record_shape(self):
        record = init_vault.make_record(PASSKEY)
        self.assertEqual(record["algorithm"], "scrypt")
        self.assertEqual((record["N"], record["r"], record["p"], record["keylen"]), (16384, 8, 1, 32))
        self.assertEqual(len(bytes.fromhex(record["salt"])), 16)
        self.assertEqual(len(bytes.fromhex(record["hash"])), 32)
        self.assertNotIn(PASSKEY, json.dumps(record))

    def test_verify(self):
        record = init_vault.make_record(PASSKEY)
        self.assertTrue(init_vault.verify(PASSKEY, record))
        self.assertFalse(init_vault.verify(OTHER_PASSKEY, record))
        self.assertFalse(init_vault.verify("", record))
        self.assertFalse(init_vault.verify(PASSKEY, None))

    def test_random_salt(self):
        self.assertNotEqual(init_vault.make_record(PASSKEY)["salt"], init_vault.make_record(PASSKEY)["salt"])

    def test_passkey_rules(self):
        self.assertIsNotNone(init_vault.check_passkey("short"))
        self.assertIsNotNone(init_vault.check_passkey(" leading space passkey"))
        self.assertIsNone(init_vault.check_passkey(PASSKEY))

    def test_write_record_keeps_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_atlas").mkdir()
            shutil.copyfile(STARTER / "_atlas/layers.json", root / "_atlas/layers.json")
            before = json.loads((root / "_atlas/layers.json").read_text(encoding="utf-8"))
            record = init_vault.make_record(PASSKEY)
            init_vault.write_record(root, record)
            after = json.loads((root / "_atlas/layers.json").read_text(encoding="utf-8"))
            self.assertEqual(after["kernel"]["passkey"], record)
            after["kernel"]["passkey"] = None
            self.assertEqual(after, before)


@unittest.skipUnless(NODE, NO_NODE)
class GuardTests(TempDirCase):
    def setUp(self):
        super().setUp()
        self.record = init_vault.make_record(PASSKEY)
        self.repo = build_vault(self.tmp / "vault", self.record)

    def commit(self, message: str, trigger: str | None = None, passkey: str | None = None):
        env = {}
        if trigger is not None:
            env["ATLAS_TRIGGER"] = trigger
        if passkey is not None:
            env["ATLAS_PASSKEY"] = passkey
        return run_git(self.repo, "commit", "-q", "-m", message, env=env)

    def stage(self, rel: str, text: str) -> None:
        write(self.repo / rel, text)
        self.assertEqual(run_git(self.repo, "add", rel).returncode, 0)

    def test_docs_commit_passes(self):
        self.stage("10-core/Core Index.md", "# Core\n\nMore.\n")
        result = self.commit("docs: edit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(audit_lines(self.repo), [])

    def test_kernel_commit_without_unlock_refused(self):
        self.stage("AGENTS.md", "# AGENTS.md\n\nChanged.\n")
        result = self.commit("kernel: edit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commit refused", result.stderr)
        result = self.commit("kernel: edit", trigger="KERNEL-UNLOCK")
        self.assertNotEqual(result.returncode, 0)
        result = self.commit("kernel: edit", passkey=PASSKEY)
        self.assertNotEqual(result.returncode, 0, "a passkey without the trigger must be refused")
        self.assertTrue(all(not line["allowed"] for line in audit_lines(self.repo)))

    def test_kernel_commit_with_passkey_passes_and_is_audited(self):
        self.stage("README.md", "# Vault\n\nChanged.\n")
        self.stage("10-core/Core Index.md", "# Core\n\nAlso changed.\n")
        result = self.commit("kernel: edit", trigger="KERNEL-UNLOCK", passkey=PASSKEY)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = audit_lines(self.repo)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(set(line), {"time", "path", "layer", "allowed", "reason", "via"})
        self.assertEqual((line["path"], line["layer"], line["allowed"], line["via"]),
                         ("README.md", "kernel", True, "git-pre-commit"))
        log = "\n".join(path.read_text(encoding="utf-8") for path in (self.repo / "_atlas/audit").glob("*"))
        self.assertNotIn(PASSKEY, log)

    def test_wrong_passkey_refused(self):
        self.stage("code/git-hooks/pre-commit", (self.repo / "code/git-hooks/pre-commit").read_text() + "\n")
        result = self.commit("kernel: edit", trigger="KERNEL-UNLOCK", passkey=OTHER_PASSKEY)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("passkey did not match", result.stderr)
        self.assertEqual([line["allowed"] for line in audit_lines(self.repo)], [False])

    def test_guard_uses_committed_policy(self):
        attacker = init_vault.make_record(OTHER_PASSKEY)
        policy = json.loads((self.repo / "_atlas/layers.json").read_text(encoding="utf-8"))
        policy["kernel"]["passkey"] = attacker
        policy["layers"]["kernel"]["paths"].remove("README.md")
        self.stage("_atlas/layers.json", json.dumps(policy, indent=2) + "\n")
        self.stage("README.md", "# Vault\n\nChanged.\n")
        result = self.commit("kernel: swap the passkey", trigger="KERNEL-UNLOCK", passkey=OTHER_PASSKEY)
        self.assertNotEqual(result.returncode, 0, "a staged policy must not authorise itself")
        result = self.commit("kernel: swap the passkey", trigger="KERNEL-UNLOCK", passkey=PASSKEY)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_uncommitted_guard_edit_does_not_run(self):
        write(self.repo / "code/git-hooks/layer-guard.mjs", "process.exit(0);\n")
        self.stage("AGENTS.md", "# AGENTS.md\n\nChanged.\n")
        result = self.commit("kernel: edit")
        self.assertNotEqual(result.returncode, 0, "the guard must run from HEAD, not the working tree")


@unittest.skipUnless(NODE, NO_NODE)
class FirstPasskeyTests(TempDirCase):
    def setUp(self):
        super().setUp()
        self.repo = build_vault(self.tmp / "vault", None)

    def test_kernel_refused_until_passkey_set(self):
        write(self.repo / "AGENTS.md", "# AGENTS.md\n\nChanged.\n")
        run_git(self.repo, "add", "AGENTS.md")
        result = run_git(self.repo, "commit", "-q", "-m", "kernel: edit",
                         env={"ATLAS_TRIGGER": "KERNEL-UNLOCK", "ATLAS_PASSKEY": PASSKEY})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("init_vault.py", result.stderr)

    def test_init_vault_record_commits_through_guard(self):
        init_vault.write_record(self.repo, init_vault.make_record(PASSKEY))
        run_git(self.repo, "add", "_atlas/layers.json")
        result = run_git(self.repo, "commit", "-q", "-m", "kernel: set the passkey",
                         env={"ATLAS_TRIGGER": "KERNEL-UNLOCK", "ATLAS_PASSKEY": OTHER_PASSKEY})
        self.assertNotEqual(result.returncode, 0)
        result = run_git(self.repo, "commit", "-q", "-m", "kernel: set the passkey",
                         env={"ATLAS_TRIGGER": "KERNEL-UNLOCK", "ATLAS_PASSKEY": PASSKEY})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_passkey_cannot_carry_other_policy_edits(self):
        policy = json.loads((self.repo / "_atlas/layers.json").read_text(encoding="utf-8"))
        policy["kernel"]["passkey"] = init_vault.make_record(PASSKEY)
        policy["layers"]["kernel"]["paths"].remove("AGENTS.md")
        write(self.repo / "_atlas/layers.json", json.dumps(policy, indent=2) + "\n")
        run_git(self.repo, "add", "_atlas/layers.json")
        result = run_git(self.repo, "commit", "-q", "-m", "kernel: set the passkey",
                         env={"ATLAS_TRIGGER": "KERNEL-UNLOCK", "ATLAS_PASSKEY": PASSKEY})
        self.assertNotEqual(result.returncode, 0)


class NewProjectTests(TempDirCase):
    def setUp(self):
        super().setUp()
        self.main = build_vault(self.tmp / "main", init_vault.make_record(PASSKEY))
        self.projects = self.tmp / "projects"

    def tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(self.main / "code/setup/new_project.py"), *args,
                               "--projects-root", str(self.projects)],
                              capture_output=True, text=True, env=git_env())

    def test_create_and_check(self):
        result = self.tool("create", "demo-project", "--title", "Demo Project")
        self.assertEqual(result.returncode, 0, result.stderr)
        project = self.projects / "demo-project"
        self.assertTrue((project / "AGENTS.md").is_file())
        for rel in ("code/git-hooks/pre-commit", "code/git-hooks/layer-guard.mjs", "code/setup/kernel_commit.py",
                    ".gitattributes"):
            self.assertEqual((project / rel).read_bytes(), (self.main / rel).read_bytes(), rel)
        policy = json.loads((project / "_atlas/layers.json").read_text(encoding="utf-8"))
        main_policy = json.loads((self.main / "_atlas/layers.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["kernel"]["passkey"], main_policy["kernel"]["passkey"])
        registry = json.loads((self.main / "_atlas/registry/projects.json").read_text(encoding="utf-8"))
        self.assertEqual([row["id"] for row in registry["projects"]], ["demo-project"])
        self.assertFalse(list(self.projects.glob(".*.creating")))

        result = self.tool("check", "demo-project")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("FAIL", result.stdout)
        self.assertIn("PASS  registry row", result.stdout)

    def test_check_reports_failures(self):
        self.assertEqual(self.tool("create", "demo").returncode, 0)
        write(self.projects / "demo/code/setup/kernel_commit.py", "changed\n")
        result = self.tool("check", "demo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  copy code/setup/kernel_commit.py", result.stdout)
        self.assertEqual(self.tool("check", "missing").returncode, 1)

    def test_refuses_bad_ids_and_duplicates(self):
        for bad in ("A", "Bad_Id", "-lead", "trail-", "double--hyphen", "x" * 41, "con"):
            self.assertNotEqual(self.tool("create", bad).returncode, 0, bad)
        self.assertEqual(self.tool("create", "twice").returncode, 0)
        self.assertNotEqual(self.tool("create", "twice").returncode, 0)

    @unittest.skipUnless(NODE, NO_NODE)
    def test_project_guard_is_on(self):
        self.assertEqual(self.tool("create", "guarded").returncode, 0)
        project = self.projects / "guarded"
        write(project / "README.md", (project / "README.md").read_text(encoding="utf-8") + "\nChanged.\n")
        run_git(project, "add", "README.md")
        self.assertNotEqual(run_git(project, "commit", "-q", "-m", "kernel: edit").returncode, 0)
        result = run_git(project, "commit", "-q", "-m", "kernel: edit",
                         env={"ATLAS_TRIGGER": "KERNEL-UNLOCK", "ATLAS_PASSKEY": PASSKEY})
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
