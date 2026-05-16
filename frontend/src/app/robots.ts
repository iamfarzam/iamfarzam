import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

  const allow = [
    "/$",
    "/projects$",
    "/projects/",
    "/contact$",
    "/_next/static/",
    "/_next/image",
    "/favicon.ico",
    "/sitemap.xml",
    "/robots.txt",
  ];

  return {
    rules: [
      {
        userAgent: "*",
        allow,
        disallow: "/",
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
    host: siteUrl,
  };
}
