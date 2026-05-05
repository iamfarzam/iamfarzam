import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import ExperienceSection from "./ExperienceSection";
import type { Experience } from "@/lib/types";

function makeExperience(overrides: Partial<Experience> = {}): Experience {
  return {
    id: 1,
    company: "Acme",
    role: "Engineer",
    location: "",
    start_date: "2020-01-01",
    end_date: "2023-01-01",
    description: "Did things",
    company_url: "",
    company_logo: "",
    ...overrides,
  } as Experience;
}

describe("ExperienceSection", () => {
  it("renders the timeline line only when there are 2+ items", () => {
    const { container, rerender } = render(
      <ExperienceSection experience={[makeExperience({ id: 1 })]} />,
    );
    // 1 item → no central line
    expect(container.querySelector(".w-px")).toBeNull();

    rerender(
      <ExperienceSection
        experience={[makeExperience({ id: 1 }), makeExperience({ id: 2 })]}
      />,
    );
    expect(container.querySelector(".w-px")).not.toBeNull();
  });

  it("formats end_date as 'Present' translation key when null", () => {
    render(
      <ExperienceSection
        experience={[makeExperience({ id: 1, end_date: null })]}
      />,
    );
    // The key resolver echoes "experience.present" (namespace.key)
    expect(screen.getByText(/experience\.present/)).toBeInTheDocument();
  });

  it("renders company as link when company_url is provided", () => {
    render(
      <ExperienceSection
        experience={[
          makeExperience({ id: 1, company_url: "https://acme.test", company: "Acme" }),
        ]}
      />,
    );
    const link = screen.getByText("Acme");
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "https://acme.test");
  });

  it("renders company as plain text when no company_url", () => {
    render(
      <ExperienceSection
        experience={[makeExperience({ id: 1, company: "Acme", company_url: "" })]}
      />,
    );
    const company = screen.getByText("Acme");
    expect(company.tagName).not.toBe("A");
  });

  it("does not render description block when description is empty", () => {
    render(
      <ExperienceSection
        experience={[makeExperience({ id: 1, description: "" })]}
      />,
    );
    expect(screen.queryByText("Did things")).not.toBeInTheDocument();
  });

  it("renders all items regardless of count", () => {
    const items = Array.from({ length: 6 }, (_, i) =>
      makeExperience({ id: i + 1, role: `Role${i}` }),
    );
    render(<ExperienceSection experience={items} />);
    items.forEach((it) => {
      expect(screen.getByText(it.role)).toBeInTheDocument();
    });
  });

  it("renders timeline dots without inline-style hacks", () => {
    const { container } = render(
      <ExperienceSection
        experience={[makeExperience({ id: 1 }), makeExperience({ id: 2 })]}
      />,
    );
    // The dots have a rounded-full + border-accent class signature
    const dots = container.querySelectorAll(".rounded-full.border-2.border-accent");
    expect(dots.length).toBe(2);
    // Confirm we're not relying on `style="left: undefined; ..."` strings
    dots.forEach((dot) => {
      const style = (dot as HTMLElement).getAttribute("style") || "";
      expect(style).not.toContain("undefined");
    });
  });
});
