import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import Card from "./Card";

const baseProps = {
  title: "Test project",
  summary: "A short summary.",
  href: "/projects/test",
};

describe("Card", () => {
  it("renders title, summary, and link", () => {
    render(<Card {...baseProps} />);
    expect(screen.getByText("Test project")).toBeInTheDocument();
    expect(screen.getByText("A short summary.")).toBeInTheDocument();
  });

  it("shows a fallback for missing summary", () => {
    render(<Card {...baseProps} summary="" />);
    expect(screen.getByText("projects.no_summary")).toBeInTheDocument();
  });

  it("shows a no-preview placeholder when thumbnail is missing", () => {
    render(<Card {...baseProps} thumbnail={null} />);
    expect(screen.getByText("projects.no_preview")).toBeInTheDocument();
  });

  it("renders an Image when thumbnail is provided", () => {
    render(<Card {...baseProps} thumbnail="/img.png" />);
    expect(screen.queryByText("projects.no_preview")).not.toBeInTheDocument();
    const imgs = screen.getAllByRole("img");
    expect(imgs.length).toBeGreaterThan(0);
  });

  it("hides the link row when neither GitHub nor live URL is set", () => {
    const { container } = render(<Card {...baseProps} />);
    expect(screen.queryByText(/card\.github/)).not.toBeInTheDocument();
    expect(screen.queryByText(/card\.live_demo/)).not.toBeInTheDocument();
    // The dedicated link row has the border-t separator class — confirm it's absent
    expect(container.querySelector(".border-t")).toBeNull();
  });

  it("renders only the GitHub link when only github_url is provided", () => {
    render(<Card {...baseProps} githubUrl="https://github.com/x/y" />);
    expect(screen.getByText(/card\.github/)).toBeInTheDocument();
    expect(screen.queryByText(/card\.live_demo/)).not.toBeInTheDocument();
  });

  it("renders only the live link when only live_url is provided", () => {
    render(<Card {...baseProps} liveUrl="https://example.com" />);
    expect(screen.queryByText(/card\.github/)).not.toBeInTheDocument();
    expect(screen.getByText(/card\.live_demo/)).toBeInTheDocument();
  });

  it("renders both links when both URLs are provided", () => {
    render(
      <Card
        {...baseProps}
        githubUrl="https://github.com/x/y"
        liveUrl="https://example.com"
      />,
    );
    expect(screen.getByText(/card\.github/)).toBeInTheDocument();
    expect(screen.getByText(/card\.live_demo/)).toBeInTheDocument();
  });

  it("caps visible technology badges and shows an overflow indicator", () => {
    const techs = Array.from({ length: 9 }, (_, i) => ({
      name: `Tech${i + 1}`,
      icon: "",
    }));
    render(<Card {...baseProps} technologies={techs} />);
    // First 5 visible
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByText(`Tech${i}`)).toBeInTheDocument();
    }
    // 6+ hidden behind a "+N" badge
    expect(screen.queryByText("Tech6")).not.toBeInTheDocument();
    expect(screen.getByText("+4")).toBeInTheDocument();
  });

  it("renders all techs without overflow indicator when count <= cap", () => {
    const techs = [
      { name: "A", icon: "" },
      { name: "B", icon: "" },
    ];
    render(<Card {...baseProps} technologies={techs} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
  });

  it("uses h-full + flex-col so cards line up to row height in a grid", () => {
    const { container } = render(<Card {...baseProps} />);
    const article = container.querySelector("article");
    expect(article?.className).toContain("h-full");
    expect(article?.className).toContain("flex-col");
  });
});
