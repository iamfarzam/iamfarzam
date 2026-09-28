import { execFileSync } from "node:child_process";

// Check the index, including newly staged files and force-added ignored files.
const files = execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" }).split("\0");
const forbidden = files.filter((file) => file.startsWith("demos/") ||
  /(^|\/)\.env(?:\.|$)/.test(file) && file.split("/").at(-1) !== ".env.example");
if (forbidden.length) {
  console.error("Private files are tracked. Remove them from the index:", forbidden.join(", "));
  process.exit(1);
}
console.log("No demo workspace or private environment files are tracked.");
