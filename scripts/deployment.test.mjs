import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import test from "node:test";

const bash = process.env.TEST_BASH || (process.platform === "win32"
  ? "C:/Program Files/Git/bin/bash.exe" : "bash");

function runDeployment(failure, subcommand = "deploy") {
  const directory = mkdtempSync(join(tmpdir(), "portfolio-deploy-test-"));
  try {
    mkdirSync(join(directory, "bin"));
    mkdirSync(join(directory, "backend"));
    copyFileSync(new URL("../deploy.sh", import.meta.url), join(directory, "deploy.sh"));
    for (const file of ["docker-compose.app.yml", "docker-compose.infra.yml"]) {
      writeFileSync(join(directory, file), "services: {}\n");
    }
    writeFileSync(join(directory, ".env"), "ACTIVE_COLOR=blue\nNGINX_SERVER_NAMES=example.com\n");
    writeFileSync(join(directory, ".deployed.state"), "active=blue\nprevious=green\nversion=old\n");
    writeFileSync(join(directory, "bin/git"), `#!/usr/bin/env bash
case "$*" in
  *"describe"*) exit 1 ;;
  *"rev-list"*) echo 1 ;;
  *"rev-parse"*) echo abcdef ;;
esac
`, { mode: 0o755 });
    writeFileSync(join(directory, "bin/docker"), `#!/usr/bin/env bash
echo "$*" >> docker.calls
case "$TEST_FAILURE:$*" in
  security:*"check --deploy"*) exit 1 ;;
  health:*"portfolio-green up"*) exit 1 ;;
  nginx:*"nginx -t"*) grep -q '^ACTIVE_COLOR=green' .env && exit 1 ;;
  public:*"wget"*) grep -q '^ACTIVE_COLOR=green' .env && exit 1 ;;
esac
exit 0
`, { mode: 0o755 });
    // Avoid real waits and external tools/services: only exercise rollout control flow.
    writeFileSync(join(directory, "bin/sleep"), "#!/usr/bin/env bash\nexit 0\n", { mode: 0o755 });
    let failed = false;
    try {
      execFileSync(bash, ["-c", `export PATH="$PWD/bin:$PATH"; bash deploy.sh ${subcommand} --no-pull`], {
        cwd: directory,
        env: { ...process.env, TEST_FAILURE: failure },
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

test("failed rollback restores the active upstream and retains deployment state", () => {
  const result = runDeployment("nginx", "rollback");
  assert.match(result.env, /ACTIVE_COLOR=blue/);
  assert.match(result.state, /active=blue/);
  assert.doesNotMatch(result.calls, /portfolio-blue down/);
});
