"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useTranslations } from "next-intl";

import Section from "@/components/ui/Section";
import type { Experience } from "@/lib/types";

interface ExperienceProps {
  experience: Experience[];
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
}

export default function ExperienceSection({ experience }: ExperienceProps) {
  const t = useTranslations("experience");
  const showTimelineLine = experience.length > 1;

  return (
    <Section
      id="experience"
      title={t("title")}
      subtitle={t("subtitle")}
      className="bg-bg-secondary"
    >
      <div className="relative mx-auto max-w-3xl">
        {showTimelineLine && (
          <div className="absolute left-4 top-0 h-full w-px bg-border md:left-1/2" aria-hidden />
        )}

        {experience.map((exp, index) => {
          const isLeft = index % 2 !== 0;
          const isRight = index % 2 === 0;

          return (
            <motion.div
              key={exp.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className={`relative mb-8 flex flex-col pl-12 last:mb-0 md:w-1/2 md:pl-0 ${
                isRight ? "md:ml-auto md:pl-8" : "md:mr-auto md:pr-8 md:text-right"
              }`}
            >
              {/* Timeline dot — anchored to the timeline line */}
              <div
                className={`absolute left-2.5 top-2 h-3 w-3 rounded-full border-2 border-accent bg-bg ${
                  isRight
                    ? "md:left-[calc(0%-0.375rem)]"
                    : "md:left-auto md:right-[calc(0%-0.375rem)]"
                }`}
                aria-hidden
              />

              <div className="rounded-xl border border-border bg-card p-5 transition-all hover:border-accent/30 hover:shadow-md">
                <div className={`flex items-center gap-3 ${isLeft ? "md:flex-row-reverse" : ""}`}>
                  {exp.company_logo && (
                    <Image
                      src={exp.company_logo}
                      alt={exp.company}
                      width={40}
                      height={40}
                      className="rounded-lg"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <h3 className="line-clamp-2 font-semibold text-text">{exp.role}</h3>
                    <p className="line-clamp-1 text-sm text-accent">
                      {exp.company_url ? (
                        <a
                          href={exp.company_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline"
                        >
                          {exp.company}
                        </a>
                      ) : (
                        exp.company
                      )}
                    </p>
                  </div>
                </div>

                <p className="mt-2 text-xs text-text-muted">
                  {formatDate(exp.start_date)} — {exp.end_date ? formatDate(exp.end_date) : t("present")}
                  {exp.location && ` · ${exp.location}`}
                </p>

                {exp.description && (
                  <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-text-secondary">
                    {exp.description}
                  </p>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </Section>
  );
}
