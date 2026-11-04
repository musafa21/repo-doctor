# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-04

### Added

- Ten weighted checks: README, CI, tests, license, `.gitignore`, dependencies,
  lockfile, security policy, supporting docs, and recent activity.
- Weighted scoring with partial credit plus letter grades, rendered as a
  terminal table or as JSON.
- `--fail-under` for CI gating, with distinct exit codes for a failed audit and
  an unreadable target.
- Remote targets by URL or `owner/repo` slug, shallow-cloned into a temporary
  directory and removed afterwards.

[Unreleased]: https://github.com/musafa21/repo-doctor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/musafa21/repo-doctor/releases/tag/v0.1.0
