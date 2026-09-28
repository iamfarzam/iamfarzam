# Production readiness verification

Verified on 2026-09-28. `example.com` already runs in production; this verification concerns an upgrade. The application builds and runs in an isolated production
Docker stack. Deployment remains conditional on the real host's secrets, DNS,
TLS proxy configuration, content, backups, and launch checks in
[deployment.md](deployment.md). No remote production host was deployed.

## Changes

- Explicit HTTPS security settings with existing proxy/redirect defaults preserved.
- Existing port-80 default preserved; configurable listener and trusted TLS proxy.
- Shared Redis contact throttles, trusted Cloudflare/client IP forwarding, Redis AOF persistence.
- Frontend readiness verifies the private Django hop; production startup waits for health.
- SSR requests use the public host; image optimization allows configured site/media origins.
- Deployment checks security before startup, tests both applications before switching,
  cleans failed candidates, and restores upstreams after failed rollout or rollback checks.
- Unversioned Django static assets use a one-hour cache instead of immutable caching.
- CI now builds and exercises production containers, audits both dependency sets,
  and runs deployment failure-control tests.

## Results

| Check | Result |
| --- | --- |
| Django configuration and migration drift | Passed; no model changes pending |
| Backend tests on Windows | 115 tests, passed; two OS-dependent skips |
| Backend tests in Python 3.12 Linux container | All 115 passed; no skips |
| Frontend Vitest | All 98 passed |
| Frontend lint, type checks and production build | Passed |
| Production Docker image builds | Backend, Celery and frontend passed |
| Production, infrastructure and blue/green Compose models | Validated |
| Deployment failure-control regressions | Six passed with mocked Docker commands |
| Private-content guard regression and tracked-file scan | Passed |
| Frontend production npm audit | No known vulnerabilities |
| Backend requirements pip-audit | No known vulnerabilities |
| Django production security check | Passed; only optional HSTS W005/W021 suppressed |
| PostgreSQL production startup and migration check | Passed (PostgreSQL 16.15) |
| Nginx template rendering and syntax | Passed |
| Existing Compose listener compatibility | Both production modes retain port 80 without new variables |
| Existing public site (read-only HEAD request) | HTTPS 200 through Cloudflare; no server changes |
| Readiness, homepage, projects, contact page, robots, sitemap and public APIs | HTTP checks passed |
| Admin login and static CSS | Passed; secure CSRF cookie confirmed |
| Public access to private demo authorization | Rejected with HTTP 404 |
| Contact persistence and anti-spoofing throttle | Five saved; sixth rejected with 429 despite changing forwarded IP headers |
| Redis cache and AOF configuration | Passed |
| Celery ping and task execution | Passed; five completed tasks with external notifications disabled |
| Standalone image runtime | Sharp loads; configured public media origin appears in compiled image patterns |

The verification stack used separate container names, networks and volumes, with
Nginx bound to `127.0.0.1:18080`. Its fictional contact messages were isolated from
real data. Test containers and volumes were removed after verification.

## Launch verification still required

- Real-domain HTTPS certificates, HTTP redirects and exact trusted proxy peer.
- SMTP delivery if contact notifications are enabled.
- Browser checks for populated content, uploaded/optimized media, mobile navigation,
  themes and RTL locales; no interactive browser was available in this session.
- Off-host backups and an isolated restore rehearsal.
- Capacity/load testing on the chosen VPS.
- Optional private demos follow their separate readiness checklist and remain disabled.

Blue/green failure handling was tested with mocks; the single-stack production
containers were exercised live. There was no live external blue/green traffic
switch. Nginx recreation can briefly interrupt requests, and code rollback cannot
undo shared database migrations or static assets. Dependency audits describe the
versions resolved during verification; future image builds can resolve newer
versions within the backend's declared ranges.
