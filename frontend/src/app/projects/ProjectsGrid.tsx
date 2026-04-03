"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";

import Card from "@/components/ui/Card";
import type { ProjectSummary } from "@/lib/types";

interface ProjectsGridProps {
  projects: ProjectSummary[];
}

export default function ProjectsGrid({ projects }: ProjectsGridProps) {
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    projects.forEach((p) =>
      (p.technologies || []).forEach((t) => tags.add(t.name))
    );
    return Array.from(tags).sort();
  }, [projects]);

  const filtered = activeTag
    ? projects.filter((p) =>
        (p.technologies || []).some((t) => t.name === activeTag)
      )
    : projects;

  return (
    <>
      {/* Tag filter */}
      <div className="mb-8 flex flex-wrap justify-center gap-2">
        <button
          onClick={() => setActiveTag(null)}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
            !activeTag
              ? "bg-accent text-white"
              : "bg-bg-tertiary text-text-secondary hover:text-accent"
          }`}
        >
          All
        </button>
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
              activeTag === tag
                ? "bg-accent text-white"
                : "bg-bg-tertiary text-text-secondary hover:text-accent"
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {/* Grid */}
      <motion.div layout className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence mode="popLayout">
          {filtered.map((project) => (
            <Card
              key={project.slug}
              title={project.title}
              summary={project.summary}
              thumbnail={project.thumbnail}
              href={`/projects/${project.slug}`}
              technologies={project.technologies || []}
              githubUrl={project.github_url}
              liveUrl={project.live_url}
            />
          ))}
        </AnimatePresence>
      </motion.div>

      {filtered.length === 0 && (
        <p className="mt-12 text-center text-text-muted">
          No projects match the selected filter.
        </p>
      )}
    </>
  );
}
