# Contributing

Thanks for looking. This is a small tool and the bar is simple: every change
keeps the suite green and the self-audit at grade A.

## Setup

```bash
git clone https://github.com/musafa21/repo-doctor
cd repo-doctor
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Before opening a pull request

```bash
pytest                                  # the suite must pass
repo-doctor . --fail-under 90           # and the repo must still grade A
```

If you add a check, add it to `CHECKS` in `src/repo_doctor/checks.py` with a
weight, and cover both the passing and failing paths in `tests/test_checks.py`.
Weights across the registry must total 100 — `tests/test_cli.py` asserts it.

## Style

- Standard library only. A dependency needs a strong justification.
- Type hints on public functions.
- Docstrings state what a check means, not how it loops.
- One behaviour per test, named after the behaviour.

## Reporting a score that feels wrong

That is the most useful bug report. Include the repository layout (or a minimal
reproduction) and which check you think is misreading it.
