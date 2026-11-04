# Security policy

## Supported versions

`repo-doctor` is pre-1.0. Only the latest release on `main` receives fixes.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Email the maintainer
at bsammy158@gmail.com with a description and, if possible, a minimal
reproduction. You can expect an acknowledgement within a few days.

`repo-doctor` reads local files and, for remote targets, performs a shallow
`git clone` into a temporary directory. It executes no code from the audited
repository, so the main risks are path-traversal style bugs in path handling
and unexpected network access. Reports about either are welcome.
