import { describe, expect, it, vi } from "vitest";

import { normalizeApiLocale, submitContact } from "./api";

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
