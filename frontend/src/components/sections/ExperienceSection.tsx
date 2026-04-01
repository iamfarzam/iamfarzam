"use client";

import { motion } from "framer-motion";
import Image from "next/image";

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
  return (
    <Section
      id="experience"
      title="Experience"
      subtitle="My professional journey"
      className="bg-bg-secondary"
    >
      <div className="relative mx-auto max-w-3xl">
        {/* Timeline line */}
        <div className="absolute left-4 top-0 h-full w-px bg-border md:left-1/2" />

        {experience.map((exp, index) => (
          <motion.div
            key={exp.id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className={`relative mb-8 flex flex-col pl-12 md:w-1/2 md:pl-0 ${
              index % 2 === 0
                ? "md:ml-auto md:pl-8"
                : "md:mr-auto md:pr-8 md:text-right"
            }`}
          >
            {/* Timeline dot */}
            <div
              className={`absolute left-2.5 top-1 h-3 w-3 rounded-full border-2 border-accent bg-bg md:top-1 ${
                index % 2 === 0
                  ? "md:-left-1.5 md:left-auto md:right-auto"
                  : "md:-right-1.5 md:left-auto"
              }`}
              style={index % 2 === 0 ? { left: undefined, right: undefined, marginLeft: "-6px" } : {}}
            />

            <div className="rounded-xl border border-border bg-card p-5 transition-all hover:border-accent/30 hover:shadow-md">
              <div className={`flex items-center gap-3 ${index % 2 !== 0 ? "md:flex-row-reverse" : ""}`}>
                {exp.company_logo && (
                  <Image
                    src={exp.company_logo}
                    alt={exp.company}
                    width={40}
                    height={40}
                    className="rounded-lg"
                  />
                )}
                <div>
                  <h3 className="font-semibold text-text">{exp.role}</h3>
                  <p className="text-sm text-accent">
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
                {formatDate(exp.start_date)} — {exp.end_date ? formatDate(exp.end_date) : "Present"}
                {exp.location && ` · ${exp.location}`}
              </p>

              <p className="mt-3 text-sm text-text-secondary leading-relaxed">
                {exp.description}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}
