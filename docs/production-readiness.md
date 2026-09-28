# Production readiness verification

Re-verified on 2026-09-28 against the code, in an isolated local stack. `example.com`
already runs in production, so this covers an upgrade. Deployment remains conditional
on the real host's secrets, DNS, TLS proxy configuration, content, backups, and the
launch checks in [deployment.md](deployment.md). No remote production host was deployed.

## Changes in this release

- Explicit HTTPS security settings, with existing proxy/redirect defaults preserved.
- Existing port-80 default preserved; configurable listener and trusted TLS proxy.
- Shared Redis contact throttles, trusted Cloudflare/client IP forwarding, Redis AOF.
- Frontend readiness verifies the private Django hop; startup waits for health.
- Image optimization allows the configured site and media origins.
- Deployment checks security before startup, cleans up failed candidates, and restores
  upstreams after a failed rollout or rollback.
- Unversioned Django static assets use a one-hour cache instead of immutable caching.
- CI builds and exercises production containers and audits both dependency sets.

## Defects found by running the release, and fixed

Each of these was reproduced first, then fixed, then re-verified end to end.

- **Blue/green deployment could not start.** Node's `fetch()` silently discards a
  `Host` header, so the frontend readiness route reached Django as the colour's
  internal container name (`portfolio-blue-backend`), which is not in
  `ALLOWED_HOSTS`. The frontend never became healthy and every deploy aborted;
  server-side rendering would have failed the same way. The public host now travels
  as `X-Forwarded-Host` with `USE_X_FORWARDED_HOST` enabled, and Nginx overwrites
  that header on every public path so a visitor cannot choose it.
- **`.env.example` shipped a self-contradicting pair.** `SECURE_SSL_REDIRECT=True`
  with `NGINX_PROXY_SCHEME=auto` makes Django 301 every API, admin and health
  request. The example now sets `https`, and `deploy.sh` refuses to deploy when the
  two disagree rather than discovering it after the flip.
- **The public smoke test could pass against the old live site.** BusyBox `wget`
  follows redirects and has no `--max-redirect`, so a 301 sent it to the real public
  domain. It now matches the first status line, and any redirect fails the check.
- **A broker URL without a database number broke the throttle cache.** Deriving the
  cache location by string split turned `redis://redis:6379` into `redis://1`. It is
  now derived from URL parts, and only when the broker is actually Redis.
- **A dirty checkout stamped a non-SemVer version** (`0.21.0.dirty`), which the
  image's own version test rejects. The marker is now build metadata (`+dirty`).
- **`pip` was pinned after it had already installed the requirements.** The pin now
  precedes installation, so the pinned resolver installs the application.

## Deployment checks that did not cover what the release now depends on

- **Readiness ignored Redis.** This release made the cache load-bearing for contact
  throttling, but `/healthz/` only tested the database, so a broken cache URL would
  deploy successfully and fail on the first contact submission. Readiness now
  verifies a cache round trip and reports each dependency; with Redis stopped it
  returns `503 {"ready": false, "database": true, "cache": false}`, and the public
  smoke script fails with it.
- **Celery was never validated by either deployment path.** Neither Compose file
  gave the worker a healthcheck, so a worker that could not reach the broker still
  counted as a successful deploy. Both now health-check the worker with
  `celery -A config inspect ping`, so `--wait` gates on it.
- **The deploy pre-flight did not validate configuration.** A missing `.env` value
  or an invalid Compose model was only discovered after a full image build. Both
  are now checked before anything is built.
- **The public smoke test covered less than the standalone smoke script.** It now
  also checks the API and asserts the private demo gate answers 404 at the public
  origin, so a flip cannot succeed while that boundary is open.
- **The privacy guard rejected the repository's own commit identity.** A
  `users.noreply.github.com` address exists to keep a real address private, so it
  is now recognised as non-disclosing. The local denylist governs published content
  and is no longer applied to the public commit identity; generic rules still are.

## Results

Verified by running each check, not from prior records.

| Check | Result |
| --- | --- |
| Frontend Vitest | 98 passed |
| Frontend lint | No ESLint warnings or errors |
| Frontend production build | Passed |
| Production image builds (backend, celery, frontend) | Passed |
| Production and infrastructure Compose models | Validated |
| Backend tests in the deployed container | 119 passed |
| Django production security check (`--fail-level WARNING`) | Passed; only optional HSTS W005/W021 silenced |
| Migration drift and `migrate --check` | No model changes pending |
| Nginx configuration syntax | Passed |
| Deployment failure-control regressions | 12 passed with mocked Docker commands |
| Private-content guard regression and tracked-file scan | Passed; no tracked file matches |
| Blue/green `fresh`, `deploy` flip and `rollback` | All completed live against real containers |
| Public smoke suite through Nginx | 12 endpoint checks passed |
| Readiness, homepage, projects, contact, robots, sitemap, public APIs | Passed |
| Admin login and static CSS | Passed; secure CSRF cookie confirmed |
| Public access to the private demo gate | Rejected with HTTP 404 |
| Contact throttle under changing forwarded IP headers | Five saved, sixth rejected with 429 |
| `X-Forwarded-Host` spoofing through the public origin | Overwritten by Nginx; direct spoofing rejected with 400 |
| Celery worker healthcheck | Healthy in both single-stack and blue/green |
| Readiness with Redis stopped | 503 with `cache: false`; smoke script fails with it |
| Frontend production `npm audit` | 0 vulnerabilities |
| Backend `pip-audit` of requirements | No known vulnerabilities |

Verification used separate container names, networks and volumes, with Nginx bound to
`127.0.0.1:18080`, and fictional contact messages isolated from real data. Test
containers and volumes were removed afterwards.

## Launch verification still required

- Real-domain HTTPS certificates, HTTP redirects and the exact trusted proxy peer.
- SMTP delivery if contact notifications are enabled.
- Browser checks for populated content, uploaded/optimized media, mobile navigation,
  themes and RTL locales; no interactive browser was available in this session.
- Off-host backups and an isolated restore rehearsal.
- Capacity and load testing on the chosen VPS.
- Optional private demos follow their separate readiness checklist and remain disabled.

Nginx recreation can briefly interrupt requests, and a code rollback cannot undo
shared database migrations or static assets. Dependency audits describe the versions
resolved during verification; later image builds can resolve newer versions within
the backend's declared ranges.
