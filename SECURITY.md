# Security Policy

## Supported Versions

OSHI is an early-stage open-source project. Security support is provided
for the latest release on the `main` branch only.

| Version | Supported |
|---------|-----------|
| main    | ✅        |

## Reporting a Vulnerability

OSHI operates in scientific and humanitarian contexts. Security is critical.

Please **do not** open public GitHub issues for security vulnerabilities.

Instead, report security concerns privately to the project maintainers:

- Email: security@oshi.example (replace with actual contact)
- Include: description of the vulnerability, steps to reproduce, affected
  components, and potential impact.

We will acknowledge receipt within 5 business days and provide an initial
assessment within 10 business days.

## Security Considerations for Contributors

- Never commit API keys, tokens, passwords, or other secrets.
- Use environment variables via `packages/core.config` for all credentials.
- All API routes (except `/health`) require API key authentication.
- Retrieved external content is treated as untrusted data (see Part 8.2 of the blueprint).
- No arbitrary code execution from retrieved documents.
- No autonomous disaster warnings or evacuation instructions (see Part 3.5 mandatory restrictions).

## Dependency Security

- Dependencies are managed with `uv` and pinned in `uv.lock`.
- Run `uv lock` after adding or updating dependencies.
- Maintainers review dependency updates for known vulnerabilities.

## Disclosure

We follow coordinated vulnerability disclosure. We will not publicly disclose
a security issue until a fix is available or a reasonable remediation period
has passed.

## License

OSHI is licensed under Apache-2.0. See [LICENSE](LICENSE).
