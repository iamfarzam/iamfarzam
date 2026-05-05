import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import SkillsSection from "./SkillsSection";
import type { SkillCategory } from "@/lib/types";

function makeCategory(overrides: Partial<SkillCategory> = {}): SkillCategory {
  return {
    id: 1,
    name: "Backend",
    skills: [{ id: 11, name: "Python", icon: "", proficiency: 90 }],
    ...overrides,
  } as SkillCategory;
}

describe("SkillsSection", () => {
  it("renders the empty-state message when there are no categories", () => {
    render(<SkillsSection categories={[]} />);
    expect(screen.getByText("skills.no_skills")).toBeInTheDocument();
  });

  it("renders single category in a single-column layout", () => {
    const { container } = render(<SkillsSection categories={[makeCategory()]} />);
    const grid = container.querySelector(".grid");
    expect(grid?.className).toContain("grid-cols-1");
    expect(grid?.className).toContain("max-w-md");
  });

  it("renders 2 categories in a 2-column max-w-3xl grid", () => {
    const { container } = render(
      <SkillsSection
        categories={[makeCategory({ id: 1 }), makeCategory({ id: 2, name: "ML" })]}
      />,
    );
    const grid = container.querySelector(".grid");
    expect(grid?.className).toContain("sm:grid-cols-2");
    expect(grid?.className).toContain("max-w-3xl");
  });

  it("renders 3+ categories in the full responsive grid", () => {
    const cats = Array.from({ length: 4 }, (_, i) =>
      makeCategory({ id: i + 1, name: `Cat${i}` }),
    );
    const { container } = render(<SkillsSection categories={cats} />);
    const grid = container.querySelector(".grid");
    expect(grid?.className).toContain("lg:grid-cols-3");
  });

  it("renders an empty-category message when a category has no skills", () => {
    render(
      <SkillsSection
        categories={[makeCategory({ id: 1, name: "DevOps", skills: [] })]}
      />,
    );
    expect(screen.getByText("skills.no_skills_in_category")).toBeInTheDocument();
  });

  it("renders skills as badges without proficiency percentages", () => {
    render(
      <SkillsSection
        categories={[
          makeCategory({
            id: 1,
            skills: [
              { id: 1, name: "Python", icon: "", proficiency: 80 },
              { id: 2, name: "Rust", icon: "", proficiency: 60 },
            ],
          }),
        ]}
      />,
    );
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Rust")).toBeInTheDocument();
    // Percentages must NOT appear — modern portfolios don't quantify skills.
    expect(screen.queryByText("80%")).not.toBeInTheDocument();
    expect(screen.queryByText("60%")).not.toBeInTheDocument();
    expect(screen.queryAllByRole("progressbar")).toHaveLength(0);
  });

  it("category cards use h-full so heights line up", () => {
    const { container } = render(
      <SkillsSection
        categories={[
          makeCategory({ id: 1, skills: [] }),
          makeCategory({
            id: 2,
            skills: Array.from({ length: 8 }, (_, i) => ({
              id: i + 1,
              name: `S${i}`,
              icon: "",
              proficiency: 50,
            })),
          }),
        ]}
      />,
    );
    const cards = container.querySelectorAll(".rounded-xl");
    cards.forEach((card) => {
      expect(card.className).toContain("h-full");
    });
  });
});
