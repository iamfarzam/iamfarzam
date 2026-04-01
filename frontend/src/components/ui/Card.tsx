"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";

import Badge from "./Badge";

interface CardProps {
  title: string;
  summary: string;
  thumbnail: string;
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
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4 }}
      className="group overflow-hidden rounded-xl border border-border bg-card transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5"
    >
      <Link href={href} className="block">
        <div className="relative aspect-video overflow-hidden">
          <Image
            src={thumbnail}
            alt={title}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        </div>
      </Link>
      <div className="p-5">
        <Link href={href}>
          <h3 className="text-lg font-semibold text-text transition-colors group-hover:text-accent">
            {title}
          </h3>
        </Link>
        <p className="mt-2 line-clamp-2 text-sm text-text-secondary">
          {summary}
        </p>
        {technologies.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {technologies.map((tech) => (
              <Badge key={tech.name}>{tech.name}</Badge>
            ))}
          </div>
        )}
        <div className="mt-4 flex gap-3">
          {githubUrl && (
            <a
              href={githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-text-muted transition-colors hover:text-accent"
            >
              GitHub &rarr;
            </a>
          )}
          {liveUrl && (
            <a
              href={liveUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-text-muted transition-colors hover:text-accent"
            >
              Live Demo &rarr;
            </a>
          )}
        </div>
      </div>
    </motion.article>
  );
}
