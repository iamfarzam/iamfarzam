# Demo production verification

Verified on 2026-09-28 in an isolated Linux Docker stack using production Django
settings, PostgreSQL 16, Gunicorn, the production Next.js image, Nginx templates,
and an outer HTTPS proxy. All records, credentials, and upload fixtures were
fictional. No live deployment or production database was changed.

## Completed checks

- The full backend suite passed on Linux, including symlink rejection and Linux
  publication ownership. Django found no configuration errors or migration drift.
  Current suite sizes are recorded in [production-readiness.md](production-readiness.md)
  rather than repeated here, where they go stale as tests are added.
  Publication creates a verified snapshot that an existing uploader write handle
  cannot modify; altered snapshots are rejected before becoming public.
- Fresh-install readiness passed through production Nginx with no profile records.
  Deployment checks use `/healthz/`, which verifies the database without depending
  on published portfolio content.
- First-level `demo-<project>.example.com` routing passed for all demos. A locally
  trusted `*.example.com` test certificate matched those hosts and rejected nested
  hosts. Unknown, unprefixed and suffix-confused hosts were denied. Browser checks
  confirmed separate storage origins and host-only demo session cookies. Actual
  Cloudflare edge certificate activation remains a live-zone deployment check.
- 92 frontend tests passed on Linux Node 22 LTS; lint, clean dependency installation, and Docker
  production builds passed. Sharp is installed from the lockfile and explicitly
  checked during the production image build.
- A fresh public-only Git clone also passed the 112 backend and 92 frontend
  tests on Linux. The production Compose images built and started without importing
  private demo assets. Readiness, the empty project API, server-rendered projects,
  disabled demo access, migration consistency and Nginx syntax passed. Test
  overrides changed fixed container/network names and bound the listener to
  loopback; application configuration and startup commands stayed production.
  The cloned deployment script passed Bash syntax and LF line-ending checks.
- All 14 private release manifests passed inventory, checksum, and content scans.
- All 12 demos passed desktop/mobile navigation and workflow checks through HTTPS.
  Checks included booking conflicts, comment moderation, quiz scoring, stock
  transfers, settlements, server-enforced roles, isolated profile edits, and
  intercepted contact messages.
  Browser checks used headless Chromium with synthetic camera capture and local
  image fixtures; physical camera hardware and other browser engines were not tested.
- Browser face/hand inference and optional original-model emotion/mask inference
  passed. Model shape and finite output checks passed after the runtime update.
- Actual admin login and CSRF-protected form submissions passed. Enabling and
  disabling a demo updated server-rendered list/detail links and direct access.
- Host-only secure cookies, cross-origin write rejection, backend outage handling,
  service restart persistence, and recovery passed. A small concurrency check used
  18 requests across six clients; this is a smoke test, not a VPS capacity estimate.
- Demo containers ran as non-root with read-only filesystems, memory/CPU limits,
  dropped capabilities, and no public ports or Docker socket. Tests confirmed they
  could neither resolve the portfolio backend nor connect to its database network.
- The documented one-off publication commands passed with a separate writable
  mount. Both single-stack and blue-green Compose configurations passed Docker's
  strict configuration validation.
- npm dependency audits and audits of the actual backend/inference container Python
  packages reported no known vulnerabilities at verification time. This does not
  constitute an operating-system image audit or guarantee against future advisories.
- The Git privacy guard, pre-commit hook, and force-added-file regression test passed. Private
  demo artifacts, models, inventories, and environment files remain excluded.

## Required checks on the deployment server

Follow [demos.md](demos.md) before enabling demos. Verify each first-level demo DNS record and
trusted certificate, HTTPS redirect, origin firewall, proxy real-IP configuration,
CDN cache bypass, SFTP permissions, backups, and available CPU/RAM on that server.
Repeat the enable/disable and direct-URL checks against its actual public origins.
Local TLS used a test certificate and does not validate a production certificate.

Django's deployment check retains `security.W021` because HSTS preload is opt-in.
Only enable preload after deliberately qualifying the entire domain for that
browser policy. Production migrations and dependency upgrades require a database
backup and a tested application rollback procedure.

CI runs backend/frontend checks and the privacy guard. Private demo browser and
runtime tests stay in the ignored workspace; a fresh public clone cannot run or
restore them. Keep a restricted backup of that workspace and repeat the operator
checks whenever private releases or model runtimes change.
