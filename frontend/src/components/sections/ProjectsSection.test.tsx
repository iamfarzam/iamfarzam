import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import ProjectsSection from "./ProjectsSection";
import type { ProjectSummary } from "@/lib/types";

function makeProject(overrides: Partial<ProjectSummary> = {}): ProjectSummary {
  return {
    title: "Sample",
    slug: "sample",
    summary: "A summary.",
    thumbnail: null,
    technologies: [],
    github_url: "",
    live_url: "",
    is_featured: true,
    ...overrides,
  } as ProjectSummary;
}

describe("ProjectsSection", () => {
  it("renders the empty-state message when no projects are featured", () => {
    render(<ProjectsSection projects={[]} />);
    expect(screen.getByText("projects.no_featured")).toBeInTheDocument();
    expect(screen.queryByText("projects.view_all")).not.toBeInTheDocument();
  });

  it("renders empty-state and 'View all' button when there are projects but none featured", () => {
    render(
      <ProjectsSection
        projects={[
          makeProject({ slug: "a", is_featured: false }),
          makeProject({ slug: "b", is_featured: false }),
        ]}
      />,
    );
    expect(screen.getByText("projects.no_featured")).toBeInTheDocument();
    expect(screen.getByText("projects.view_all")).toBeInTheDocument();
  });

  it("renders single featured project in a max-w-md single column", () => {
    const { container } = render(
      <ProjectsSection projects={[makeProject({ slug: "only" })]} />,
    );
    const grid = container.querySelector(".grid");
    expect(grid?.className).toContain("grid-cols-1");
    expect(grid?.className).toContain("max-w-md");
    expect(grid?.className).not.toContain("sm:grid-cols-2");
  });

  it("renders 2 featured projects in a 2-column max-w-3xl grid", () => {
    const { container } = render(
      <ProjectsSection
        projects={[makeProject({ slug: "a" }), makeProject({ slug: "b" })]}
      />,
    );
    const grid = container.querySelector(".grid");
    expect(grid?.className).toContain("sm:grid-cols-2");
    expect(grid?.className).toContain("max-w-3xl");
    expect(grid?.className).not.toContain("lg:grid-cols-3");
  });

  it("uses the full responsive grid for 3+ featured projects", () => {
    const { container } = render(
      <ProjectsSection
        projects={[
          makeProject({ slug: "a" }),
          makeProject({ slug: "b" }),
          makeProject({ slug: "c" }),
          makeProject({ slug: "d" }),
        ]}
      />,
    );
    const grid = container.querySelector(".grid");
    expect(grid?.className).toContain("sm:grid-cols-2");
    expect(grid?.className).toContain("lg:grid-cols-3");
    expect(grid?.className).not.toContain("max-w-md");
  });

  it("hides 'View all' when every project is featured", () => {
    render(
      <ProjectsSection
        projects={[
          makeProject({ slug: "a" }),
          makeProject({ slug: "b" }),
        ]}
      />,
    );
    expect(screen.queryByText("projects.view_all")).not.toBeInTheDocument();
  });

  it("shows 'View all' when there are projects beyond the featured ones", () => {
    render(
      <ProjectsSection
        projects={[
          makeProject({ slug: "a", is_featured: true }),
          makeProject({ slug: "b", is_featured: false }),
        ]}
      />,
    );
    expect(screen.getByText("projects.view_all")).toBeInTheDocument();
  });
});
