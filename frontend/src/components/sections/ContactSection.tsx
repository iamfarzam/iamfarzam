"use client";

import { motion } from "framer-motion";
import { useState } from "react";

import Button from "@/components/ui/Button";
import Section from "@/components/ui/Section";
import { submitContact } from "@/lib/api";

export default function ContactSection() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("sending");
    setErrorMsg("");
    try {
      await submitContact(form);
      setStatus("sent");
      setForm({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  const inputClasses =
    "w-full rounded-lg border border-border bg-bg px-4 py-2.5 text-sm text-text placeholder-text-muted transition-colors focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent";

  return (
    <Section
      id="contact"
      title="Get In Touch"
      subtitle="Have a question or want to work together?"
      className="bg-bg-secondary"
    >
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        onSubmit={handleSubmit}
        className="mx-auto max-w-xl space-y-5"
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="name" className="mb-1.5 block text-sm font-medium text-text">
              Name
            </label>
            <input
              id="name"
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={inputClasses}
              placeholder="Your name"
            />
          </div>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-text">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className={inputClasses}
              placeholder="your@email.com"
            />
          </div>
        </div>

        <div>
          <label htmlFor="subject" className="mb-1.5 block text-sm font-medium text-text">
            Subject
          </label>
          <input
            id="subject"
            type="text"
            required
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            className={inputClasses}
            placeholder="What's this about?"
          />
        </div>

        <div>
          <label htmlFor="message" className="mb-1.5 block text-sm font-medium text-text">
            Message
          </label>
          <textarea
            id="message"
            required
            rows={5}
            value={form.message}
            onChange={(e) => setForm({ ...form, message: e.target.value })}
            className={`${inputClasses} resize-none`}
            placeholder="Your message..."
          />
        </div>

        <Button type="submit" className="w-full" disabled={status === "sending"}>
          {status === "sending" ? "Sending..." : "Send Message"}
        </Button>

        {status === "sent" && (
          <p className="text-center text-sm text-green-600 dark:text-green-400">
            Message sent successfully! You&apos;ll hear back soon.
          </p>
        )}
        {status === "error" && (
          <p className="text-center text-sm text-red-600 dark:text-red-400">
            {errorMsg}
          </p>
        )}
      </motion.form>
    </Section>
  );
}
