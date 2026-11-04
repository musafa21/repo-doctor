"""Allow ``python -m repo_doctor``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
