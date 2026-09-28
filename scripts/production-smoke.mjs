import assert from "node:assert/strict";
import http from "node:http";
import https from "node:https";

const base = process.env.SMOKE_BASE_URL || "http://127.0.0.1:8080";
const host = process.env.SMOKE_HOST || new URL(base).host;

async function request(path) {
  const url = new URL(path, base);
  const client = url.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    // Native HTTP preserves the explicit Host header across Node versions.
    const req = client.get(url, { headers: { Host: host } }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("error", reject);
      response.on("end", () => {
        const headers = new Headers();
        for (const [name, value] of Object.entries(response.headers)) {
          if (value !== undefined) {
            for (const entry of Array.isArray(value) ? value : [value]) {
              headers.append(name, entry);
            }
          }
        }
        resolve(new Response(Buffer.concat(chunks), { status: response.statusCode, headers }));
      });
    });
    req.on("error", reject);
    req.setTimeout(15000, () => req.destroy(new Error(`Timeout: ${path}`)));
  });
}

for (const path of ["/healthz/", "/frontend-healthz/"]) {
  const response = await request(path);
  assert.equal(response.status, 200, `${path} must be ready`);
  assert.deepEqual(await response.json(), { ready: true });
  console.log(`PASS ${path}`);
}

for (const path of [
  "/", "/projects", "/contact", "/robots.txt", "/sitemap.xml",
  "/api/v1/profile/", "/api/v1/projects/", "/admin/login/",
  "/static/admin/css/base.css",
]) {
  const response = await request(path);
  assert.equal(response.status, 200, `${path} must respond successfully`);
  const body = await response.text();
  assert.ok(body.length > 0, `${path} must not be empty`);
  if (path === "/admin/login/") {
    assert.match(response.headers.get("set-cookie") || "", /; Secure/i);
  }
  console.log(`PASS ${path}`);
}

assert.equal((await request("/internal/demos/authorize/")).status, 404);
console.log("PASS private gate is inaccessible through the public origin");
