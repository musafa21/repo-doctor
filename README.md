# repo-doctor

[![ci](https://github.com/musafa21/repo-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/musafa21/repo-doctor/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

**Score any repository the way a reviewer does — before someone else does.**

One command. Ten checks. A number out of 100, and the specific fixes that move it.

```console
$ repo-doctor musafa21/simple_shell
Score 10/100 (F) - 9 failing, 1 partial
```

## Why this exists

A repository is read in seconds, then judged. Does it look maintained? Can I install it? Is there evidence the author tests their work? Those questions have mechanical answers — and almost nobody checks their own repo against them.

`repo-doctor` turns that checklist into executable rules, so it can run in CI instead of living in a reviewer's head. It was written to grade my own portfolio, and the first score was uncomfortable.

## Install

Requires Python 3.10+. No runtime dependencies — the standard library only.

```bash
pipx install git+https://github.com/musafa21/repo-doctor
```

Or from a checkout:

```bash
git clone https://github.com/musafa21/repo-doctor
cd repo-doctor
pip install .
```

## Usage

```bash
repo-doctor .                                      # score the current directory
repo-doctor musafa21/simple_shell                  # score a GitHub repo by slug
repo-doctor https://github.com/psf/requests        # or by URL (shallow clone)
repo-doctor . --json                               # machine-readable
repo-doctor . --fail-under 90                      # exit 1 when below 90, for CI
repo-doctor . --verbose                            # every suggested fix, not just the top four
```

Remote targets are shallow-cloned into a temporary directory and removed afterwards. Local audits never touch the network.

## Sample output

```console
$ repo-doctor .
repo-doctor 0.1.0 - /home/dev/repo-doctor

  PASS  README        20/20  README.md: 5239 chars, 11 sections, code samples
  PASS  CI            15/15  1 workflow(s) with run steps
  PASS  Tests         15/15  2 file(s) under tests/
  PASS  License       10/10  LICENSE present
  PASS  Gitignore     10/10  covers 7 common patterns
  PASS  Dependencies  10/10  pyproject.toml
  FAIL  Lockfile        0/5  no lockfile
  PASS  Security        5/5  SECURITY.md
  PASS  Docs            5/5  CONTRIBUTING.md
  PASS  Activity        5/5  last commit 0 days ago

Score 95/100 (A) - 1 failing

Fix next:
  1. Lockfile: Commit a lockfile so installs are reproducible.
```

## What it checks

| Check | Weight | Passing means |
|---|---:|---|
| README | 20 | 400+ characters, at least two sections, at least one code block |
| CI | 15 | a workflow with a trigger **and** real run steps |
| Tests | 15 | discoverable test files under `tests/` or `test_*.py` |
| License | 10 | `LICENSE`, or a declared license in the manifest |
| Gitignore | 10 | covers at least two common artifact patterns |
| Dependencies | 10 | a manifest (`pyproject.toml`, `package.json`, …) |
| Lockfile | 5 | a committed lockfile, partial credit for pinned requirements, or nothing to lock |
| Security | 5 | `SECURITY.md` or `.github/dependabot.yml` |
| Docs | 5 | `CONTRIBUTING.md`, `CHANGELOG.md`, or `docs/` |
| Activity | 5 | a commit within the last 180 days |

Scoring is weighted: **pass** earns the full weight, **partial** earns half, **fail** earns nothing. Grades: **A** ≥ 90, **B** ≥ 80, **C** ≥ 70, **D** ≥ 60, otherwise **F**.

Partial credit matters. A short README that still explains install is worth half the points, not zero — the tool should encourage incremental improvement rather than demand a rewrite.

## Gate a repository in CI

```yaml
- uses: actions/checkout@v4
- run: pip install git+https://github.com/musafa21/repo-doctor
- run: repo-doctor . --fail-under 90
```

This project runs that exact step against itself — see [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | audit completed and the score met `--fail-under` |
| 1 | audit completed but the score fell short |
| 2 | the target could not be read (missing path, failed clone) |

## Development

```bash
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

The suite is written with `unittest`, so it also runs on a bare interpreter with nothing installed — `PYTHONPATH=src python -m unittest discover -s tests`. CI runs it through `pytest`, which collects the same cases.

The checks are pure functions from a `Path` to a result, so each one is tested against a temporary directory rather than mocked filesystem calls. To see the whole suite run on this repository:

```bash
python -m repo_doctor .
```

## Design notes

- **Standard library only.** A tool that judges projects should install in one step and never break because a dependency moved.
- **Partial credit over binaries.** Most real repositories are halfway to good; the score should reflect that.
- **No network for local audits.** Scoring a checkout is pure filesystem work, so it is fast and reproducible.
- **Hints are actionable.** Every failing check returns the specific change that fixes it, not a description of the problem.

## License

MIT — see [LICENSE](LICENSE).
