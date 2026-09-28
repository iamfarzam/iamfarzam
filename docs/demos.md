# Private interactive demos

See [production verification](demo-production-checks.md) for completed checks and
the remaining checks required on the actual deployment server.

Demo hosting is optional and disabled by default. The public repository contains
the hosting feature, validation commands, and fictional tests. Personal demo
implementations, model weights, uploads, registry entries, and deployment files
belong exclusively in the ignored root `demos/` directory.

Browser-delivered HTML, JavaScript, and model assets can be downloaded by visitors.
Use replicas rather than original proprietary frontend code when redistribution
is unacceptable. Keep original backend code, secrets, and private models outside
`dist/`. Automated validation catches common mistakes; it does not replace reviewing
datasets, asset rights, personal metadata, and embedded credentials.

## Directory contract

```text
demos/
  inventory/                         # Private project specifications
  private/<project>/                 # Source, models, operator deployment files
  staging/<project>/<release>/
    manifest.json
    dist/                            # Sanitized public build only
  published/<project>/<release>/     # Immutable validated release
  config/services.json               # Operator-owned backend allowlist
```

Project and release names must be lowercase DNS labels: letters, numbers and
hyphens, at most 63 characters. Public project slugs have a 58-character limit
because the reserved `demo-` prefix also counts toward the 63-character host label.
A release cannot replace an existing release ID.
Upload a new ID to update a demo. The static entry page is `index.html`; a build
must use assets relative to its demo host, not the portfolio domain.

## Production setup

1. Create `published`, `staging`, and `config` under a stable SFTP-accessible host
   directory. Set `DEMOS_HOST_ROOT` to its absolute path in the server's `.env`.
   Keep this directory independent of deployment cleanup and application images.
2. Set `DEMOS_BASE_DOMAIN=example.com` to your root DNS zone, not `demos.example.com`.
   Add a DNS record for each `demo-<project-slug>.example.com`, and make sure TLS
   covers those first-level hosts. Cloudflare Universal SSL in a full DNS setup
   covers the root and first-level subdomains when the records are proxied; see
   [Cloudflare's coverage limits](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/limitations/).
   No nested wildcard or paid deep-subdomain certificate is required. Explicit
   records avoid changing DNS behavior for unrelated subdomains. A dedicated
   origin certificate or wildcard `*.example.com` must also cover the hostnames
   when the HTTPS proxy connects to the origin using TLS.
   Terminate TLS at your existing trusted reverse proxy and forward to Nginx.
   Set `NGINX_PROXY_SCHEME=https` so portfolio admin requests preserve their
   secure origin through that HTTP hop. Restrict the origin listener to your
   trusted proxy and redirect public HTTP to HTTPS at the outer proxy.
   For server-rendered API requests over private HTTP, set
   `INTERNAL_API_FORWARD_PROTO=https` alongside `INTERNAL_API_URL`; this avoids
   redirects to HTTPS on a backend port that only speaks HTTP.
   Enable `SECURE_SSL_REDIRECT=True` after HTTPS is working.
   Configure the CDN to bypass caching for every demo hostname and path.
3. Generate `DEMOS_GATE_SECRET` independently with at least 32 characters, e.g.
   `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Keep the same
   value in the portfolio backend and Nginx environment. It must not be placed
   inside demo builds or passed to demo services.
4. Set `DEMOS_AUTH_HOST` to a hostname in Django's `ALLOWED_HOSTS`.
   Leave `DEMOS_PROXY_URL=http://nginx` for Compose. The backend uses this private
   proxy address to probe services without joining their networks.
5. Set `DEMOS_ENABLED=True`, run migrations, and recreate Nginx and application
   containers to load the settings and templates. Existing projects still have
   no enabled demos. Both production Compose layouts include the mounts.

The normal website stays on its existing hostname. Every demo has a separate
origin at `https://demo-<project-slug>.example.com/`. Demo paths on the portfolio
origin are deliberately unsupported. Do not add demo origins to portfolio CORS
or trusted-CSRF settings, and do not configure parent-domain session cookies.
Secure production portfolio cookies now use the `__Host-` prefix; existing admin
users must sign in again when demo hosting is enabled. With hosting disabled,
existing cookie names remain unchanged. Secure session and CSRF cookies are
required when production demo hosting is enabled, including behind external TLS.
Keep `NGINX_SERVER_NAMES` limited to portfolio hostnames: a wildcard such as
`*.example.com` would take precedence over the demo regex server. All static,
API and WebSocket requests still pass the same activation gate. With Cloudflare,
the reserved `demo-*` hostnames must use a cache-bypass rule for every path.

### Cloudflare configuration

1. In the root zone's DNS dashboard, create a proxied A record named
   `demo-sample-project` pointing to the origin's IPv4 address. Alternatively,
   use a proxied CNAME to the existing portfolio ingress. Repeat for each project;
   all releases of a project use the same record. Only add AAAA records when the
   origin's IPv6 route and firewall are configured too.
2. Confirm the zone's Universal SSL certificate is active and covers
   `*.example.com`. Proxy status must be enabled for Cloudflare to serve this
   edge certificate. This covers `demo-sample-project.example.com` without a
   nested `*.demos.example.com` certificate.
3. Preserve the existing trusted HTTPS origin setup. Use Full (strict) when
   Cloudflare connects to a TLS origin with a valid certificate covering these
   hostnames. The shipped Nginx templates listen on HTTP port 80 and therefore
   need an outer TLS proxy or a protected tunnel. `NGINX_PROXY_SCHEME=https`
   preserves Django's secure request context; it does not create a TLS listener.
   Forward the original Host to Nginx and restrict direct origin access.
4. Enable the public HTTP-to-HTTPS redirect. Add a Cache Rule with Bypass cache
   for hostnames starting with `demo-` in this zone, covering every path. Remove
   conflicting cache rules and purge previously cached demo responses before
   testing revocation. Never cache demo API or HTML responses.
5. Verify `/`, an asset, and backend interactions over each real HTTPS hostname.
   Disable a demo in admin and confirm its direct URL is unavailable. Cloudflare
   DNS/certificate checks must be done on the live zone; the local verification
   stack uses a fictional root domain and certificate.

When upgrading from the previous nested-host configuration, change
`DEMOS_BASE_DOMAIN` from `demos.example.com` to `example.com`, add the first-level
records, and recreate the backend, frontend and Nginx containers. No database
migration or public build change is needed specifically for the hostname switch.
Private backend services that derive project names from Host must remove the
`demo-` prefix; update/rebuild those services too. Old nested-host requests are
not redirected or authorized. Keep portfolio CORS and CSRF origins unchanged.

## SFTP upload and publication

Upload **only the sanitized build** into `staging/<project>/<release>/dist/`,
then generate its manifest. For a blue-green deployment, substitute the active
project name for `portfolio-blue`:

```bash
docker compose -f docker-compose.app.yml -p portfolio-blue run --rm --no-deps \
  -v "$DEMOS_HOST_ROOT:/demo-publication:rw" \
  -e DEMOS_ROOT=/demo-publication backend \
  python manage.py demo_manifest sample-project v1

docker compose -f docker-compose.app.yml -p portfolio-blue run --rm --no-deps \
  -v "$DEMOS_HOST_ROOT:/demo-publication:rw" \
  -e DEMOS_ROOT=/demo-publication backend \
  python manage.py demo_release sample-project v1 --publish
```

Here `$DEMOS_HOST_ROOT` must be an exported **absolute host path**, not just a
value in `.env`; for example `export DEMOS_HOST_ROOT=/srv/portfolio-demos`.
The separate `/demo-publication` mount is needed because ordinary backend
containers have read-only subdirectory mounts under `/app/demos`. Overriding
that parent alone does not remove those nested mounts. Keeping staging and
published under one writable mount also permits atomic directory renames.
With the single-stack deployment, use
`-f docker-compose.prod.yml` and omit `-p portfolio-blue`.

Use `--spa` on `demo_manifest` only when extensionless HTML navigation routes
should fall back to the entry page. Missing JS, images, and other assets never
fall back to HTML. `--service <key>` creates a backend manifest.
`--script-eval` enables a per-release CSP exception for reviewed legacy WASM
bindings that require JavaScript eval; omit it for normal browser builds.

The v1 manifest format is:

```json
{
  "version": 1,
  "project": "sample-project",
  "release": "v1",
  "type": "static",
  "entry": "index.html",
  "spa": false,
  "script_eval": false,
  "files": {"index.html": "<64-character SHA-256 checksum>"}
}
```

The validator checks the file inventory and hashes, permitted file types, common
credential patterns, noncanonical paths, dotfiles, extra files, and symlinks.
It rejects source maps, archives, environment files and server source. Promotion
copies the upload into an operator-owned snapshot, validates those copied bytes,
and renames the snapshot atomically into the published directory. Staging remains
available for inspection; the operator can remove it after successful publication.
Do not upload into a published release. Give the SFTP user write access to
staging only; published releases and the registry must be operator-owned and
readable by container users. On Linux publication copies through directory file
descriptors without following symlinks. New files belong to the invoking operator,
with directories set to 0755 and files to 0644. An uploader's existing write handles
cannot modify the published copy. Run this one-off command as an operator authorized
to read the uploads (the backend image uses root); never as the SFTP uploader.
The `published` parent must also be operator-owned and unwritable by the uploader.
Mounts remain read-only during serving.

Large vendored WASM-in-JavaScript builds can contain random strings resembling
credential patterns. For a verified false positive, an operator can place an
exact SHA-256 checksum and a substantive review reason in the private
`config/reviewed-assets.json` object. Only that exact byte sequence is exempt;
changing the dependency requires another review. Never exempt an actual secret.

## Backend demos

Backend source is uploaded under `private/` and is deployed through a separately
reviewed operator Compose file. Uploading a manifest never executes code.

Register fixed internal services in `config/services.json`:

```json
{
  "sample-service": {"url": "http://demo-sample-service:8080"}
}
```

Use a `demo-*` Docker hostname and explicit port. Public URLs, credentials in
URLs, paths, redirects and portfolio service hostnames are rejected. The backend
manifest references the registry key using `"service": "sample-service"`.
Services must provide `GET /healthz` returning 200 and JSON such as
`{"ready": true, "release": "v1"}`. The reported release must match the selected
manifest, so an old running service cannot activate a newer uploaded build.
Readiness checks traverse the
proxy using a private authenticated probe; they work before public activation.

Connect demo services to `portfolio_demo_edge`, which is shared only with the
edge proxy, not the portfolio backend or databases. More sensitive demos should
use a separate private network per stack and connect Nginx to the needed networks.
Use unique host-only secure cookies, server-side sandbox ownership, 24-hour expiry,
reset and cleanup, bounded record counts, and request limits. Reject cross-origin
writes. Intercept email, payment and external integrations. Never expose the
portfolio's production admin or reuse its data and credentials.

Run containers without public ports, as non-root, with dropped capabilities,
`no-new-privileges`, read-only filesystems, resource limits, and writable volumes
only for demo data. Do not mount the Docker socket. Test CPU and memory under
concurrent visitors before enabling a service; private CPU model inference can
require substantially more memory than a browser simulation.

The local private workspace may contain its own deployment commands and tests;
these intentionally do not ship in the open-source repository.

## Enable, disable, and rollback

Edit a project in Django admin, add its Demo configuration, select a published
release, enter instructions/disclosure, and enable it. Saving an enabled demo
verifies checksums and backend readiness. Saving a disabled configuration also
records readiness feedback, which can be inspected before enabling it.

The project API exposes only a public demo URL, runtime, instructions and
disclosure; private paths and upstreams are excluded. Cards and project detail
pages distinguish the existing website from the interactive demo.

Every new static request, backend request and WebSocket handshake passes the
availability gate. Disabling the configuration blocks direct requests as well
as hiding its link on fresh API responses. Backend or authorization failure
fails closed. Already downloaded pages/assets and established connections cannot
be revoked; stop a service to terminate existing server connections. Set the
existing frontend `NEXT_PUBLIC_REVALIDATE=0` for immediately refreshed links.

Public serializers cache backend readiness for up to 15 seconds to avoid running
a health request for every card render. Admin activation always performs a fresh
check; disabling public access does not depend on this health cache.

The demo edge limits each client address to 10 requests/second with a burst of
100, and 20 simultaneous connections. When an outer proxy/CDN is used, configure
Nginx real-IP handling for that proxy's trusted addresses; never trust arbitrary
forwarded client-IP headers from the public internet.

Rollback a demo by selecting an older immutable release. Backend service rollback
is an operator action; keep the demo disabled during incompatible service updates.
Portfolio blue-green deployment and rollback preserve private uploads and demo
stacks. Back up private files and demo volumes separately with restricted access;
never publish backups or attach them to public issues.

Before committing, run `node scripts/check-private-files.mjs`. CI runs the same
guard. Install the local pre-commit check with
`git config --local core.hooksPath .githooks` to reject private files before a
commit is created. Hook configuration is local to a clone; enable it again in
each fresh clone. CI also checks the
index for tracked demo content and private environment files, including files
force-added despite gitignore. Gitignore and CI cannot undo content already pushed:
rotate exposed credentials immediately if an accidental publication occurs.
