"use client";

import Link from "next/link";

import Card from "@/components/ui/Card";
import Section from "@/components/ui/Section";
import Button from "@/components/ui/Button";
import type { ProjectSummary } from "@/lib/types";

interface ProjectsProps {
  projects: ProjectSummary[];
}

export default function ProjectsSection({ projects }: ProjectsProps) {
  const featured = projects.filter((p) => p.is_featured);

  return (
    <Section id="projects" title="Featured Projects" subtitle="Some of my recent work">
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {featured.map((project) => (
          <Card
            key={project.slug}
            title={project.title}
            summary={project.summary}
            thumbnail={project.thumbnail}
            href={`/projects/${project.slug}`}
            technologies={project.technologies}
            githubUrl={project.github_url}
            liveUrl={project.live_url}
          />
        ))}
      </div>
      {projects.length > featured.length && (
        <div className="mt-10 text-center">
          <Button as={Link} href="/projects" variant="outline">
            View All Projects
          </Button>
        </div>
      )}
    </Section>
  );
}
