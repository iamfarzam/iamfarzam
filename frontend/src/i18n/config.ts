export const locales = ["en", "es", "fr", "de", "zh", "ja", "ar", "pt"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const rtlLocales: readonly Locale[] = ["ar"];
