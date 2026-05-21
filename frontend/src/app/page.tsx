import { cookies } from "next/headers";

import AboutSection from "@/components/sections/AboutSection";
import ContactSection from "@/components/sections/ContactSection";
import EducationSection from "@/components/sections/EducationSection";
import ExperienceSection from "@/components/sections/ExperienceSection";
import HeroSection from "@/components/sections/HeroSection";
import ProjectsSection from "@/components/sections/ProjectsSection";
import SkillsSection from "@/components/sections/SkillsSection";
import {
  fetchEducation,
  fetchExperience,
  fetchProfile,
  fetchProjects,
  fetchSkills,
} from "@/lib/api";
import { defaultLocale, locales, type Locale } from "@/i18n/config";
import { serializeJsonLd } from "@/lib/jsonLd";
import type { Profile } from "@/lib/types";

// cookies() + ISR-cached fetches collide and produce DYNAMIC_SERVER_USAGE;
// force per-request rendering (see /projects/[slug] for the full note).
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get("NEXT_LOCALE")?.value as Locale | undefined;
  const locale = cookieLocale && locales.includes(cookieLocale) ? cookieLocale : defaultLocale;

  const fallbackProfile: Profile = {
    full_name: "Developer",
    headline: "",
    tagline: "",
    bio: "",
    avatar: null,
    resume: null,
    email: "",
    location: "",
    github_url: "",
    linkedin_url: "",
    twitter_url: "",
    website_url: "",
    meta_title: "",
    meta_description: "",
    og_image: null,
    logo: null,
    favicon: null,
  };

  const [profileResult, skillsResult, projectsResult, experienceResult, educationResult] = await Promise.allSettled([
    fetchProfile(locale),
    fetchSkills(locale),
    fetchProjects(locale),
    fetchExperience(locale),
    fetchEducation(locale),
  ]);

  const results = { profileResult, skillsResult, projectsResult, experienceResult, educationResult };
  for (const [key, result] of Object.entries(results)) {
    if (result.status === "rejected") {
      console.error(`[HomePage] ${key} failed:`, result.reason);
    }
  }

  const profile =
    profileResult.status === "fulfilled" ? profileResult.value : fallbackProfile;
  const skills = skillsResult.status === "fulfilled" ? skillsResult.value : [];
  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  const experience =
    experienceResult.status === "fulfilled" ? experienceResult.value : [];
  const education =
    educationResult.status === "fulfilled" ? educationResult.value : [];

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

  const personLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": `${siteUrl}/#person`,
    name: profile.full_name,
    jobTitle: profile.headline,
    description: profile.bio,
    url: siteUrl,
    image: profile.avatar,
    email: profile.email || undefined,
    sameAs: [
      profile.github_url,
      profile.linkedin_url,
      profile.twitter_url,
      profile.website_url,
    ].filter(Boolean),
  };

  const websiteLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${siteUrl}/#website`,
    url: siteUrl,
    name: profile.full_name,
    description: profile.meta_description || profile.headline,
    inLanguage: "en",
    publisher: { "@id": `${siteUrl}/#person` },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(personLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(websiteLd) }}
      />
      <HeroSection profile={profile} />
      <AboutSection profile={profile} />
      <SkillsSection categories={skills} />
      <ProjectsSection projects={projects} />
      {experience.length > 0 && <ExperienceSection experience={experience} />}
      {education.length > 0 && <EducationSection education={education} />}
      <ContactSection />
    </>
  );
}
