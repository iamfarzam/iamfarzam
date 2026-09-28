import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import test from "node:test";

const bash = process.env.TEST_BASH || (process.platform === "win32"
  ? "C:/Program Files/Git/bin/bash.exe" : "bash");

// A complete, fictional .env: the deploy pre-flight requires every value present.
const COMPLETE_ENV = [
  "ACTIVE_COLOR=blue",
  "NGINX_SERVER_NAMES=example.com",
  "DJANGO_SECRET_KEY=fictional-deploy-test-secret-0123456789abcdef0123456789",
  "DATABASE_URL=postgres://portfolio:example-password@postgres:5432/portfolio",
  "POSTGRES_PASSWORD=example-password",
  "ALLOWED_HOSTS=example.com,localhost",
  "NEXT_PUBLIC_SITE_URL=https://example.com",
  "NEXT_PUBLIC_API_URL=https://example.com/api/v1",
  "CELERY_BROKER_URL=redis://redis:6379/0",
  "",
].join("\n");

function runDeployment(failure, subcommand = "deploy", extraEnv = "", tagged = false, envFile = COMPLETE_ENV) {
  const directory = mkdtempSync(join(tmpdir(), "portfolio-deploy-test-"));
  try {
    mkdirSync(join(directory, "bin"));
    mkdirSync(join(directory, "backend"));
    copyFileSync(new URL("../deploy.sh", import.meta.url), join(directory, "deploy.sh"));
    for (const file of ["docker-compose.app.yml", "docker-compose.infra.yml"]) {
      writeFileSync(join(directory, file), "services: {}\n");
    }
    writeFileSync(join(directory, ".env"), `${envFile}${extraEnv}`);
    writeFileSync(join(directory, ".deployed.state"), "active=blue\nprevious=green\nversion=old\n");
    writeFileSync(join(directory, "bin/git"), `#!/usr/bin/env bash
case "$*" in
  *"describe --tags --abbrev=0"*) [ -n "$TEST_TAGGED" ] || exit 1 ;;
  # Report the tag as dirty, exactly as the requested --dirty marker spells it.
  *"describe"*)
    marker=""
    for arg in "$@"; do case "$arg" in --dirty=*) marker="\${arg#--dirty=}" ;; esac; done
    echo "v1.2.3\${marker}" ;;
  *"rev-list"*) echo 1 ;;
  *"rev-parse"*) echo abcdef ;;
esac
`, { mode: 0o755 });
    writeFileSync(join(directory, "bin/docker"), `#!/usr/bin/env bash
echo "$*" >> docker.calls
flipped() { grep -q '^ACTIVE_COLOR=green' .env; }
case "$TEST_FAILURE:$*" in
  security:*"check --deploy"*) exit 1 ;;
  health:*"portfolio-green up"*) exit 1 ;;
  nginx:*"nginx -t"*) flipped && exit 1 ;;
  public:*"wget"*) flipped && exit 1 ;;
  # A 301 to the real public domain must never read as a healthy candidate.
  redirect:*"wget"*) if flipped; then echo "  HTTP/1.1 301 Moved Permanently"; exit 0; fi ;;
  # A reachable private demo gate must never read as a healthy candidate.
  gate:*"wget"*"/internal/demos/authorize/"*) if flipped; then echo "  HTTP/1.1 200 OK"; exit 0; fi ;;
esac
case "$*" in
  # The gate is expected to be blocked at the public origin.
  *"wget"*"/internal/demos/authorize/"*) echo "  HTTP/1.1 404 Not Found" ;;
  *"wget"*) echo "  HTTP/1.1 200 OK" ;;
esac
exit 0
`, { mode: 0o755 });
    // Avoid real waits and external tools/services: only exercise rollout control flow.
    writeFileSync(join(directory, "bin/sleep"), "#!/usr/bin/env bash\nexit 0\n", { mode: 0o755 });
    let failed = false;
    try {
      execFileSync(bash, ["-c", `export PATH="$PWD/bin:$PATH"; bash deploy.sh ${subcommand} --no-pull`], {
        cwd: directory,
        env: { ...process.env, TEST_FAILURE: failure, TEST_TAGGED: tagged ? "1" : "" },
        stdio: "pipe",
        timeout: 30000,
      });
    } catch (error) {
      assert.equal(error.status, 1, error.stderr?.toString());
      failed = true;
    }
    assert.equal(failed, true, "deployment must fail in the injected scenario");
    return {
      env: readFileSync(join(directory, ".env"), "utf8"),
      state: readFileSync(join(directory, ".deployed.state"), "utf8"),
      calls: (() => { try { return readFileSync(join(directory, "docker.calls"), "utf8"); } catch { return ""; } })(),
      version: (() => { try { return readFileSync(join(directory, "backend/VERSION"), "utf8").trim(); } catch { return ""; } })(),
    };
  } finally {
    assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
    assert.ok(basename(directory).startsWith("portfolio-deploy-test-"));
    rmSync(directory, { recursive: true, force: true });
  }
}

test("fresh refuses to overwrite an active deployment", () => {
  const result = runDeployment("", "fresh");
  assert.match(result.state, /active=blue/);
  assert.doesNotMatch(result.calls, / up /);
});

test("security failure stops before starting the new application", () => {
  const result = runDeployment("security");
  assert.match(result.calls, /check --deploy --fail-level WARNING/);
  assert.doesNotMatch(result.calls, /portfolio-green up/);
  assert.match(result.env, /ACTIVE_COLOR=blue/);
});

test("health failure tears down only the candidate colour", () => {
  const result = runDeployment("health");
  assert.match(result.calls, /portfolio-green down/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
  assert.match(result.env, /ACTIVE_COLOR=blue/);
});

test("invalid nginx configuration restores the previous upstream", () => {
  const result = runDeployment("nginx");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.match(result.calls, /portfolio-green down/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
});

test("public smoke failure restores the previous upstream", () => {
  const result = runDeployment("public");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.match(result.calls, /portfolio-green down/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
});

test("a redirected public probe never passes as a healthy flip", () => {
  const result = runDeployment("redirect");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.match(result.calls, /portfolio-green down/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
});

test("a publicly reachable demo gate never passes as a healthy flip", () => {
  const result = runDeployment("gate");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.match(result.calls, /portfolio-green down/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
});

test("refuses to deploy when a required env value is missing", () => {
  const result = runDeployment("", "deploy", "", false, "ACTIVE_COLOR=blue\nNGINX_SERVER_NAMES=example.com\n");
  assert.doesNotMatch(result.calls, / up /);
  assert.match(result.state, /active=blue/);
});

test("refuses to deploy when the HTTPS redirect and proxy scheme disagree", () => {
  const result = runDeployment("", "deploy", "SECURE_SSL_REDIRECT=True\nNGINX_PROXY_SCHEME=auto\n");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.doesNotMatch(result.calls, / up /);
});

test("accepts a consistent HTTPS redirect and proxy scheme", () => {
  const result = runDeployment("health", "deploy", "SECURE_SSL_REDIRECT=True\nNGINX_PROXY_SCHEME=https\n");
  assert.match(result.calls, /portfolio-green up/);
});

test("a dirty checkout still stamps a SemVer version into the image", () => {
  const result = runDeployment("health", "deploy", "", true);
  // PROJECT_VERSION is asserted to be SemVer, so the marker is build metadata.
  assert.match(result.version, /^\d+\.\d+\.\d+(?:[-+].*)?$/);
  assert.match(result.version, /dirty/);
});

test("failed rollback restores the active upstream and retains deployment state", () => {
  const result = runDeployment("nginx", "rollback");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
});
