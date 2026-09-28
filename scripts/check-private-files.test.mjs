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
    writeFileSync(join(directory, "scripts/privacy-rules.mjs"), readFileSync(join(dirname(guard), "privacy-rules.mjs")));
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

test("guard rejects staged disclosures and commit identities without printing values", () => {
  const directory = mkdtempSync(join(tmpdir(), "portfolio-guard-test-"));
  try {
    const git = (...args) => execFileSync("git", args, { cwd: directory, stdio: "pipe" });
    const run = () => spawnSync(process.execPath, [guard], { cwd: directory, encoding: "utf8" });
    git("init", "-q");
    git("config", "user.name", "Repository Maintainer");
    git("config", "user.email", "maintainer@example.invalid");
    writeFileSync(join(directory, "safe.md"), "Contact: contact@example.com\n");
    git("add", "safe.md");
    assert.equal(run().status, 0);

    const privateEmail = "fictional-person@" + "mail-provider.com";
    writeFileSync(join(directory, "safe.md"), `Contact: ${privateEmail}\n`);
    git("add", "safe.md");
    writeFileSync(join(directory, "safe.md"), "Unstaged safe text\n");
    let result = run();
    assert.equal(result.status, 1);
    assert.ok(!(result.stdout + result.stderr).includes(privateEmail));

    const syntheticToken = "ghp_" + "A".repeat(36);
    writeFileSync(join(directory, "safe.md"), syntheticToken);
    git("add", "safe.md");
    result = run();
    assert.equal(result.status, 1);
    assert.ok(!(result.stdout + result.stderr).includes(syntheticToken));

    const opaqueSecret = "F".repeat(48);
    writeFileSync(join(directory, "safe.md"), "DJANGO_SECRET_KEY=" + opaqueSecret);
    git("add", "safe.md");
    result = run();
    assert.equal(result.status, 1);
    assert.ok(!(result.stdout + result.stderr).includes(opaqueSecret));

    const databasePassword = "fictional" + "PrivatePassword";
    writeFileSync(join(directory, "safe.md"), "postgres://user:" + databasePassword + "@database:5432/app");
    git("add", "safe.md");
    result = run();
    assert.equal(result.status, 1);
    assert.ok(!(result.stdout + result.stderr).includes(databasePassword));

    writeFileSync(join(directory, "safe.md"), "Safe content\n");
    git("add", "safe.md");
    git("config", "user.email", privateEmail);
    result = run();
    assert.equal(result.status, 1);
    assert.ok(!(result.stdout + result.stderr).includes(privateEmail));

    git("config", "user.email", "maintainer@example.invalid");
    const privateName = "Fictional Private Name";
    writeFileSync(join(directory, ".privacy-patterns.json"), JSON.stringify([privateName]));
    writeFileSync(join(directory, "safe.md"), privateName);
    git("add", "safe.md");
    result = run();
    assert.equal(result.status, 1);
    assert.ok(!(result.stdout + result.stderr).includes(privateName));
    git("add", ".privacy-patterns.json");
    assert.equal(run().status, 1);
  } finally {
    const target = resolve(directory);
    if (!target.startsWith(resolve(tmpdir()) + sep)) throw new Error("Unexpected test cleanup path");
    rmSync(target, { recursive: true, force: true });
  }
});
