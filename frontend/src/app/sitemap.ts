import type { MetadataRoute } from "next";

import type { ProjectSummary } from "@/lib/types";

// Always render the sitemap per-request. With a non-zero
// NEXT_PUBLIC_REVALIDATE, the shared fetch helper otherwise turns every
// fetch into ISR-cached, which lets Next.js pre-render this route at
// build time — and at build time the backend is not yet reachable, so
// the catch below returns only the static pages, freezing a broken
// sitemap into the build output.
export const dynamic = "force-dynamic";

const API_BASE =
  process.env.INTERNAL_API_URL || "http://localhost:8000/api/v1";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    {
      url: siteUrl,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 1,
    },
    {
      url: `${siteUrl}/projects`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${siteUrl}/contact`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.5,
    },
  ];

  try {
    const res = await fetch(`${API_BASE}/projects/`, {
      headers: { "Accept-Language": "en" },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`API ${res.status} ${res.statusText}`);
    }
    const projects = (await res.json()) as ProjectSummary[];
    const projectPages: MetadataRoute.Sitemap = projects.map((project) => {
      const stamp = project.updated_at || project.created_at;
      return {
        url: `${siteUrl}/projects/${project.slug}`,
        lastModified: stamp ? new Date(stamp) : now,
        changeFrequency: "monthly" as const,
        priority: 0.7,
      };
    });
    return [...staticPages, ...projectPages];
  } catch (err) {
    console.error("[sitemap] Failed to load projects, returning static pages only:", err);
    return staticPages;
  }
}
