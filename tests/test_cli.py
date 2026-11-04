"""Tests for scoring, rendering, and the command-line contract."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from repo_doctor.checks import CHECKS
from repo_doctor.cli import analyze, main, render_text
from repo_doctor.model import Report, Result, Status


def write(path: Path, text: str) -> None:
    """Create ``path`` and any missing parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def complete_repo(root: Path) -> Path:
    """Write a repository that passes every check except git history."""
    write(
        root / "README.md",
        "# demo\n\nA project with enough content to satisfy the checks.\n\n"
        "## Install\n\n```bash\npip install demo\n```\n\n"
        "## Usage\n\n```python\nimport demo\n```\n\n"
        + ("Substance for the readme. " * 12),
    )
    write(root / "LICENSE", "MIT\n")
    write(root / ".gitignore", ".venv/\n__pycache__/\n.env\ndist/\n")
    write(root / "pyproject.toml", '[project]\nname = "demo"\n')
    write(root / "uv.lock", "version = 1\n")
    write(root / "SECURITY.md", "# Security\n")
    write(root / "CHANGELOG.md", "# Changelog\n")
    write(root / "tests" / "test_demo.py", "def test_ok():\n    assert True\n")
    write(root / ".github" / "workflows" / "ci.yml", "on: [push]\nsteps:\n  - run: pytest\n")
    return root


def run_main(argv: list[str]) -> tuple[int, str, str]:
    """Call the CLI and capture its exit code, stdout, and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class ReportTests(unittest.TestCase):
    """Scoring, grading, and rendering."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_analyze_covers_every_registered_check(self) -> None:
        report = analyze(complete_repo(self.root))
        self.assertEqual([result.name for result in report.results], [check.name for check in CHECKS])
        self.assertEqual(sum(result.weight for result in report.results), 100)

    def test_complete_repo_scores_high(self) -> None:
        report = analyze(complete_repo(self.root))
        self.assertGreaterEqual(report.score, 90)
        self.assertEqual(report.grade, "A")

    def test_empty_repo_scores_low(self) -> None:
        report = analyze(self.root)
        self.assertLessEqual(report.score, 10)
        self.assertEqual(report.grade, "F")
        self.assertTrue(report.fixes)

    def test_grade_boundaries(self) -> None:
        cases = {100: "A", 90: "A", 89: "B", 80: "B", 79: "C", 70: "C", 69: "D", 60: "D", 59: "F"}
        for points, grade in cases.items():
            report = Report(root=Path("."))
            report.results = [Result("x", points, Status.PASS, "")]
            with self.subTest(points=points):
                self.assertEqual(report.grade, grade)
                self.assertEqual(report.score, points)

    def test_partial_credit_is_half_weight(self) -> None:
        self.assertEqual(Result("README", 20, Status.PARTIAL, "").earned, 10)

    def test_render_text_mentions_score_and_fixes(self) -> None:
        text = render_text(analyze(self.root))
        self.assertIn("Score ", text)
        self.assertIn("Fix next:", text)
        self.assertIn("/100", text)


class CliTests(unittest.TestCase):
    """The process-facing contract: exit codes and output formats."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_json_output_is_valid(self) -> None:
        complete_repo(self.root)
        code, out, _ = run_main([str(self.root), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["grade"], "A")
        self.assertEqual(len(payload["checks"]), len(CHECKS))

    def test_fail_under_controls_exit_code(self) -> None:
        code, _, _ = run_main([str(self.root), "--fail-under", "100"])
        self.assertEqual(code, 1)

    def test_fail_under_passes_when_met(self) -> None:
        complete_repo(self.root)
        code, _, _ = run_main([str(self.root), "--fail-under", "90"])
        self.assertEqual(code, 0)

    def test_missing_target_exits_two(self) -> None:
        code, _, err = run_main(["definitely-not-a-directory-xyz"])
        self.assertEqual(code, 2)
        self.assertIn("repo-doctor", err)


if __name__ == "__main__":
    unittest.main()
