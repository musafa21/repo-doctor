"""Command-line interface for repo-doctor."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from . import __version__
from .checks import CHECKS
from .model import Report, Result, Status

_SLUG = re.compile(r"^(?:gh:)?(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)$")
_MARKS = {Status.PASS: "PASS", Status.PARTIAL: "PART", Status.FAIL: "FAIL"}


def analyze(root: Path) -> Report:
    """Run every registered check against ``root`` and collect the results."""
    report = Report(root=root)
    for check in CHECKS:
        status, detail, hint = check.run(root)
        report.results.append(
            Result(name=check.name, weight=check.weight, status=status, detail=detail, hint=hint)
        )
    return report


def _git_clone(url: str, destination: Path) -> None:
    """Shallow-clone ``url``; retries with git's OpenSSL backend on Windows.

    The retry exists because some Windows installs hand HTTPS work to schannel,
    which fails with SEC_E_NO_CREDENTIALS in restricted environments.
    """
    base = ["git", "clone", "--depth", "1", "--quiet", url, str(destination)]
    attempt = subprocess.run(base, capture_output=True, text=True, check=False)
    if attempt.returncode == 0:
        return
    if sys.platform == "win32":
        retry = subprocess.run(
            [*base[:1], "-c", "http.sslBackend=openssl", *base[1:]],
            capture_output=True,
            text=True,
            check=False,
        )
        if retry.returncode == 0:
            return
        attempt = retry
    detail = (attempt.stderr or attempt.stdout or "git clone failed").strip().splitlines()
    raise RuntimeError(detail[-1] if detail else "git clone failed")


@contextmanager
def _resolve(target: str) -> Iterator[Path]:
    """Yield a local repository root for a path, URL, or ``owner/repo`` slug."""
    candidate = Path(target).expanduser()
    if candidate.is_dir():
        yield candidate.resolve()
        return

    match = _SLUG.match(target)
    if target.startswith(("http://", "https://", "git@")) or match:
        url = target
        if match:
            url = f"https://github.com/{match.group('owner')}/{match.group('repo')}.git"
        with tempfile.TemporaryDirectory(prefix="repo-doctor-") as workspace:
            destination = Path(workspace) / "repo"
            _git_clone(url, destination)
            yield destination
        return

    raise FileNotFoundError(f"not a directory and not a cloneable target: {target}")


def render_text(report: Report, verbose: bool = False) -> str:
    """Human-readable report: one line per check, then the score and fixes."""
    lines = [f"repo-doctor {__version__} - {report.root}", ""]
    width = max(len(result.name) for result in report.results) if report.results else 0
    for result in report.results:
        mark = _MARKS[result.status]
        points = f"{result.earned:g}/{result.weight:g}"
        lines.append(f"  {mark}  {result.name.ljust(width)}  {points:>5}  {result.detail}")
    lines.append("")
    failing = [r for r in report.results if r.status is Status.FAIL]
    partial = [r for r in report.results if r.status is Status.PARTIAL]
    summary = f"Score {report.score}/100 ({report.grade})"
    if failing or partial:
        counts = []
        if failing:
            counts.append(f"{len(failing)} failing")
        if partial:
            counts.append(f"{len(partial)} partial")
        summary += " - " + ", ".join(counts)
    lines.append(summary)

    fixes = report.fixes
    if fixes:
        lines.append("")
        lines.append("Fix next:")
        for index, result in enumerate(fixes[:4] if not verbose else fixes, start=1):
            lines.append(f"  {index}. {result.name}: {result.hint or result.detail}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="repo-doctor",
        description="Score a repository on the things employers and reviewers check first.",
    )
    parser.add_argument("target", help="local path, https URL, or GitHub owner/repo")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--fail-under",
        type=int,
        default=0,
        metavar="N",
        help="exit non-zero when the score is below N (default: 0)",
    )
    parser.add_argument("--verbose", action="store_true", help="list every suggested fix")
    parser.add_argument("--version", action="version", version=f"repo-doctor {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        with _resolve(args.target) as root:
            report = analyze(root)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"repo-doctor: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_text(report, verbose=args.verbose))

    return 1 if report.score < args.fail_under else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
