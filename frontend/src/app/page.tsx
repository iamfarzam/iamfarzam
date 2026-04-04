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
import type { Profile } from "@/lib/types";

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
  };

  const [profileResult, skillsResult, projectsResult, experienceResult, educationResult] = await Promise.allSettled([
    fetchProfile(locale),
    fetchSkills(locale),
    fetchProjects(locale),
    fetchExperience(locale),
    fetchEducation(locale),
  ]);

  const profile =
    profileResult.status === "fulfilled" ? profileResult.value : fallbackProfile;
  const skills = skillsResult.status === "fulfilled" ? skillsResult.value : [];
  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  const experience =
    experienceResult.status === "fulfilled" ? experienceResult.value : [];
  const education =
    educationResult.status === "fulfilled" ? educationResult.value : [];

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: profile.full_name,
    jobTitle: profile.headline,
    description: profile.bio,
    url: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
    image: profile.avatar,
    email: profile.email,
    sameAs: [
      profile.github_url,
      profile.linkedin_url,
      profile.twitter_url,
    ].filter(Boolean),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
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
