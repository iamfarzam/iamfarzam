# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do not open a public issue.** Instead, send an email to the repository owner with details of the vulnerability.

Include the following in your report:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You can expect an initial response within 48 hours.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Security Practices

- All secrets are managed via environment variables (`.env` files, never committed)
- API contact endpoint is rate-limited
- CORS is restricted to configured origins
- Django security middleware is enabled (CSRF, XSS, clickjacking protection)
- Production uses HTTPS via reverse proxy
