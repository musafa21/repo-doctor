"""Behavioural tests for the individual checks.

Written with ``unittest`` so the suite runs on a bare interpreter:

    python -m unittest discover -s tests

``pytest`` collects the same cases in CI.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_doctor.checks import (
    check_activity,
    check_ci,
    check_dependencies,
    check_docs,
    check_gitignore,
    check_license,
    check_lockfile,
    check_readme,
    check_security,
    check_tests,
)
from repo_doctor.model import Status

FULL_README = (
    "# demo\n\n"
    "A tiny project that exists so the checks have something honest to read.\n\n"
    "## Install\n\n```bash\npip install demo\n```\n\n"
    "## Usage\n\n```python\nimport demo\n\ndemo.run()\n```\n\n"
    "## Why\n\n"
    + ("It demonstrates a readable README with enough substance to pass. " * 6)
)


def write(path: Path, text: str) -> None:
    """Create ``path`` and any missing parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CheckTests(unittest.TestCase):
    """Each check is exercised against a temporary directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_readme_missing_is_fail(self) -> None:
        status, _, hint = check_readme(self.root)
        self.assertIs(status, Status.FAIL)
        self.assertIn("README", hint)

    def test_readme_thin_is_partial(self) -> None:
        write(self.root / "README.md", "# demo\n\nshort.\n")
        status, _, hint = check_readme(self.root)
        self.assertIs(status, Status.PARTIAL)
        self.assertTrue(hint)

    def test_readme_complete_passes(self) -> None:
        write(self.root / "README.md", FULL_README)
        status, detail, _ = check_readme(self.root)
        self.assertIs(status, Status.PASS)
        self.assertIn("sections", detail)

    def test_ci_requires_a_trigger_and_steps(self) -> None:
        workflow = self.root / ".github" / "workflows" / "ci.yml"
        write(workflow, "jobs:\n  test:\n    steps:\n      - run: pytest\n")
        self.assertIs(check_ci(self.root)[0], Status.PARTIAL)
        write(workflow, "on: [push]\njobs:\n  test:\n    steps:\n      - run: pytest\n")
        self.assertIs(check_ci(self.root)[0], Status.PASS)

    def test_ci_missing_is_fail(self) -> None:
        self.assertIs(check_ci(self.root)[0], Status.FAIL)

    def test_tests_directory_is_discovered(self) -> None:
        write(self.root / "tests" / "test_one.py", "def test_a():\n    assert 1\n")
        status, detail, _ = check_tests(self.root)
        self.assertIs(status, Status.PASS)
        self.assertIn("tests", detail)

    def test_empty_tests_directory_is_partial(self) -> None:
        (self.root / "tests").mkdir()
        self.assertIs(check_tests(self.root)[0], Status.PARTIAL)

    def test_license_accepts_file_or_manifest(self) -> None:
        self.assertIs(check_license(self.root)[0], Status.FAIL)
        write(self.root / "pyproject.toml", '[project]\nlicense = { text = "MIT" }\n')
        self.assertIs(check_license(self.root)[0], Status.PASS)
        write(self.root / "LICENSE", "MIT\n")
        self.assertIs(check_license(self.root)[0], Status.PASS)

    def test_dependencies_and_lockfile(self) -> None:
        self.assertIs(check_dependencies(self.root)[0], Status.FAIL)
        self.assertIs(check_lockfile(self.root)[0], Status.FAIL)
        write(self.root / "requirements.txt", "requests==2.32.0\n")
        self.assertIs(check_dependencies(self.root)[0], Status.PASS)
        self.assertIs(check_lockfile(self.root)[0], Status.PARTIAL)
        write(self.root / "poetry.lock", "")
        self.assertIs(check_lockfile(self.root)[0], Status.PASS)

    def test_lockfile_is_found_regardless_of_case(self) -> None:
        write(self.root / "Cargo.lock", "")
        status, detail, _ = check_lockfile(self.root)
        self.assertIs(status, Status.PASS)
        self.assertEqual(detail, "Cargo.lock")

    def test_gitignore_needs_common_patterns(self) -> None:
        self.assertIs(check_gitignore(self.root)[0], Status.FAIL)
        write(self.root / ".gitignore", ".venv/\n")
        self.assertIs(check_gitignore(self.root)[0], Status.PARTIAL)
        write(self.root / ".gitignore", ".venv/\n__pycache__/\n.env\n")
        self.assertIs(check_gitignore(self.root)[0], Status.PASS)

    def test_security_and_docs(self) -> None:
        self.assertIs(check_security(self.root)[0], Status.FAIL)
        self.assertIs(check_docs(self.root)[0], Status.FAIL)
        write(self.root / "SECURITY.md", "report privately\n")
        write(self.root / "CHANGELOG.md", "## 0.1.0\n")
        self.assertIs(check_security(self.root)[0], Status.PASS)
        self.assertIs(check_docs(self.root)[0], Status.PASS)

    def test_activity_without_git_is_partial(self) -> None:
        status, _, hint = check_activity(self.root)
        self.assertIs(status, Status.PARTIAL)
        self.assertIn("git", hint)


if __name__ == "__main__":
    unittest.main()
