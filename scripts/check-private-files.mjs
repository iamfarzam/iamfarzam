import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

import { containsPrivateContent } from "./privacy-rules.mjs";

// Check the index, including newly staged files and force-added ignored files.
const files = execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" }).split("\0");
const forbidden = files.filter((file) => file.startsWith("demos/") ||
  file === ".privacy-patterns.json" ||
  /(^|\/)\.env(?:\.|$)/.test(file) && file.split("/").at(-1) !== ".env.example");
if (forbidden.length) {
  console.error(`Private files are tracked (${forbidden.length}). Remove them from the index.`);
  process.exit(1);
}

let personalPatterns = [];
if (existsSync(".privacy-patterns.json")) {
  try {
    personalPatterns = JSON.parse(readFileSync(".privacy-patterns.json", "utf8"));
    if (!Array.isArray(personalPatterns) || personalPatterns.some((value) => typeof value !== "string")) {
      throw new Error();
    }
  } catch {
    console.error("Local privacy patterns are invalid; values have not been printed.");
    process.exit(1);
  }
}

let rejected = 0;
for (const file of files.filter(Boolean)) {
  // Read staged content, so unstaged edits cannot hide a staged disclosure.
  const content = execFileSync("git", ["show", `:${file}`], { maxBuffer: 16 * 1024 * 1024 });
  if (content.includes(0)) continue;
  if (containsPrivateContent(content.toString("utf8"), personalPatterns)) rejected++;
}

// Guard newly created commit identities as well as tracked file contents.
for (const variable of ["GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"]) {
  let identity;
  try {
    identity = execFileSync("git", ["var", variable], { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] });
  } catch {
    continue;
  }
  if (containsPrivateContent(identity, personalPatterns)) rejected++;
}
if (rejected) {
  console.error(`Privacy check blocked ${rejected} content or identity disclosure(s). Matched values are redacted.`);
  process.exit(1);
}
console.log("Privacy checks passed; no matched personal values or credentials were printed.");
