"use client";

import { useLocale } from "next-intl";
import { useState, useRef, useEffect } from "react";
import { locales, type Locale } from "@/i18n/config";

const labels: Record<Locale, string> = {
  en: "English",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  zh: "中文",
  ja: "日本語",
  ar: "العربية",
  pt: "Português",
  ru: "Русский",
  bn: "বাংলা",
  hi: "हिन्दी",
  ur: "اردو",
  ko: "한국어",
  tr: "Türkçe",
  ro: "Română",
  hu: "Magyar",
  it: "Italiano",
  sm: "Gagana Samoa",
  mi: "Te Reo Māori",
};

const flags: Record<Locale, string> = {
  en: "EN",
  es: "ES",
  fr: "FR",
  de: "DE",
  zh: "中",
  ja: "日",
  ar: "ع",
  pt: "PT",
  ru: "RU",
  bn: "বা",
  hi: "हि",
  ur: "ار",
  ko: "한",
  tr: "TR",
  ro: "RO",
  hu: "HU",
  it: "IT",
  sm: "SM",
  mi: "MI",
};

export default function LanguageSwitcher() {
  const locale = useLocale() as Locale;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function switchLocale(newLocale: Locale) {
    document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=31536000;SameSite=Lax`;
    setOpen(false);
    window.location.reload();
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-bg-tertiary hover:text-accent"
        aria-label="Change language"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.6 9h16.8M3.6 15h16.8" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z" />
        </svg>
        <span>{flags[locale]}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 max-h-80 w-40 overflow-y-auto rounded-lg border border-border bg-bg shadow-lg">
          {locales.map((l) => (
            <button
              key={l}
              onClick={() => switchLocale(l)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-bg-tertiary ${
                l === locale
                  ? "font-medium text-accent"
                  : "text-text-secondary"
              }`}
            >
              <span className="w-6 text-center text-xs font-bold">{flags[l]}</span>
              {labels[l]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
