import { describe, it, expect } from "vitest";

import { gridClassesForCount } from "./grid";

describe("gridClassesForCount", () => {
  it("returns single-column layout for 1 item", () => {
    const cls = gridClassesForCount(1);
    expect(cls).toContain("grid-cols-1");
    expect(cls).toContain("max-w-md");
    expect(cls).not.toContain("sm:grid-cols-2");
  });

  it("returns two-column layout for 2 items", () => {
    const cls = gridClassesForCount(2);
    expect(cls).toContain("sm:grid-cols-2");
    expect(cls).toContain("max-w-3xl");
    expect(cls).not.toContain("lg:grid-cols-3");
  });

  it("returns full responsive grid for 3 items", () => {
    const cls = gridClassesForCount(3);
    expect(cls).toContain("sm:grid-cols-2");
    expect(cls).toContain("lg:grid-cols-3");
    expect(cls).not.toContain("max-w-md");
    expect(cls).not.toContain("max-w-3xl");
  });

  it("uses full responsive grid for any count >= 3", () => {
    for (const n of [3, 4, 5, 7, 12]) {
      expect(gridClassesForCount(n)).toBe(gridClassesForCount(3));
    }
  });

  it("treats 0 like 1 (single column) so callers handling empty state get a sane default", () => {
    expect(gridClassesForCount(0)).toContain("grid-cols-1");
  });
});
