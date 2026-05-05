"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import Card from "@/components/ui/Card";
import Section from "@/components/ui/Section";
import Button from "@/components/ui/Button";
import { gridClassesForCount } from "@/lib/grid";
import type { ProjectSummary } from "@/lib/types";

interface ProjectsProps {
  projects: ProjectSummary[];
}

export default function ProjectsSection({ projects }: ProjectsProps) {
  const t = useTranslations("projects");
  const featured = projects.filter((p) => p.is_featured);
  const hasMoreBeyondFeatured = projects.length > featured.length;

  return (
    <Section id="projects" title={t("title")} subtitle={t("subtitle")}>
      {featured.length > 0 ? (
        <div className={gridClassesForCount(featured.length)}>
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
      ) : (
        <p className="text-center text-sm text-text-muted">
          {t("no_featured")}
        </p>
      )}
      {hasMoreBeyondFeatured && (
        <div className="mt-10 text-center">
          <Button as={Link} href="/projects" variant="outline">
            {t("view_all")}
          </Button>
        </div>
      )}
    </Section>
  );
}
