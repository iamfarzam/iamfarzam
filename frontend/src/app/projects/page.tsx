import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";

import ProjectsGrid from "./ProjectsGrid";
import { fetchProjects } from "@/lib/api";
import { defaultLocale, locales, type Locale } from "@/i18n/config";
import { serializeJsonLd } from "@/lib/jsonLd";

// cookies() + ISR-cached fetches collide and produce DYNAMIC_SERVER_USAGE;
// force per-request rendering (see /projects/[slug] for the full note).
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Projects",
  description: "A showcase of my engineering work.",
  alternates: {
    canonical: "/projects",
  },
  openGraph: {
    title: "Projects",
    description: "A showcase of my engineering work.",
    url: "/projects",
    type: "website",
  },
};

export default async function ProjectsPage() {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get("NEXT_LOCALE")?.value as Locale | undefined;
  const locale = cookieLocale && locales.includes(cookieLocale) ? cookieLocale : defaultLocale;
  const t = await getTranslations("projects");
  const projects = await fetchProjects(locale);

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: siteUrl },
      { "@type": "ListItem", position: 2, name: "Projects", item: `${siteUrl}/projects` },
    ],
  };
  const collectionLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Projects",
    url: `${siteUrl}/projects`,
    inLanguage: "en",
    hasPart: projects.map((p) => ({
      "@type": "CreativeWork",
      name: p.title,
      url: `${siteUrl}/projects/${p.slug}`,
      image: p.thumbnail,
    })),
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(breadcrumbLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(collectionLd) }}
      />
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-text">
          {t("all_title")}
        </h1>
        <p className="mt-3 text-text-secondary">
          {t("all_subtitle")}
        </p>
        <div className="mx-auto mt-4 h-1 w-12 rounded-full bg-accent" />
      </div>
      <ProjectsGrid projects={projects} />
    </div>
  );
}
