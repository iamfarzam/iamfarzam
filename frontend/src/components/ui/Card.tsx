"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";

import Badge from "./Badge";

const MAX_TECH_BADGES = 5;

interface CardProps {
  title: string;
  summary: string;
  thumbnail?: string | null;
  href: string;
  technologies?: { name: string; icon: string }[];
  githubUrl?: string;
  liveUrl?: string;
}

export default function Card({
  title,
  summary,
  thumbnail,
  href,
  technologies = [],
  githubUrl,
  liveUrl,
}: CardProps) {
  const t = useTranslations();
  const visibleTechs = technologies.slice(0, MAX_TECH_BADGES);
  const hiddenCount = technologies.length - visibleTechs.length;
  const hasLinks = Boolean(githubUrl || liveUrl);

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4 }}
      className="group flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5"
    >
      <Link href={href} className="block">
        <div className="relative aspect-video overflow-hidden">
          {thumbnail ? (
            <Image
              src={thumbnail}
              alt={title}
              fill
              className="object-cover transition-transform duration-500 group-hover:scale-105"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            />
          ) : (
            <div className="flex h-full items-center justify-center bg-bg-tertiary text-sm text-text-muted">
              {t("projects.no_preview")}
            </div>
          )}
        </div>
      </Link>
      <div className="flex flex-1 flex-col p-5">
        <Link href={href}>
          <h3 className="line-clamp-2 text-lg font-semibold text-text transition-colors group-hover:text-accent">
            {title}
          </h3>
        </Link>
        {summary ? (
          <p className="mt-2 line-clamp-3 text-sm text-text-secondary">
            {summary}
          </p>
        ) : (
          <p className="mt-2 line-clamp-3 text-sm italic text-text-muted">
            {t("projects.no_summary")}
          </p>
        )}
        {visibleTechs.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {visibleTechs.map((tech) => (
              <Badge key={tech.name}>{tech.name}</Badge>
            ))}
            {hiddenCount > 0 && (
              <Badge>+{hiddenCount}</Badge>
            )}
          </div>
        )}
        {/* Spacer pushes the link row to the bottom regardless of summary length */}
        <div className="flex-1" />
        {hasLinks && (
          <div className="mt-4 flex flex-wrap gap-3 border-t border-border/50 pt-3">
            {githubUrl && (
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-text-muted transition-colors hover:text-accent"
              >
                {t("card.github")} &rarr;
              </a>
            )}
            {liveUrl && (
              <a
                href={liveUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-text-muted transition-colors hover:text-accent"
              >
                {t("card.live_demo")} &rarr;
              </a>
            )}
          </div>
        )}
      </div>
    </motion.article>
  );
}
