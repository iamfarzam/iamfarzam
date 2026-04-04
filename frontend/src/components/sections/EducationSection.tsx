"use client";

import { motion } from "framer-motion";
import Image from "next/image";

import Section from "@/components/ui/Section";
import type { Education } from "@/lib/types";

interface EducationProps {
  education: Education[];
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
}

export default function EducationSection({ education }: EducationProps) {
  return (
    <Section id="education" title="Education" subtitle="Where it all started">
      <div className="mx-auto max-w-3xl space-y-6">
        {education.map((edu, index) => (
          <motion.div
            key={edu.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="flex gap-4 rounded-xl border border-border bg-card p-5 transition-all hover:border-accent/30 hover:shadow-md"
          >
            {edu.institution_logo && (
              <Image
                src={edu.institution_logo}
                alt={edu.institution}
                width={48}
                height={48}
                className="h-12 w-12 rounded-lg object-contain"
              />
            )}
            <div className="flex-1">
              <h3 className="font-semibold text-text">{edu.degree}</h3>
              {edu.field_of_study && (
                <p className="text-sm text-accent">{edu.field_of_study}</p>
              )}
              <p className="text-sm text-text-secondary">{edu.institution}</p>
              <p className="mt-1 text-xs text-text-muted">
                {formatDate(edu.start_date)} — {edu.end_date ? formatDate(edu.end_date) : "Present"}
              </p>
              {edu.description && (
                <p className="mt-2 text-sm text-text-secondary leading-relaxed">
                  {edu.description}
                </p>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}
