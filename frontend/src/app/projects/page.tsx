import type { Metadata } from "next";

import ProjectsGrid from "./ProjectsGrid";
import { fetchProjects } from "@/lib/api";

export const metadata: Metadata = {
  title: "Projects",
  description: "Explore my portfolio of software engineering projects.",
};

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const projects = await fetchProjects();

  return (
    <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-text">
          All Projects
        </h1>
        <p className="mt-3 text-text-secondary">
          A collection of my work across various domains
        </p>
        <div className="mx-auto mt-4 h-1 w-12 rounded-full bg-accent" />
      </div>
      <ProjectsGrid projects={projects} />
    </div>
  );
}
