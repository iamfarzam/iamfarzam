import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import test from "node:test";

const guard = join(dirname(fileURLToPath(import.meta.url)), "check-private-files.mjs");

test("guard permits examples and rejects force-added demo content and private env files", () => {
  const directory = mkdtempSync(join(tmpdir(), "portfolio-guard-test-"));
  try {
    const git = (...args) => execFileSync("git", args, { cwd: directory, stdio: "pipe" });
    git("init", "-q");
    git("config", "user.name", "Fictional Test");
    git("config", "user.email", "test@example.test");
    mkdirSync(join(directory, "scripts"));
    writeFileSync(join(directory, "scripts/check-private-files.mjs"), readFileSync(guard));
    mkdirSync(join(directory, ".githooks"));
    writeFileSync(join(directory, ".githooks/pre-commit"),
      readFileSync(join(dirname(guard), "../.githooks/pre-commit")), { mode: 0o755 });
    git("config", "core.hooksPath", ".githooks");
    writeFileSync(join(directory, ".env.example"), "PLACEHOLDER=example\n");
    git("add", ".env.example");
    const run = () => spawnSync(process.execPath, [guard], { cwd: directory, encoding: "utf8" });
    assert.equal(run().status, 0);
    git("commit", "--no-gpg-sign", "-m", "Fictional example fixture");
    mkdirSync(join(directory, "demos"));
    writeFileSync(join(directory, ".gitignore"), "/demos/\n");
    writeFileSync(join(directory, "demos", "fictional.txt"), "Fictional guard test data only.\n");
    git("add", "-f", "demos/fictional.txt");
    assert.equal(run().status, 1);
    const rejectedCommit = spawnSync("git", ["commit", "--no-gpg-sign", "-m", "Rejected fictional demo"], {
      cwd: directory, encoding: "utf8",
    });
    assert.notEqual(rejectedCommit.status, 0);
    assert.match(rejectedCommit.stderr, /Private files are tracked/);
    git("rm", "--cached", "demos/fictional.txt");
    writeFileSync(join(directory, ".env.staging"), "PLACEHOLDER=fictional\n");
    git("add", ".env.staging");
    assert.equal(run().status, 1);
  } finally {
    const target = resolve(directory);
    if (!target.startsWith(resolve(tmpdir()) + sep)) throw new Error("Unexpected test cleanup path");
    rmSync(target, { recursive: true, force: true });
  }
});
