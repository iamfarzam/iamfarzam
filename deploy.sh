#!/usr/bin/env bash
#
# Blue-green production deployment for the portfolio stack.
#
# Architecture:
#   - docker-compose.infra.yml  — postgres, redis, nginx (project: portfolio-infra)
#   - docker-compose.app.yml    — backend, celery, frontend (project: portfolio-blue OR portfolio-green)
#
# At any time, exactly one colour is "active" (nginx upstream points at it)
# and the other is either "idle" or doesn't exist. Deployment brings up the
# IDLE colour, healthchecks it, runs migrations, then flips nginx. On any
# failure the new colour is torn down and the previously-active colour
# keeps serving traffic uninterrupted. Rollback re-flips back if the
# previous colour is still up.
#
# Subcommands:
#   ./deploy.sh                     auto-detect (fresh on first run, blue-green flip on subsequent)
#   ./deploy.sh fresh               first-time bring-up (no current colour)
#   ./deploy.sh deploy              build + bring up idle colour, flip nginx, retire old colour
#   ./deploy.sh rollback            flip nginx back to the previous colour (if still running)
#   ./deploy.sh status              show current and previous colour, image versions
#   ./deploy.sh --version v1.2.3    override the auto-resolved git SemVer
#   ./deploy.sh --no-pull           skip `git pull` during deploy
#   ./deploy.sh --help
#
# Required: docker, docker compose v2, git, .env, repo root as cwd.

set -euo pipefail

# ---------------------------------------------------------------------------
INFRA_PROJECT="portfolio-infra"
INFRA_FILE="docker-compose.infra.yml"
APP_FILE="docker-compose.app.yml"
STATE_FILE=".deployed.state"
VERSION_FILE="backend/VERSION"
ENV_FILE=".env"
HEALTHCHECK_TIMEOUT=120
PUBLIC_HEALTH_PATH="/healthz/"

if [[ -t 1 ]]; then
    BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; CYAN=$'\033[36m'; RESET=$'\033[0m'
else
    BOLD=""; GREEN=""; YELLOW=""; RED=""; CYAN=""; RESET=""
fi
log()  { echo "${CYAN}==>${RESET} ${BOLD}$*${RESET}"; }
ok()   { echo "${GREEN}✓${RESET} $*"; }
warn() { echo "${YELLOW}!${RESET} $*"; }
die()  { echo "${RED}✗${RESET} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------
SUBCMD=""
VERSION_OVERRIDE=""
SKIP_PULL=false

usage() {
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        fresh|deploy|rollback|status) SUBCMD="$1"; shift ;;
        --version) VERSION_OVERRIDE="${2:-}"; shift 2 ;;
        --no-pull) SKIP_PULL=true; shift ;;
        -h|--help) usage ;;
        *) die "Unknown argument: $1 (use --help)";;
    esac
done

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
preflight() {
    command -v docker >/dev/null 2>&1 || die "docker not found in PATH"
    docker compose version >/dev/null 2>&1 || die "docker compose v2 plugin missing"
    command -v git >/dev/null 2>&1 || die "git not found in PATH"
    [[ -f "$INFRA_FILE" ]] || die "$INFRA_FILE missing — run from the repo root"
    [[ -f "$APP_FILE" ]]   || die "$APP_FILE missing — run from the repo root"
    [[ -f "$ENV_FILE" ]]   || die "$ENV_FILE missing — copy .env.example and fill in secrets"
    git rev-parse --git-dir >/dev/null 2>&1 || die "Not inside a git repository"
    check_required_env
    check_proxy_scheme
    check_compose_models
}

# Fail on a missing value before spending a full image build to discover it.
check_required_env() {
    local missing=() name
    for name in DJANGO_SECRET_KEY DATABASE_URL POSTGRES_PASSWORD ALLOWED_HOSTS \
                NEXT_PUBLIC_SITE_URL NEXT_PUBLIC_API_URL NGINX_SERVER_NAMES \
                CELERY_BROKER_URL; do
        [[ -n "$(env_value "$name")" ]] || missing+=("$name")
    done
    [[ ${#missing[@]} -eq 0 ]] || die "${ENV_FILE} is missing values for: ${missing[*]}"
}

check_compose_models() {
    docker compose -f "$INFRA_FILE" config --quiet >/dev/null 2>&1 \
        || die "$INFRA_FILE is not a valid Compose model"
    COMPOSE_PROJECT_NAME="portfolio-blue" docker compose -f "$APP_FILE" config --quiet >/dev/null 2>&1 \
        || die "$APP_FILE is not a valid Compose model"
}

env_value() {
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '[:space:]' || true
}

check_proxy_scheme() {
    # The hop into container nginx is plain HTTP. With SECURE_SSL_REDIRECT on,
    # Django 301s everything unless nginx asserts https, which would only be
    # discovered after the flip — so refuse the deploy up front instead.
    local redirect scheme
    redirect="$(env_value SECURE_SSL_REDIRECT | tr '[:upper:]' '[:lower:]')"
    scheme="$(env_value NGINX_PROXY_SCHEME | tr '[:upper:]' '[:lower:]')"
    case "$redirect" in
        1|true|yes|on)
            [[ "$scheme" == "https" ]] || die \
                "SECURE_SSL_REDIRECT is enabled but NGINX_PROXY_SCHEME=${scheme:-auto}; set NGINX_PROXY_SCHEME=https in ${ENV_FILE}"
            ;;
    esac
}

# ---------------------------------------------------------------------------
# State helpers — track current and previous colours in a tiny TOML-ish file
# ---------------------------------------------------------------------------
read_state() {
    local key="$1"
    [[ -f "$STATE_FILE" ]] || { echo ""; return; }
    grep -E "^${key}=" "$STATE_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true
}

write_state() {
    local active="$1" previous="$2" version="$3"
    cat > "$STATE_FILE" <<EOF
active=${active}
previous=${previous}
version=${version}
deployed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
git_sha=$(git rev-parse HEAD)
EOF
}

other_colour() {
    case "$1" in
        blue)  echo "green" ;;
        green) echo "blue" ;;
        *)     echo "blue" ;;
    esac
}

# ---------------------------------------------------------------------------
# Version resolution from git (writes backend/VERSION)
# ---------------------------------------------------------------------------
resolve_version() {
    if [[ -n "$VERSION_OVERRIDE" ]]; then
        echo "$VERSION_OVERRIDE"
        return
    fi
    if git describe --tags --abbrev=0 >/dev/null 2>&1; then
        local desc
        # SemVer build metadata, not a fourth version part: "0.21.0.dirty" is not
        # a version, and PROJECT_VERSION is asserted to be SemVer.
        desc="$(git describe --tags --always --dirty=+dirty 2>/dev/null)"
        echo "${desc#v}"
    else
        local count sha dirty=""
        count="$(git rev-list --count HEAD)"
        sha="$(git rev-parse --short HEAD)"
        if ! git diff-index --quiet HEAD --; then dirty=".dirty"; fi
        echo "0.0.0+${count}.g${sha}${dirty}"
    fi
}

write_version() {
    local v="$1"
    [[ -f "$VERSION_FILE" ]] && [[ "$(<"$VERSION_FILE")" == "$v" ]] && return
    echo "$v" > "$VERSION_FILE"
    ok "Wrote ${VERSION_FILE} = ${v}"
}

# ---------------------------------------------------------------------------
# Compose helpers
# ---------------------------------------------------------------------------
infra_compose() { docker compose -f "$INFRA_FILE" -p "$INFRA_PROJECT" "$@"; }
app_compose()   {
    local colour="$1"; shift
    COMPOSE_PROJECT_NAME="portfolio-${colour}" \
        docker compose -f "$APP_FILE" -p "portfolio-${colour}" "$@"
}

ensure_infra_up() {
    log "Bringing up infrastructure (postgres, redis, nginx)"
    # Compose owns the portfolio_net network on first up; the app stack
    # declares it as external so it just attaches.
    infra_compose up -d --wait
    ok "Infra healthy"
}

set_active_colour_in_env() {
    local colour="$1"
    if grep -q '^ACTIVE_COLOR=' "$ENV_FILE"; then
        # Portable in-place edit: rewrite via temp file.
        local tmp
        tmp="$(mktemp)"
        sed "s/^ACTIVE_COLOR=.*/ACTIVE_COLOR=${colour}/" "$ENV_FILE" > "$tmp"
        mv "$tmp" "$ENV_FILE"
    else
        printf '\nACTIVE_COLOR=%s\n' "$colour" >> "$ENV_FILE"
    fi
}

reload_nginx() {
    log "Reloading nginx"
    # Recreate nginx so the templated default.conf is regenerated with the
    # new ACTIVE_COLOR. Faster and safer than a hot reload + manual rewrite.
    if ! infra_compose up -d --force-recreate --no-deps nginx; then
        warn "nginx recreation failed"
        return 1
    fi
    sleep 2
    if ! infra_compose exec -T nginx nginx -t >/dev/null 2>&1; then
        warn "nginx config invalid after reload"
        return 1
    fi
    ok "nginx now points at ${1:-?} colour"
}

primary_host() {
    # First entry from NGINX_SERVER_NAMES — used as the Host: header so
    # Django ALLOWED_HOSTS and nginx server_name checks both pass.
    grep -E '^NGINX_SERVER_NAMES=' "$ENV_FILE" 2>/dev/null \
        | head -1 | cut -d= -f2- | awk '{print $1}' || echo localhost
}

smoke_test_internal() {
    local colour="$1"
    local host
    host="$(primary_host)"
    log "Smoke-testing ${colour} backend (Host: ${host})"
    local container="portfolio-${colour}-backend"
    for _ in $(seq 1 20); do
        if docker exec -e PRIMARY_HOST="$host" "$container" python -c \
            "import os,urllib.request; req=urllib.request.Request('http://127.0.0.1:8000${PUBLIC_HEALTH_PATH}', headers={'Host':os.environ['PRIMARY_HOST'],'X-Forwarded-Proto':'https'}); urllib.request.urlopen(req, timeout=3)" \
            >/dev/null 2>&1; then
            ok "${colour} backend responds"
            return 0
        fi
        sleep 2
    done
    return 1
}

status_via_nginx() {
    local host="$1" path="$2" timeout="$3"
    # BusyBox wget has no --max-redirect and follows a 301 to the real public
    # domain, which would smoke-test the OLD live site instead of this stack.
    # Read the first status line only, so a redirect is never mistaken for a pass.
    docker exec portfolio-nginx sh -c \
        "wget -S -T ${timeout} -O /dev/null --header='Host: ${host}' 'http://127.0.0.1${path}' 2>&1 | grep -m1 'HTTP/'" \
        2>/dev/null | grep -oE 'HTTP/[0-9.]+ [0-9]{3}' | grep -oE '[0-9]{3}$'
}

probe_via_nginx() {
    [[ "$(status_via_nginx "$1" "$2" "$3")" =~ ^2[0-9][0-9]$ ]]
}

smoke_test_public() {
    local host
    host="$(primary_host)"
    log "Smoke-testing public endpoint via nginx (Host: ${host})"
    # Use 127.0.0.1 explicitly: 'localhost' often resolves to IPv6 ::1 first
    # in alpine /etc/hosts, and nginx in this image listens on IPv4 only.
    for _ in $(seq 1 15); do
        if probe_via_nginx "$host" "${PUBLIC_HEALTH_PATH}" 5 \
            && probe_via_nginx "$host" "/frontend-healthz/" 5 \
            && probe_via_nginx "$host" "/api/v1/projects/" 5 \
            && probe_via_nginx "$host" "/" 10; then
            # The private demo gate must never be reachable from the public origin.
            local gate_status
            gate_status="$(status_via_nginx "$host" "/internal/demos/authorize/" 5)"
            if [[ "$gate_status" != "404" ]]; then
                warn "Private demo gate is publicly reachable (HTTP ${gate_status:-no response})"
                return 1
            fi
            ok "Public endpoint responds"
            return 0
        fi
        sleep 2
    done
    return 1
}

# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------
cmd_status() {
    local active previous version
    active="$(read_state active)"
    previous="$(read_state previous)"
    version="$(read_state version)"
    echo "Active colour:    ${active:-<none>}"
    echo "Previous colour:  ${previous:-<none>}"
    echo "Version:          ${version:-<unknown>}"
    echo
    echo "Running app stacks:"
    for c in blue green; do
        if docker ps --filter "name=portfolio-${c}-backend" --format '{{.Names}}' | grep -q .; then
            echo "  ${c}: up"
        else
            echo "  ${c}: down"
        fi
    done
    echo
    if docker ps --filter "name=portfolio-nginx" --format '{{.Names}}' | grep -q .; then
        echo "Infra: up"
    else
        echo "Infra: down"
    fi
}

# ---------------------------------------------------------------------------
# Subcommand: deploy (or fresh)
# ---------------------------------------------------------------------------
cmd_deploy() {
    local mode="${1:-deploy}"   # "fresh" or "deploy"
    local current_active target

    current_active="$(read_state active || true)"
    if [[ "$mode" == "fresh" ]] && [[ -n "$current_active" ]]; then
        die "An active deployment already exists; use deploy instead of fresh"
    fi
    if [[ "$mode" == "fresh" ]] || [[ -z "$current_active" ]]; then
        target="blue"
        current_active=""
        log "Fresh deploy → bringing up colour: ${target}"
    else
        target="$(other_colour "$current_active")"
        log "Blue-green deploy: active=${current_active}, target=${target}"
    fi

    # Pull latest code (unless told not to and we're not on a fresh run).
    if [[ "$mode" != "fresh" ]] && [[ "$SKIP_PULL" == false ]]; then
        log "Pulling latest code"
        if ! git diff-index --quiet HEAD --; then
            warn "Working tree has uncommitted changes — pull will not stash them"
        fi
        git pull --ff-only
        ok "Code at $(git rev-parse --short HEAD)"
    fi

    local version
    version="$(resolve_version)"
    log "Resolved version: ${BOLD}${version}${RESET}"
    write_version "$version"

    ensure_infra_up

    log "Building images for ${target}"
    app_compose "$target" build
    ok "Build done"

    log "Checking production security settings before startup"
    app_compose "$target" run --rm --no-deps backend python manage.py check --deploy --fail-level WARNING

    log "Bringing up ${target} stack with healthcheck wait"
    if ! app_compose "$target" up -d --wait --wait-timeout "$HEALTHCHECK_TIMEOUT"; then
        app_compose "$target" logs --tail=80
        app_compose "$target" down
        die "Healthcheck timed out for ${target} — leaving ${current_active:-nothing} active"
    fi
    ok "${target} stack healthy"

    log "Running migrations on ${target}"
    if ! docker exec "portfolio-${target}-backend" python manage.py migrate --noinput; then
        warn "Migration failed — tearing down ${target}"
        app_compose "$target" down
        die "Migration failed; rolled back to ${current_active:-no previous deployment}"
    fi
    ok "Migrations applied"

    log "Collecting static files on ${target}"
    docker exec "portfolio-${target}-backend" python manage.py collectstatic --noinput >/dev/null
    ok "Static files collected"

    if ! smoke_test_internal "$target"; then
        warn "${target} backend not responding — tearing down"
        app_compose "$target" down
        die "Internal smoke test failed; rolled back to ${current_active:-no previous deployment}"
    fi

    log "Flipping nginx to ${target}"
    set_active_colour_in_env "$target"
    if ! reload_nginx "$target" || ! smoke_test_public; then
        warn "Public smoke test failed — flipping nginx back to ${current_active:-(no previous)}"
        if [[ -n "$current_active" ]]; then
            set_active_colour_in_env "$current_active"
            reload_nginx "$current_active"
        fi
        app_compose "$target" down
        die "Public smoke test failed; rolled back"
    fi

    ok "Public traffic now served by ${target}"

    # Tear down the previously-active colour to free resources.
    if [[ -n "$current_active" ]] && [[ "$current_active" != "$target" ]]; then
        log "Tearing down old ${current_active} stack"
        app_compose "$current_active" down
        ok "Old ${current_active} stack stopped"
    fi

    write_state "$target" "$current_active" "$version"

    echo
    echo "${GREEN}${BOLD}Deployment complete${RESET}"
    echo "  active:   ${target}"
    echo "  previous: ${current_active:-<none>}"
    echo "  version:  ${version}"
    echo "  git sha:  $(git rev-parse --short HEAD)"
}

# ---------------------------------------------------------------------------
# Subcommand: rollback
# ---------------------------------------------------------------------------
cmd_rollback() {
    local active previous
    active="$(read_state active)"
    previous="$(read_state previous)"

    [[ -n "$active" ]]   || die "No active deployment — nothing to roll back from"
    [[ -n "$previous" ]] || die "No previous deployment recorded — cannot roll back"

    log "Rollback: ${active} → ${previous}"

    if ! docker ps --filter "name=portfolio-${previous}-backend" --format '{{.Names}}' | grep -q .; then
        warn "Previous ${previous} stack is not running — restarting it from existing images"
        if ! app_compose "$previous" up -d --wait --wait-timeout "$HEALTHCHECK_TIMEOUT"; then
            die "Could not restart ${previous} stack — manual intervention required"
        fi
    fi

    if ! smoke_test_internal "$previous"; then
        die "Cannot reach ${previous} backend; rollback aborted"
    fi

    log "Flipping nginx back to ${previous}"
    set_active_colour_in_env "$previous"
    if ! reload_nginx "$previous" || ! smoke_test_public; then
        warn "Rollback verification failed; restoring ${active} upstream"
        set_active_colour_in_env "$active"
        reload_nginx "$active"
        die "Rollback verification failed; deployment state retained"
    fi

    log "Tearing down failed ${active} stack"
    app_compose "$active" down

    write_state "$previous" "$active" "$(read_state version)"

    echo
    echo "${GREEN}${BOLD}Rollback complete${RESET}"
    echo "  active:   ${previous}"
    echo "  rolled-back from: ${active}"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
preflight

case "${SUBCMD:-}" in
    status)         cmd_status ;;
    rollback)       cmd_rollback ;;
    fresh)          cmd_deploy fresh ;;
    deploy)         cmd_deploy deploy ;;
    "")
        # Auto-detect: fresh if no state file, otherwise blue-green deploy.
        if [[ -f "$STATE_FILE" ]]; then cmd_deploy deploy; else cmd_deploy fresh; fi
        ;;
    *)              die "Unknown subcommand: $SUBCMD" ;;
esac
