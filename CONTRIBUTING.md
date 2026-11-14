# Contributing to OSHI

Thank you for your interest in contributing to OSHI (Open Science & Humanitarian Intelligence Infrastructure). OSHI is an open-source intelligence infrastructure that makes scientific knowledge more accessible, verifiable, and actionable for humanitarian purposes.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Security](#security)
- [License](#license)

## Code of Conduct

OSHI adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code. Please report unacceptable conduct to the project maintainers.

## How to Contribute

### Issues

1. **Search existing issues** before creating a new one.
2. Use the issue template when available.
3. Label issues appropriately (see [Issue Labels](#issue-labels)).
4. For security vulnerabilities, see [SECURITY.md](SECURITY.md) — do not open public issues for security concerns.

### Pull Requests

1. Fork the repository and create a feature branch from `main`.
2. Implement your change with tests.
3. Ensure all existing tests pass (`uv run pytest tests/`).
4. Update documentation if your change affects user-facing behavior.
5. Submit a pull request against `main`.
6. A maintainer will review your PR. Address review comments before merge.

### What to Contribute

- Bug fixes and improvements to existing connectors.
- New scientific or disaster data source connectors.
- Frontend components for the web dashboard.
- Documentation and tutorials.
- Test coverage and CI improvements.
- Translations for multilingual accessibility.

## Development Setup

### Prerequisites

- Python 3.11+
- `uv` (https://github.com/astral-sh/uv)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/nextjohnp7/OSHI.git
cd OSHI

# Create and activate virtual environment
uv sync

# Install development dependencies
uv sync --dev

# Run database migrations
uv run alembic upgrade head

# Copy environment example
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application

```bash
# Start the API server
uv run uvicorn apps.api.main:app --reload

# Or use the application factory
uv run python -c "from apps.api.main import app; print(app)"
```

### Running Tests

```bash
# All tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=apps --cov=packages

# Specific test file
uv run pytest tests/unit/test_auth.py -v
```

## Pull Request Process

1. Ensure your branch is up to date with `main`.
2. Run the full test suite and confirm all tests pass.
3. Update `docs/PROJECT_STATUS.md` if your change represents a milestone.
4. Open a PR with a descriptive title and summary.
5. Link any related issues in the PR description.
6. Request review from project maintainers.
7. Address review feedback and re-run tests.

All PRs must pass CI checks before merging.

## Coding Standards

- Follow PEP 8 for Python code.
- Use type hints in all new code.
- Write docstrings for public functions and classes.
- Keep functions small and focused on a single responsibility.
- Do not hardcode API keys, tokens, or passwords — use environment variables via `packages/core.config`.
- All new routes must be protected by `require_api_key` unless explicitly public (e.g. `/health`).
- Every SQLAlchemy model change requires an Alembic migration (`uv run alembic revision --autogenerate`).
- Unit tests must not depend on network access; use mocks/fixtures for external APIs.

## Testing

- Unit tests live in `tests/unit/`.
- Use `pytest` with `TestClient` for API tests.
- Each test function gets a fresh temporary SQLite database via `conftest.py`.
- Run `uv run pytest tests/` before committing.
- Aim for high coverage on connectors, auth, and document processing.

## Documentation

- Update `docs/PROJECT_STATUS.md` for each milestone.
- Document new API endpoints in `README.md` and relevant `docs/` files.
- Add Architecture Decision Records (ADR) in `docs/adr/` for significant decisions.
- Use the ADR format: Status, Context, Problem, Options, Decision, Consequences, Security implications, Alternatives rejected, Date.

## Security

- Read [SECURITY.md](SECURITY.md) before reporting vulnerabilities.
- Never commit secrets, API keys, or credentials.
- All dependencies are pinned via `uv.lock` — run `uv lock` after adding dependencies.
- Security-sensitive changes require careful review.

## Issue Labels

Suggested labels (blueprint Part 15.3):

- `good-first-issue` — suitable for new contributors
- `help-wanted` — maintainers need assistance
- `research-needed` — requires investigation before implementation
- `security` — security-related change
- `scientific-integrity` — affects scientific accuracy or evidence
- `humanitarian` — humanitarian intelligence functionality
- `data-source` — connector or data source integration
- `agent-engineering` — LangChain/LangGraph agent work
- `documentation` — docs-only change
- `frontend` — web UI change
- `backend` — API or backend change

## License

OSHI is licensed under the Apache-2.0 License. See [LICENSE](LICENSE) for details.

Third-party libraries and data sources retain their own licenses. Respect upstream licenses and attribution requirements.
