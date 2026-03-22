<![CDATA[# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main branch (latest) | ✅ |
| Older commits | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability in Callsum, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email the maintainers or use [GitHub Security Advisories](https://github.com/sapirl7/Callsum/security/advisories/new) to report the issue privately.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

### Response timeline

- **Acknowledgment:** within 48 hours
- **Initial assessment:** within 7 days
- **Fix or mitigation:** best effort, typically within 30 days

## Security Model

Callsum processes audio data through a serverless pipeline. Key security controls:

- **Secrets management:** AWS Secrets Manager for all tokens and keys
- **Encryption at rest:** S3 AES-256 server-side encryption
- **Encryption in transit:** HTTPS for all external communication
- **Webhook validation:** `TELEGRAM_SECRET_TOKEN` and `RUNPOD_CALLBACK_TOKEN`
- **User isolation:** S3 paths scoped by `user_id`
- **Least privilege:** IAM roles with minimal required permissions
- **Data retention:** S3 lifecycle policy auto-deletes objects after 30 days

For detailed architecture, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Dependency Security

- Dependencies are monitored via [Dependabot](.github/dependabot.yml)
- CI runs security checks on every pull request
]]>
