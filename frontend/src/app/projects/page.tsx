import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";

import ProjectsGrid from "./ProjectsGrid";
import { fetchProjects } from "@/lib/api";
import { defaultLocale, locales, type Locale } from "@/i18n/config";

export const metadata: Metadata = {
  title: "Projects",
  description: "A showcase of my engineering work.",
};

export const dynamic = "force-dynamic";

export default async function ProjectsPage() {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get("NEXT_LOCALE")?.value as Locale | undefined;
  const locale = cookieLocale && locales.includes(cookieLocale) ? cookieLocale : defaultLocale;
  const t = await getTranslations("projects");
  const projects = await fetchProjects(locale);

  return (
    <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
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
