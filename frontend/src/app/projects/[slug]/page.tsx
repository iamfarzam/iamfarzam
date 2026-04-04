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
      <article className="mx-auto max-w-5xl px-4 py-20 sm:px-6 lg:px-8">
        {/* Back link */}
        <Link
          href="/projects"
          className="mb-8 inline-flex items-center gap-2 text-sm font-medium text-text-muted transition-colors hover:text-accent"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          {t("back")}
        </Link>

        {/* Hero section */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold tracking-tight text-text sm:text-5xl">
            {title}
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-text-secondary sm:text-xl">
            {summary}
          </p>

          {technologies.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-2">
              {technologies.map((tech) => (
                <Badge key={tech.name}>{tech.name}</Badge>
              ))}
            </div>
          )}

          <div className="mt-8 flex flex-wrap gap-4">
            {project.github_url && (
              <Button as="a" href={project.github_url} target="_blank" rel="noopener noreferrer" variant="outline">
                <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
                {t("view_github")}
              </Button>
            )}
            {project.live_url && (
              <Button as="a" href={project.live_url} target="_blank" rel="noopener noreferrer">
                <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                {t("live_demo")}
              </Button>
            )}
          </div>
        </div>

        {/* Project image */}
        {(project.image || project.thumbnail) && (
          <div className="relative mb-12 aspect-video overflow-hidden rounded-2xl border border-border shadow-lg">
            <Image
              src={project.image || project.thumbnail}
              alt={title}
              fill
              className="object-cover"
              priority
              sizes="(max-width: 1024px) 100vw, 1024px"
            />
          </div>
        )}

        {/* Description */}
        <div className="mx-auto max-w-3xl">
          <div className="prose prose-lg prose-slate dark:prose-invert max-w-none prose-p:leading-relaxed prose-p:text-text-secondary">
            {descriptionParagraphs.length > 0 ? (
              descriptionParagraphs.map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))
            ) : (
              <p className="text-text-muted italic">{t("no_description")}</p>
            )}
          </div>
        </div>
      </article>
    </>
  );
}
