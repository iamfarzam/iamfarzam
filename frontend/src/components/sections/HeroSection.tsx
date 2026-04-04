"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useEffect, useState } from "react";

import Button from "@/components/ui/Button";
import SocialLinks from "@/components/ui/SocialLinks";
import type { Profile } from "@/lib/types";

interface HeroProps {
  profile: Profile;
}

const roles = [
  "Software Engineer",
  "System Architect",
  "Open Source Contributor",
  "Problem Solver",
];

function useTypewriter(words: string[], speed = 100, pause = 2000) {
  const [text, setText] = useState("");
  const [wordIndex, setWordIndex] = useState(0);
  const [phase, setPhase] = useState<"typing" | "pausing" | "deleting">("typing");

  useEffect(() => {
    const current = words[wordIndex];

    const timeout = setTimeout(
      () => {
        if (phase === "typing") {
          if (text.length < current.length) {
            setText(current.slice(0, text.length + 1));
          } else {
            setPhase("pausing");
          }
        } else if (phase === "pausing") {
          setPhase("deleting");
        } else {
          if (text.length > 0) {
            setText(text.slice(0, -1));
          } else {
            setWordIndex((prev) => (prev + 1) % words.length);
            setPhase("typing");
          }
        }
      },
      phase === "pausing" ? pause : phase === "deleting" ? speed / 2 : speed
    );

    return () => clearTimeout(timeout);
  }, [text, wordIndex, phase, words, speed, pause]);

  return text;
}

export default function HeroSection({ profile }: HeroProps) {
  const typedRole = useTypewriter(roles);
  const fullName = profile.full_name?.trim() || "Developer";
  const firstName = fullName.split(" ")[0] || "Developer";
  const initials = fullName
    .split(" ")
    .filter(Boolean)
    .map((n) => n[0])
    .join("") || "D";
  const headline = profile.headline?.trim() || "I solve complex problems and build software that lasts.";

  return (
    <section className="relative flex min-h-[calc(100vh-4rem)] items-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/4 top-1/4 h-96 w-96 rounded-full bg-accent/5 blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-accent/10 blur-3xl" />
      </div>

      <div className="mx-auto flex w-full max-w-6xl flex-col-reverse items-center gap-12 px-4 py-20 sm:px-6 md:flex-row lg:px-8">
        {/* Text */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex-1 text-center md:text-left"
        >
          <p className="text-sm font-medium uppercase tracking-widest text-accent">
            Design · Build · Ship
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-text sm:text-5xl lg:text-6xl">
            Hi, I&apos;m{" "}
            <span className="text-accent">{firstName}</span>
          </h1>
          <div className="mt-4 h-8 text-xl text-text-secondary sm:text-2xl">
            <span>{typedRole}</span>
            <span className="animate-pulse text-accent">|</span>
          </div>
          <p className="mt-6 max-w-lg text-text-secondary md:text-lg">
            {headline}
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4 md:justify-start">
            <Button as="a" href="/#contact">
              Get In Touch
            </Button>
            {profile.resume && (
              <Button
                as="a"
                href={profile.resume}
                variant="outline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Download Resume
              </Button>
            )}
          </div>

          <SocialLinks
            github={profile.github_url}
            linkedin={profile.linkedin_url}
            twitter={profile.twitter_url}
            email={profile.email}
            className="mt-8 justify-center md:justify-start"
          />
        </motion.div>

        {/* Avatar */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="flex-shrink-0"
        >
          {profile.avatar ? (
            <div className="relative h-64 w-64 overflow-hidden rounded-full border-4 border-accent/20 shadow-2xl shadow-accent/10 sm:h-80 sm:w-80">
              <Image
                src={profile.avatar}
                alt={fullName}
                fill
                className="object-cover"
                priority
                sizes="320px"
              />
            </div>
          ) : (
            <div className="flex h-64 w-64 items-center justify-center rounded-full border-4 border-accent/20 bg-bg-tertiary text-6xl font-bold text-accent sm:h-80 sm:w-80">
              {initials}
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}
