import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("frontend readiness", () => {
  it("checks Django over the private hop with the public host and HTTPS", async () => {
    vi.stubEnv("INTERNAL_API_URL", "http://portfolio-blue-backend:8000/api/v1");
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com");
    vi.stubEnv("INTERNAL_API_FORWARD_PROTO", "https");
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ready: true }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET();
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(fetchMock.mock.calls[0][0].href).toBe("http://portfolio-blue-backend:8000/healthz/");
    expect(fetchMock.mock.calls[0][1].headers).toEqual({
      "X-Forwarded-Host": "example.com",
      "X-Forwarded-Proto": "https",
    });
  });

  it.each([
    () => Promise.resolve(Response.json({ ready: false }, { status: 503 })),
    () => Promise.resolve(Response.json({ ready: false })),
    () => Promise.resolve(new Response("invalid JSON")),
    () => Promise.reject(new Error("private connection details")),
  ])("returns unavailable when the dependency is not ready", async (fetchImpl) => {
    vi.stubGlobal("fetch", vi.fn(fetchImpl));
    const response = await GET();
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ ready: false });
  });
});
