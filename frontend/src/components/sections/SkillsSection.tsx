"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";

import Badge from "@/components/ui/Badge";
import Section from "@/components/ui/Section";
import { gridClassesForCount } from "@/lib/grid";
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
      {categories.length === 0 ? (
        <p className="text-center text-sm text-text-muted">{t("no_skills")}</p>
      ) : (
        <div className={gridClassesForCount(categories.length)}>
          {categories.map((category, catIndex) => (
            <motion.div
              key={category.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: catIndex * 0.1 }}
              className="flex h-full flex-col rounded-xl border border-border bg-card p-6"
            >
              <h3 className="mb-4 line-clamp-1 text-lg font-semibold text-text">
                {category.name}
              </h3>
              {category.skills.length === 0 ? (
                <p className="text-sm italic text-text-muted">
                  {t("no_skills_in_category")}
                </p>
              ) : (
                <ul className="flex flex-wrap gap-2" aria-label={category.name}>
                  {category.skills.map((skill) => (
                    <li key={skill.id}>
                      <Badge>{skill.name}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </Section>
  );
}
