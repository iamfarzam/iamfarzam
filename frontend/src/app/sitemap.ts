import type { MetadataRoute } from "next";

import { fetchProjects } from "@/lib/api";

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
    const projects = await fetchProjects();
    const projectPages: MetadataRoute.Sitemap = projects.map((project) => ({
      url: `${siteUrl}/projects/${project.slug}`,
      lastModified: project.created_at ? new Date(project.created_at) : now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    }));
    return [...staticPages, ...projectPages];
  } catch {
    return staticPages;
  }
}
