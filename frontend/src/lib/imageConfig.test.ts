// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("allows image optimization for the configured site and media origins", async () => {
  vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://portfolio.example.com");
  vi.stubEnv("PUBLIC_MEDIA_BASE_URL", "https://media.example.com/uploads");
  // @ts-expect-error The Next.js configuration is an untyped JavaScript module.
  const { default: config } = await import("../../next.config.mjs");
  expect(config.images.remotePatterns).toEqual(expect.arrayContaining([
    { protocol: "https", hostname: "portfolio.example.com", port: "", pathname: "/**" },
    { protocol: "https", hostname: "media.example.com", port: "", pathname: "/uploads/**" },
  ]));
});
