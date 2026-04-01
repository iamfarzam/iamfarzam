"use client";

import { motion } from "framer-motion";

interface SectionProps {
  id: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

export default function Section({
  id,
  title,
  subtitle,
  children,
  className = "",
}: SectionProps) {
  return (
    <section id={id} className={`py-20 ${className}`}>
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="mb-12 text-center"
        >
          <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-3 text-text-secondary">{subtitle}</p>
          )}
          <div className="mx-auto mt-4 h-1 w-12 rounded-full bg-accent" />
        </motion.div>
        {children}
      </div>
    </section>
  );
}
