#!/usr/bin/env bash
#
# Production deployment script for the portfolio stack.
#
# Single entrypoint that handles both fresh and incremental deployments:
#   - Resolves a SemVer version from git (newest tag, optionally with commit
#     hash and dirty marker) and writes it to backend/VERSION so the admin
#     panel chip reflects what's running.
#   - Pulls latest code (renew mode) or assumes the working tree is current
#     (fresh mode).
#   - Builds images, applies migrations, collects static files, then brings
#     services up with docker compose.
#
# Usage:
#   ./deploy.sh                  # auto-detect: renew if .deployed marker exists, else fresh
#   ./deploy.sh fresh            # force a fresh deploy (no `git pull`, prompts for confirmation)
#   ./deploy.sh renew            # force renew: `git pull` then rebuild
#   ./deploy.sh --version v1.2.3 # override the auto-resolved version
#   ./deploy.sh --no-pull        # skip `git pull` even in renew mode
#   ./deploy.sh --help
#
# Requirements: docker, docker compose v2, git. Run from the repository root.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COMPOSE_FILE="docker-compose.prod.yml"
VERSION_FILE="backend/VERSION"
DEPLOY_MARKER=".deployed"
ENV_FILE=".env"
SERVICES_TO_BUILD=("backend" "celery" "frontend")

# Colors (dim if not a TTY)
if [[ -t 1 ]]; then
    BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; CYAN=$'\033[36m'; RESET=$'\033[0m'
else
    BOLD=""; GREEN=""; YELLOW=""; RED=""; CYAN=""; RESET=""
fi

log()    { echo "${CYAN}==>${RESET} ${BOLD}$*${RESET}"; }
ok()     { echo "${GREEN}✓${RESET} $*"; }
warn()   { echo "${YELLOW}!${RESET} $*"; }
die()    { echo "${RED}✗${RESET} $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------
MODE=""
VERSION_OVERRIDE=""
SKIP_PULL=false

usage() {
    sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        fresh|renew) MODE="$1"; shift ;;
        --version) VERSION_OVERRIDE="${2:-}"; shift 2 ;;
        --no-pull) SKIP_PULL=true; shift ;;
        -h|--help) usage ;;
        *) die "Unknown argument: $1 (use --help)";;
    esac
done

if [[ -z "$MODE" ]]; then
    if [[ -f "$DEPLOY_MARKER" ]]; then MODE="renew"; else MODE="fresh"; fi
    log "Auto-detected mode: ${BOLD}${MODE}${RESET}"
fi

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
log "Pre-flight checks"

command -v docker >/dev/null 2>&1 || die "docker not found in PATH"
docker compose version >/dev/null 2>&1 || die "docker compose v2 plugin not available"
command -v git >/dev/null 2>&1 || die "git not found in PATH"

[[ -f "$COMPOSE_FILE" ]] || die "$COMPOSE_FILE missing — run from the repo root"
[[ -f "$ENV_FILE" ]] || die "$ENV_FILE missing — copy .env.example and fill in secrets first"
git rev-parse --git-dir >/dev/null 2>&1 || die "Not inside a git repository"

ok "Tooling and config present"

# ---------------------------------------------------------------------------
# Renew: pull latest code first, before resolving version from git
# ---------------------------------------------------------------------------
if [[ "$MODE" == "renew" ]] && [[ "$SKIP_PULL" == false ]]; then
    log "Pulling latest code"
    if ! git diff-index --quiet HEAD --; then
        warn "Working tree has uncommitted changes — pulling will not stash them"
    fi
    git pull --ff-only
    ok "Code updated to $(git rev-parse --short HEAD)"
fi

# ---------------------------------------------------------------------------
# Resolve SemVer version from git
# ---------------------------------------------------------------------------
resolve_version() {
    if [[ -n "$VERSION_OVERRIDE" ]]; then
        echo "$VERSION_OVERRIDE"
        return
    fi
    # Newest annotated/lightweight tag, plus commit count + short sha + dirty marker.
    # Examples:
    #   1.2.3                  (commit IS the tag, clean tree)
    #   1.2.3-4-g5a6b7c8       (4 commits past tag 1.2.3, sha 5a6b7c8)
    #   1.2.3-4-g5a6b7c8.dirty (same, with uncommitted changes)
    if git describe --tags --abbrev=0 >/dev/null 2>&1; then
        local desc
        desc="$(git describe --tags --always --dirty=.dirty 2>/dev/null)"
        # Strip a leading "v" so the chip shows e.g. "v1.2.3" not "vv1.2.3"
        echo "${desc#v}"
    else
        # No tags yet — fall back to commit count + short sha
        local count sha dirty=""
        count="$(git rev-list --count HEAD)"
        sha="$(git rev-parse --short HEAD)"
        if ! git diff-index --quiet HEAD --; then dirty=".dirty"; fi
        echo "0.0.0+${count}.g${sha}${dirty}"
    fi
}

NEW_VERSION="$(resolve_version)"
log "Version resolved to ${BOLD}${NEW_VERSION}${RESET}"

if [[ -f "$VERSION_FILE" ]]; then
    OLD_VERSION="$(<"$VERSION_FILE")"
    if [[ "$OLD_VERSION" != "$NEW_VERSION" ]]; then
        log "Updating ${VERSION_FILE}: ${OLD_VERSION} → ${NEW_VERSION}"
    fi
fi
echo "$NEW_VERSION" > "$VERSION_FILE"
ok "Wrote ${VERSION_FILE}"

# ---------------------------------------------------------------------------
# Confirm fresh deployments (destructive on volumes if you've messed with them)
# ---------------------------------------------------------------------------
if [[ "$MODE" == "fresh" ]] && [[ -t 0 ]]; then
    if ! "${FORCE_YES:-false}" >/dev/null 2>&1; then  # always false; keeps shellcheck quiet
        :
    fi
    echo
    warn "Fresh deploy will build all images and bring the stack up from scratch."
    warn "Existing data volumes (postgres, media) will NOT be deleted."
    read -r -p "Continue? [y/N] " ans
    [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]] || die "Aborted by user"
fi

# ---------------------------------------------------------------------------
# Build images
# ---------------------------------------------------------------------------
log "Building images: ${SERVICES_TO_BUILD[*]}"
docker compose -f "$COMPOSE_FILE" build "${SERVICES_TO_BUILD[@]}"
ok "Images built"

# ---------------------------------------------------------------------------
# Bring up infrastructure first so migrations have something to talk to
# ---------------------------------------------------------------------------
log "Starting infrastructure (postgres, redis)"
docker compose -f "$COMPOSE_FILE" up -d postgres redis

log "Waiting for postgres to be healthy"
for _ in $(seq 1 60); do
    if docker compose -f "$COMPOSE_FILE" ps postgres --format json 2>/dev/null \
         | grep -q '"Health":"healthy"'; then
        ok "Postgres is healthy"
        break
    fi
    sleep 1
done

# ---------------------------------------------------------------------------
# Run Django management commands inside a one-shot container
# ---------------------------------------------------------------------------
run_django() {
    docker compose -f "$COMPOSE_FILE" run --rm --no-deps backend python manage.py "$@"
}

log "Applying migrations"
run_django migrate --noinput
ok "Migrations applied"

log "Collecting static files"
run_django collectstatic --noinput
ok "Static files collected"

# ---------------------------------------------------------------------------
# Bring everything up (or restart it for renew)
# ---------------------------------------------------------------------------
log "Bringing up application services"
docker compose -f "$COMPOSE_FILE" up -d
ok "Services up"

log "Reloading nginx (if present)"
if docker compose -f "$COMPOSE_FILE" ps --services 2>/dev/null | grep -qx nginx; then
    docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload 2>/dev/null \
        && ok "nginx reloaded" \
        || warn "nginx reload failed (or not running yet — `docker compose up` will have started it)"
fi

# ---------------------------------------------------------------------------
# Mark this directory as having been deployed at least once
# ---------------------------------------------------------------------------
{
    echo "version=${NEW_VERSION}"
    echo "deployed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "git_sha=$(git rev-parse HEAD)"
    echo "mode=${MODE}"
} > "$DEPLOY_MARKER"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "${GREEN}${BOLD}Deployment complete${RESET}"
echo "  mode:    ${MODE}"
echo "  version: ${NEW_VERSION}"
echo "  git sha: $(git rev-parse --short HEAD)"
echo
docker compose -f "$COMPOSE_FILE" ps
