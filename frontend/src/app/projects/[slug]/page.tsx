import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { fetchProject, fetchProjects } from "@/lib/api";

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
  const { slug } = await params;
  const project = await fetchProject(slug);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: project.title,
    description: project.summary,
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
          &larr; Back to Projects
        </Link>

        <h1 className="text-4xl font-bold tracking-tight text-text">
          {project.title}
        </h1>
        <p className="mt-3 text-lg text-text-secondary">{project.summary}</p>

        {project.technologies.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {project.technologies.map((tech) => (
              <Badge key={tech.name}>{tech.name}</Badge>
            ))}
          </div>
        )}

        <div className="mt-6 flex gap-3">
          {project.github_url && (
            <Button as="a" href={project.github_url} target="_blank" rel="noopener noreferrer" variant="outline">
              View on GitHub
            </Button>
          )}
          {project.live_url && (
            <Button as="a" href={project.live_url} target="_blank" rel="noopener noreferrer">
              Live Demo
            </Button>
          )}
        </div>

        {(project.image || project.thumbnail) && (
          <div className="relative mt-10 aspect-video overflow-hidden rounded-xl border border-border">
            <Image
              src={project.image || project.thumbnail}
              alt={project.title}
              fill
              className="object-cover"
              priority
              sizes="(max-width: 896px) 100vw, 896px"
            />
          </div>
        )}

        <div className="prose prose-slate dark:prose-invert mt-10 max-w-none">
          {project.description.split("\n").map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>
      </article>
    </>
  );
}
