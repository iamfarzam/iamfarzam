# Production upgrades

`example.com` is an existing production deployment. Upgrade the current stack
in its current server checkout. Keep the existing `.env`, secrets, DNS, TLS
termination, origin listener, Compose project name, volumes and content.
Do not copy `.env.example` over the live `.env`, regenerate credentials, reseed
content, create another admin account, or run `deploy.sh fresh` during an upgrade.

The production Compose files retain the original public port-80 default. The
optional `NGINX_BIND_ADDRESS` and `NGINX_HTTP_PORT` variables change it only when
explicitly configured. Django's existing redirect default is also preserved;
HTTPS hardening requires verification of the current proxy hop.

Verification results are recorded in [production-readiness.md](production-readiness.md).
A read-only HTTPS check confirmed `example.com` returns HTTP 200 through Cloudflare. The origin deployment mode and TLS configuration have not been inspected.
Use the path matching the running stack; do not migrate deployment modes as part
of this update. The two modes share infrastructure names and cannot run together.

Nginx trusts Cloudflare's officially published edge networks for visitor IP restoration when Cloudflare connects directly. If another proxy sits between Cloudflare and Nginx, configure that exact trusted peer too. Review the embedded ranges against [Cloudflare's current IP lists](https://www.cloudflare.com/ips/) when upgrading; forwarding headers from other peers are discarded.

## Upgrade the existing server

1. In the existing checkout, record `git rev-parse HEAD`, `git status --short`,
   `docker ps`, and the current Compose project name. Save a restricted backup of
   `.env`, dump PostgreSQL, and back up media using the commands below. Preserve
   the current image IDs for rollback; do not prune images during the upgrade.
2. Drain outstanding Celery work before the first Redis persistence update:
   inspect `active`, `reserved` and `scheduled` jobs on the existing worker and
   account for queued jobs. Enabling AOF recreates an existing Redis container;
   its previous in-memory queue is not automatically copied into the new volume.
   Apply that infrastructure change in a planned maintenance window.
3. Add the HTTPS settings an older `.env` predates. The production security check
   fails the release on `security.W008` unless `SECURE_SSL_REDIRECT=True`, and
   `deploy.sh` now refuses before building rather than after. Once TLS terminates
   at your proxy, set all of these together:

   ```dotenv
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   NGINX_PROXY_SCHEME=https
   INTERNAL_API_FORWARD_PROTO=https
   ```

   `NGINX_PROXY_SCHEME=https` is required with the redirect: the origin hop into
   container Nginx is plain HTTP, so `auto` would make Django 301 every API, admin
   and health request. `INTERNAL_API_FORWARD_PROTO=https` keeps server-side
   rendering from being redirected. Do not expose that HTTP listener to untrusted
   clients once Nginx asserts HTTPS. Set `NGINX_TRUSTED_PROXY` only to the actual
   trusted peer if forwarding client addresses. Keep the current listener and
   proxy upstream.
4. Update the existing checkout to the tested `master` revision with
   `git pull --ff-only` once these commits have been pushed. Use the existing
   production `.env` and Compose project name when validating the model.

For an existing blue/green installation with a valid `.deployed.state`:

```bash
bash deploy.sh status
bash deploy.sh deploy --no-pull
bash deploy.sh status
```

For an existing single-stack installation, retain its current Compose project
name (if you previously used `-p`, use the same value for every command):

```bash
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    python manage.py check --deploy --fail-level WARNING
docker compose -f docker-compose.prod.yml up -d --wait --wait-timeout 180
```

Resolve security-check failures using the verified proxy settings before
replacing application containers. Startup performs migrations and collects
static files. Check existing content, admin access, media and contact delivery:

```bash
curl --fail --max-time 15 https://example.com/healthz/
curl --fail --max-time 15 https://example.com/frontend-healthz/
curl --fail --max-time 15 https://example.com/api/v1/profile/
curl --fail --max-time 15 https://example.com/ -o /dev/null
```

With Node.js 22 or newer, run
`SMOKE_BASE_URL=https://example.com node scripts/production-smoke.mjs` for the
read-only public checks. For blue/green failure, use `bash deploy.sh rollback`
while previous images remain compatible with the current database. For a single
stack, use retained previous images or check out the recorded revision and
rebuild with the same project name. Neither method reverses database migrations.
Never run `down -v` on the production stack.

The remaining sections describe new-installation setup and operational reference.
They do not require changing `example.com`'s existing infrastructure.

## Reference: preparing a new installation

Install Docker using the [official installation guide](https://docs.docker.com/engine/install/)
and verify `docker compose version`. Allow public ports 80/443 for your TLS proxy
and restrict SSH to your administration network. Point your domain's DNS to the
VPS. Ensure enough free disk and memory to build Next.js; blue/green temporarily
runs two application stacks. No fixed minimum has been load-tested.

```bash
git clone https://github.com/portfolio-owner/portfolio-owner.git portfolio
cd portfolio
cp .env.example .env
chmod 600 .env
mkdir -p fixtures demos/published demos/config demos/staging
# Generate two independent values; paste one into DJANGO_SECRET_KEY and use
# the other for POSTGRES_PASSWORD and the password in DATABASE_URL.
openssl rand -hex 48
openssl rand -hex 32
```

Edit `.env`, replacing every `example.com` and placeholder credential. Use a hex
password so it is safe inside the database URL. Relevant production values:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<first-generated-value>
POSTGRES_DB=portfolio
POSTGRES_USER=portfolio
POSTGRES_PASSWORD=<second-generated-value>
DATABASE_URL=postgres://portfolio:<second-generated-value>@postgres:5432/portfolio
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
NEXT_PUBLIC_SITE_URL=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://yourdomain.com/api/v1
NEXT_PUBLIC_SITE_TITLE=Your Name
NEXT_PUBLIC_REVALIDATE=0
PUBLIC_MEDIA_BASE_URL=https://yourdomain.com
INTERNAL_API_URL=http://backend:8000/api/v1
INTERNAL_API_FORWARD_PROTO=https
NGINX_SERVER_NAMES=yourdomain.com www.yourdomain.com
NGINX_PROXY_SCHEME=https
NGINX_BIND_ADDRESS=127.0.0.1
NGINX_HTTP_PORT=8080
CELERY_BROKER_URL=redis://redis:6379/0
DJANGO_CACHE_URL=redis://redis:6379/1
DEMOS_ENABLED=False
ACTIVE_COLOR=blue
```

The blue/green Compose file sets `INTERNAL_API_URL` to the current colour's
backend automatically. Keep `localhost` in `ALLOWED_HOSTS` if using the default
private demo gate host. Public URLs and the allowed image origins are compiled
into the frontend image: rebuild when changing these values. An optional custom
storage origin belongs in `PUBLIC_MEDIA_BASE_URL`; configure the S3 settings
listed in `.env.example` as well.

## 2. Configure HTTPS

Terminate TLS at a reverse proxy on the same host, forwarding to
`http://127.0.0.1:8080`. For example, install Caddy on the host and use this Caddyfile
(replace both hostnames):

```caddyfile
yourdomain.com, www.yourdomain.com {
    reverse_proxy 127.0.0.1:8080
}
```

Caddy manages certificates and HTTP-to-HTTPS redirects. See its
[automatic HTTPS documentation](https://caddyserver.com/docs/automatic-https).
Keep `NGINX_PROXY_SCHEME=https`: the inner Nginx uses HTTP and asserts HTTPS only
because it is reachable through this trusted proxy. Do not expose that listener
to untrusted clients. A containerized outer proxy needs a private Docker network
and an appropriate upstream instead of the host-loopback address.

Set `NGINX_TRUSTED_PROXY` to the exact TLS proxy peer address as seen by container
Nginx. For host Caddy this is usually a Docker bridge gateway. After the first
startup, make a request through Caddy, inspect `docker logs portfolio-nginx`,
and use the logged proxy peer address. Set that value in `.env`, then run
`docker compose -f docker-compose.infra.yml -p portfolio-infra up -d --force-recreate --no-deps nginx`
(or use `docker-compose.prod.yml` for the single stack). Verify that requests
through Caddy now log individual client IPs before opening the site to visitors.
Nginx trusts this peer's forwarding header and replaces the downstream header.
Never trust arbitrary networks. Until configured, contact throttling shares the
proxy's five/hour limit among its visitors. Production counters are shared in
Redis across workers and deployment colours.

## 3. Deploy

### Blue/green deployment

```bash
bash deploy.sh fresh
bash deploy.sh status
# The first active colour is blue.
docker exec -it portfolio-blue-backend python manage.py createsuperuser
```

The script builds images, checks production security settings, waits for backend
and frontend readiness, and verifies Nginx routing and the homepage before
retiring the old colour. Startup applies migrations and collects static assets.
It recreates Nginx when switching colours, so a brief interruption is possible.
Database migrations and static files are shared between colours; this is not a
transactional rollback of database or assets.

For later releases, back up first, then run:

```bash
bash deploy.sh deploy
bash deploy.sh status
# Restart the previous colour's retained images and switch traffic back:
bash deploy.sh rollback
```

Use `--no-pull` when deploying an already checked-out revision. `fresh` refuses
to overwrite recorded active state. Use backward-compatible migrations during
blue/green overlap; destructive schema changes require a separate maintenance
plan. Old Celery workers may execute queued jobs while the new colour starts,
so task changes must also be compatible. Rollback is available only while the
previous images remain on the host and its code works with the current schema.

### Single-stack deployment

```bash
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    python manage.py check --deploy --fail-level WARNING
docker compose -f docker-compose.prod.yml up -d --wait --wait-timeout 180
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

For updates, back up, check out the desired release, and repeat build/check/up.
This replaces services in place and can interrupt traffic. To return to an older
release, check it out and rebuild; database compatibility is still required.
Never use `down -v` against production: it deletes persistent data.

## 4. Populate content and verify the release

Log in at `https://yourdomain.com/admin/` and create the profile and projects.
Readiness deliberately works with an empty portfolio. Optionally import your
private fixtures with the active backend's `manage.py seed --fixture-dir /app/fixtures`.
Do not use `seed --flush` on production content you need to keep.

For blue/green, replace `blue` below with the active colour:

```bash
docker exec portfolio-blue-backend python manage.py check --deploy --fail-level WARNING
docker exec portfolio-blue-backend python manage.py migrate --check
docker exec portfolio-nginx nginx -t
docker exec portfolio-blue-celery celery -A config inspect ping --timeout 10
curl --fail --max-time 15 https://yourdomain.com/healthz/
curl --fail --max-time 15 https://yourdomain.com/frontend-healthz/
curl --fail --max-time 15 https://yourdomain.com/api/v1/profile/
curl --fail --max-time 15 https://yourdomain.com/ -o /dev/null
curl --fail --max-time 15 https://yourdomain.com/projects -o /dev/null
curl --fail --max-time 15 https://yourdomain.com/robots.txt
curl --fail --max-time 15 https://yourdomain.com/sitemap.xml
```

With Node.js 22 or newer installed on the host, `SMOKE_BASE_URL=https://yourdomain.com node scripts/production-smoke.mjs` runs the read-only HTTP checks above, including admin cookies, static CSS and the private-gate boundary.

Verify the HTTP origin redirects to HTTPS, the admin login succeeds, cookies
have `Secure`/`HttpOnly` where appropriate, and uploaded media and optimized
images load. Check light/dark themes, mobile navigation, contact validation,
language changes including RTL, and a project detail page in a browser.
Submit one real contact message and confirm it is saved in admin. If email is
required, configure SMTP and `CONTACT_NOTIFY_EMAIL`, then confirm delivery;
the default console email backend does not deliver email externally.

With `NEXT_PUBLIC_REVALIDATE=0`, content is fetched on each request. A positive
value caches API responses for that number of seconds; there is no automatic
one-hour delay or configured on-demand revalidation endpoint.

## 5. Backups and operations

For blue/green deployments, the database container is always `portfolio-postgres`
and media is in `portfolio_backend_media`:

```bash
mkdir -p backups
chmod 700 backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker exec portfolio-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "backups/database-$stamp.dump"
docker run --rm -v portfolio_backend_media:/media:ro \
    -v "$PWD/backups:/backup" alpine \
    tar -czf "/backup/media-$stamp.tar.gz" -C /media .
```

For the single stack, get the media volume name from
`docker volume ls --filter label=com.docker.compose.volume=backend_media` and
substitute it in the backup command. Back up `.env`, private fixtures, and demo
releases separately with restricted access. Copy backups off the VPS, schedule
them, and test a restore to an isolated database before relying on them. Restoring
a backup overwrites data and requires coordinated maintenance; ordinary code
rollback does not restore the database.

Monitor external HTTPS readiness, disk use, container restarts, database backups,
and email failures. Redis AOF data persists broker queues and throttle counters.
Review logs with `docker logs --tail 100 <active-container>`; regularly prune old
images only after the rollback window. Django file logs are in a persistent
volume, but concurrent workers can interfere with file rotation; use collected
container stdout logs as the operational source of truth.

Private demos remain disabled until their separate DNS, TLS, upload and gate
checks pass. See [demos.md](demos.md) and [demo-production-checks.md](demo-production-checks.md).

HSTS subdomain coverage and preload are explicit domain-owner opt-ins. Production settings silence only `security.W005` and `security.W021`; all other deployment warnings still fail the release check.

Production security checks follow Django's
[deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
Service startup uses Compose
[health dependencies](https://docs.docker.com/compose/how-tos/startup-order/).
