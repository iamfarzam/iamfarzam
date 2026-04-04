"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";

import Section from "@/components/ui/Section";
import type { SkillCategory } from "@/lib/types";

interface SkillsProps {
  categories: SkillCategory[];
}

export default function SkillsSection({ categories }: SkillsProps) {
  const t = useTranslations("skills");
  return (
    <Section
      id="skills"
      title={t("title")}
      subtitle={t("subtitle")}
      className="bg-bg-secondary"
    >
      <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
        {categories.map((category, catIndex) => (
          <motion.div
            key={category.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: catIndex * 0.1 }}
            className="rounded-xl border border-border bg-card p-6"
          >
            <h3 className="mb-4 text-lg font-semibold text-text">
              {category.name}
            </h3>
            <div className="space-y-3">
              {category.skills.map((skill) => (
                <div key={skill.id}>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-sm font-medium text-text-secondary">
                      {skill.name}
                    </span>
                    <span className="text-xs text-text-muted">
                      {skill.proficiency}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-bg-tertiary">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${skill.proficiency}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                      className="h-full rounded-full bg-accent"
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}
