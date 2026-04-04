"use client";

import { useTranslations } from "next-intl";

import SocialLinks from "@/components/ui/SocialLinks";
import type { Profile } from "@/lib/types";

interface FooterProps {
  profile: Profile | null;
}

export default function Footer({ profile }: FooterProps) {
  const t = useTranslations("footer");
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-bg-secondary py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between sm:px-6 lg:px-8">
        <p className="text-sm text-text-muted">
          &copy; {year} {profile?.full_name || "Portfolio"}. {t("rights")}
        </p>
        {profile && (
          <SocialLinks
            github={profile.github_url}
            linkedin={profile.linkedin_url}
            twitter={profile.twitter_url}
            email={profile.email}
          />
        )}
      </div>
    </footer>
  );
}
