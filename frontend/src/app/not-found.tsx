"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import Button from "@/components/ui/Button";

export default function NotFound() {
  const t = useTranslations("not_found");
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <h1 className="text-8xl font-bold text-accent">{t("code")}</h1>
      <h2 className="mt-4 text-2xl font-semibold text-text">{t("title")}</h2>
      <p className="mt-2 text-text-secondary">
        {t("description")}
      </p>
      <Button as={Link} href="/" className="mt-8">
        {t("go_home")}
      </Button>
    </div>
  );
}
