"""The checks repo-doctor runs, and the weighted registry that orders them."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .model import Status

CheckFn = Callable[[Path], "tuple[Status, str, str]"]

_READMES = ("readme.md", "readme.rst", "readme.txt", "readme")
_LICENSES = ("license", "license.md", "license.txt", "licence", "copying")
_LOCKFILES = (
    "uv.lock",
    "poetry.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "cargo.lock",
    "go.sum",
    "gemfile.lock",
    "composer.lock",
)
_IGNORE_PATTERNS = (
    "__pycache__",
    "node_modules",
    "venv",
    "dist/",
    "build/",
    ".env",
    ".pytest_cache",
    "coverage",
)
_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".tox",
}


@dataclass(frozen=True)
class Check:
    """A named, weighted inspection applied to a repository root."""

    name: str
    weight: int
    run: CheckFn


def _first(root: Path, names: tuple[str, ...]) -> Path | None:
    """Return the first existing file from ``names``, case-insensitively."""
    if not root.is_dir():
        return None
    present = {entry.name.lower(): entry for entry in root.iterdir() if entry.is_file()}
    for name in names:
        if name in present:
            return present[name]
    return None


def _text(path: Path) -> str:
    """Read a file as text, tolerating encoding problems and IO errors."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _skipped(path: Path, root: Path) -> bool:
    """True when ``path`` sits inside a directory we never traverse."""
    return any(part in _SKIP_DIRS for part in path.relative_to(root).parts)


def check_readme(root: Path) -> tuple[Status, str, str]:
    """A README must explain the project, be structured, and show usage."""
    path = _first(root, _READMES)
    if path is None:
        return Status.FAIL, "no README", "Add README.md: what it does, install, usage, example output."
    text = _text(path)
    headings = len(re.findall(r"(?m)^#{1,6}\s+\S", text))
    fences = text.count("```")
    if len(text) < 400:
        return Status.PARTIAL, f"{path.name} is thin ({len(text)} chars)", "Expand it: problem, install, quickstart, example output."
    if headings < 2:
        return Status.PARTIAL, f"{path.name} has no sections", "Break it into headed sections such as Install and Usage."
    if fences < 2:
        return Status.PARTIAL, f"{path.name} shows no code", "Add a runnable snippet or a terminal session."
    return Status.PASS, f"{path.name}: {len(text)} chars, {headings} sections, code samples", ""


def check_license(root: Path) -> tuple[Status, str, str]:
    """A license file, or a declared license in the package manifest."""
    path = _first(root, _LICENSES)
    if path is not None:
        return Status.PASS, f"{path.name} present", ""
    manifest = root / "pyproject.toml"
    if manifest.is_file() and re.search(r"(?m)^\s*license\s*=", _text(manifest)):
        return Status.PASS, "declared in pyproject.toml", ""
    package_json = root / "package.json"
    if package_json.is_file() and re.search(r'"license"\s*:\s*"(?!UNLICENSED)', _text(package_json)):
        return Status.PASS, "declared in package.json", ""
    return Status.FAIL, "no license", "Add LICENSE (MIT is fine) so others may legally use the code."


def check_ci(root: Path) -> tuple[Status, str, str]:
    """At least one GitHub Actions workflow that actually runs something."""
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return Status.FAIL, "no workflows", "Add .github/workflows/ci.yml that runs tests on push."
    files = [p for p in workflows.iterdir() if p.suffix in {".yml", ".yaml"}]
    if not files:
        return Status.FAIL, "workflows dir is empty", "Add a CI workflow that installs and runs the test suite."
    body = "\n".join(_text(p) for p in files)
    triggers = bool(re.search(r"(?m)^\s*on\s*:", body))
    steps = "run:" in body
    if triggers and steps:
        return Status.PASS, f"{len(files)} workflow(s) with run steps", ""
    if steps:
        return Status.PARTIAL, "workflow has steps but no clear trigger", "Declare an on: block for push and pull_request."
    return Status.FAIL, "workflow does nothing", "Add steps that install dependencies and run tests."


def check_tests(root: Path) -> tuple[Status, str, str]:
    """Discoverable automated tests."""
    test_dir = root / "tests"
    if test_dir.is_dir():
        files = [p for p in test_dir.rglob("*.py") if p.is_file()]
        if any(p.name.startswith("test_") or p.name.endswith("_test.py") for p in files):
            return Status.PASS, f"{len(files)} file(s) under tests/", ""
        return Status.PARTIAL, "tests/ exists but holds no test files", "Add tests/test_<module>.py with real assertions."
    scattered = [
        p
        for p in root.rglob("test_*.py")
        if p.is_file() and not _skipped(p, root)
    ]
    if scattered:
        return Status.PASS, f"{len(scattered)} test file(s) found", ""
    return Status.FAIL, "no tests found", "Add a tests/ directory with at least one test per module."


def check_dependencies(root: Path) -> tuple[Status, str, str]:
    """A machine-readable dependency manifest."""
    for name in ("pyproject.toml", "package.json", "requirements.txt", "Cargo.toml", "go.mod", "Gemfile"):
        if (root / name).is_file():
            return Status.PASS, name, ""
    return Status.FAIL, "no dependency manifest", "Declare dependencies in pyproject.toml or package.json."


def check_lockfile(root: Path) -> tuple[Status, str, str]:
    """A committed lockfile, or at least pinned requirements."""
    present = (
        {entry.name.lower(): entry.name for entry in root.iterdir() if entry.is_file()}
        if root.is_dir()
        else {}
    )
    for locked in _LOCKFILES:
        if locked in present:
            return Status.PASS, present[locked], ""
    pinned = [
        p
        for p in root.glob("requirements*.txt")
        if p.is_file() and re.search(r"(?m)^[A-Za-z0-9_.-]+==", _text(p))
    ]
    if pinned:
        return Status.PARTIAL, f"{pinned[0].name} pins versions", "Commit a real lockfile (uv.lock, poetry.lock) for exact reproduction."
    return Status.FAIL, "no lockfile", "Commit a lockfile so installs are reproducible."


def check_gitignore(root: Path) -> tuple[Status, str, str]:
    """Keep build artifacts and secrets out of version control."""
    path = root / ".gitignore"
    if not path.is_file():
        return Status.FAIL, "no .gitignore", "Add .gitignore covering virtualenvs, caches, and .env files."
    text = _text(path).lower()
    covered = [pattern for pattern in _IGNORE_PATTERNS if pattern in text]
    if len(covered) >= 2:
        return Status.PASS, f"covers {len(covered)} common patterns", ""
    return Status.PARTIAL, "few common patterns covered", "Add .venv/, __pycache__/, .env, dist/, build/ to .gitignore."


def check_security(root: Path) -> tuple[Status, str, str]:
    """A disclosure policy or automated dependency updates."""
    if (root / "SECURITY.md").is_file():
        return Status.PASS, "SECURITY.md", ""
    if (root / ".github" / "dependabot.yml").is_file():
        return Status.PASS, "dependabot configured", ""
    return Status.FAIL, "no security policy", "Add SECURITY.md or .github/dependabot.yml."


def check_docs(root: Path) -> tuple[Status, str, str]:
    """Contributor-facing or release-facing documentation."""
    for name in ("CONTRIBUTING.md", "CHANGELOG.md", "CODE_OF_CONDUCT.md"):
        if (root / name).is_file():
            return Status.PASS, name, ""
    if (root / "docs").is_dir():
        return Status.PASS, "docs/", ""
    return Status.FAIL, "no supporting docs", "Add CHANGELOG.md or CONTRIBUTING.md."


def check_activity(root: Path) -> tuple[Status, str, str]:
    """Recent commits, which employers read as active maintenance."""
    if not (root / ".git").exists():
        return Status.PARTIAL, "not a git checkout", "Initialize git and commit the work."
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        stamp = int(completed.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return Status.PARTIAL, "git history unreadable", "Ensure the checkout has at least one commit."
    if stamp == 0:
        return Status.PARTIAL, "no commits yet", "Commit the initial version."
    age = (time.time() - stamp) / 86400
    if age <= 180:
        return Status.PASS, f"last commit {age:.0f} days ago", ""
    if age <= 365:
        return Status.PARTIAL, f"last commit {age:.0f} days ago", "Refresh the repo or archive it deliberately."
    return Status.FAIL, f"dormant ({age:.0f} days)", "Push a current version or archive the repository."


CHECKS: tuple[Check, ...] = (
    Check("README", 20, check_readme),
    Check("CI", 15, check_ci),
    Check("Tests", 15, check_tests),
    Check("License", 10, check_license),
    Check("Gitignore", 10, check_gitignore),
    Check("Dependencies", 10, check_dependencies),
    Check("Lockfile", 5, check_lockfile),
    Check("Security", 5, check_security),
    Check("Docs", 5, check_docs),
    Check("Activity", 5, check_activity),
)
