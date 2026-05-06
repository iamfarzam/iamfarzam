import { describe, expect, it } from "vitest";

import { serializeJsonLd } from "./jsonLd";

describe("serializeJsonLd", () => {
  it("escapes characters that can break out of a script tag", () => {
    const serialized = serializeJsonLd({
      name: "</script><script>alert('xss')</script>",
      description: "A & B",
    });

    expect(serialized).not.toContain("</script>");
    expect(serialized).not.toContain("<script>");
    expect(serialized).toContain("\\u003c/script\\u003e");
    expect(serialized).toContain("\\u0026");
  });
});
