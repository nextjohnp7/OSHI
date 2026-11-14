# OSHI Governance

## Overview

OSHI (Open Science & Humanitarian Intelligence Infrastructure) is an open-source
intelligence infrastructure governed by its maintainers and contributors.
This document describes the governance model, decision-making process, and
roles within the project.

## Mission

Make scientific knowledge more accessible, verifiable, actionable, and useful
for solving humanity's most important problems, particularly in humanitarian
contexts.

## Roles

### Maintainers

Maintainers have write access to the repository and are responsible for:

- Reviewing and merging pull requests.
- Triaging issues and assigning labels.
- Releasing new versions.
- Enforcing the Code of Conduct.
- Making final decisions when consensus cannot be reached.

### Contributors

Contributors are anyone who submits code, documentation, tests, or other
improvements to the project. Contributors are encouraged to:

- Follow the Contributing guidelines.
- Participate in discussions respectfully.
- Help review other contributors' pull requests.

### Users

Users are anyone who deploys, runs, or integrates with OSHI. User feedback
is valued and helps shape the project roadmap.

## Decision-Making

### Consensus-Based

Most decisions (feature additions, bug fixes, documentation changes) are made
by consensus among maintainers and active contributors through pull request
reviews and issue discussions.

### Maintainer Final Say

When consensus cannot be reached, the lead maintainer makes the final decision.
Decisions are documented in Architecture Decision Records (ADR) under
`docs/adr/`.

### Major Changes

Major architectural changes (new database models, new agent workflows,
breaking API changes, license changes) require:

- A written proposal (ADR format).
- Review by at least two maintainers.
- Community discussion period (minimum 7 days for non-urgent changes).

## Release Process

1. Changes are merged into `main` via pull requests.
2. Maintainers create a release tag (semantic versioning, e.g. `v0.1.0`).
3. Release notes document new features, bug fixes, and breaking changes.
4. Docker images are built and pushed for tagged releases.

## Communication

- Issues and pull requests: GitHub repository
- Discussions: GitHub Discussions (when enabled)
- Security reports: private channel (see SECURITY.md)

## Changes to This Document

Changes to this governance document require:

- A pull request against `main`.
- Review and approval by at least two maintainers.
- Community discussion period.

## License

OSHI is licensed under Apache-2.0. See [LICENSE](LICENSE).
