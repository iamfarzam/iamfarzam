export const locales = ["en", "es", "fr", "de", "zh", "ja", "ar", "pt", "ru", "bn", "hi", "ur", "ko", "tr", "ro", "hu", "it", "sm", "mi"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const rtlLocales: readonly Locale[] = ["ar", "ur"];
