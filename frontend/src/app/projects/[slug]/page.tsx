import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { fetchProject, fetchProjects } from "@/lib/api";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  try {
    const projects = await fetchProjects();
    return projects.map((p) => ({ slug: p.slug }));
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  try {
    const project = await fetchProject(slug);
    return {
      title: project.title,
      description: project.summary,
      openGraph: {
        title: project.title,
        description: project.summary,
        images: [{ url: project.thumbnail }],
        type: "article",
      },
    };
  } catch {
    return { title: "Project" };
  }
}

export default async function ProjectDetailPage({ params }: Props) {
  const t = await getTranslations("projects");
  const { slug } = await params;
  const project = await fetchProject(slug);
  const title = project.title || "Project";
  const summary = project.summary || "";
  const technologies = project.technologies || [];
  const descriptionParagraphs = (project.description || "")
    .split("\n")
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: title,
    description: summary,
    url: `${process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"}/projects/${project.slug}`,
    dateCreated: project.created_at,
    image: project.thumbnail,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <article className="mx-auto max-w-4xl px-4 py-20 sm:px-6 lg:px-8">
        <Link
          href="/projects"
          className="mb-6 inline-flex items-center gap-1 text-sm text-text-muted transition-colors hover:text-accent"
        >
          &larr; {t("back")}
        </Link>

        <h1 className="text-4xl font-bold tracking-tight text-text">
          {title}
        </h1>
        <p className="mt-3 text-lg text-text-secondary">{summary}</p>

        {technologies.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {technologies.map((tech) => (
              <Badge key={tech.name}>{tech.name}</Badge>
            ))}
          </div>
        )}

        <div className="mt-6 flex gap-3">
          {project.github_url && (
            <Button as="a" href={project.github_url} target="_blank" rel="noopener noreferrer" variant="outline">
              {t("view_github")}
            </Button>
          )}
          {project.live_url && (
            <Button as="a" href={project.live_url} target="_blank" rel="noopener noreferrer">
              {t("live_demo")}
            </Button>
          )}
        </div>

        {(project.image || project.thumbnail) && (
          <div className="relative mt-10 aspect-video overflow-hidden rounded-xl border border-border">
            <Image
              src={project.image || project.thumbnail}
              alt={title}
              fill
              className="object-cover"
              priority
              sizes="(max-width: 896px) 100vw, 896px"
            />
          </div>
        )}

        <div className="prose prose-slate dark:prose-invert mt-10 max-w-none">
          {descriptionParagraphs.length > 0 ? (
            descriptionParagraphs.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))
          ) : (
            <p>{t("no_description")}</p>
          )}
        </div>
      </article>
    </>
  );
}
