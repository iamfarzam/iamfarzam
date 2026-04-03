"use client";

import { motion } from "framer-motion";
import Image from "next/image";

import Section from "@/components/ui/Section";
import type { Profile } from "@/lib/types";

interface AboutProps {
  profile: Profile;
}

export default function AboutSection({ profile }: AboutProps) {
  const fullName = profile.full_name?.trim() || "Developer";
  const initials = fullName
    .split(" ")
    .filter(Boolean)
    .map((n) => n[0])
    .join("") || "D";
  const bioParagraphs = (profile.bio || "")
    .split("\n")
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  return (
    <Section id="about" title="About Me" subtitle="A bit about who I am and what I do">
      <div className="grid items-center gap-12 md:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          {profile.avatar ? (
            <div className="relative mx-auto aspect-square w-full max-w-sm overflow-hidden rounded-2xl shadow-xl">
              <Image
                src={profile.avatar}
                alt={fullName}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 384px"
              />
            </div>
          ) : (
            <div className="mx-auto flex aspect-square w-full max-w-sm items-center justify-center rounded-2xl bg-bg-tertiary text-8xl font-bold text-accent">
              {initials}
            </div>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 30 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="space-y-4 text-text-secondary leading-relaxed">
            {bioParagraphs.length > 0 ? (
              bioParagraphs.map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))
            ) : (
              <p>I build reliable backend systems and modern web applications.</p>
            )}
          </div>

          {profile.location && (
            <div className="mt-6 flex items-center gap-2 text-sm text-text-muted">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {profile.location}
            </div>
          )}
        </motion.div>
      </div>
    </Section>
  );
}
