import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchProjects, normalizeApiLocale, submitContact } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("internal API HTTPS forwarding", () => {
  it("preserves HTTPS for server fetches through the configured private HTTP hop", async () => {
    vi.stubEnv("INTERNAL_API_URL", "http://backend:8000/api/v1");
    vi.stubEnv("INTERNAL_API_FORWARD_PROTO", "https");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await fetchProjects();
    expect(fetchMock.mock.calls[0][1].headers["X-Forwarded-Proto"]).toBe("https");
  });

  it("does not assert HTTPS when private forwarding is unconfigured", async () => {
    vi.stubEnv("INTERNAL_API_FORWARD_PROTO", "");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await fetchProjects();
    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty("X-Forwarded-Proto");
  });
});

describe("normalizeApiLocale", () => {
  it("maps frontend locale codes to backend language choices", () => {
    expect(normalizeApiLocale("zh")).toBe("zh-hans");
    expect(normalizeApiLocale("fa")).toBe("fa");
  });
});

describe("submitContact", () => {
  it("normalizes the submitted contact language", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await submitContact({
      name: "A",
      email: "a@example.test",
      subject: "S",
      message: "M",
      language: "zh",
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body)).toMatchObject({ language: "zh-hans" });

    vi.unstubAllGlobals();
  });
});
