import type { Metadata } from "next";
import localFont from "next/font/local";
import { cookies } from "next/headers";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";

import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import ThemeProvider from "@/components/layout/ThemeProvider";
import ScrollToTop from "@/components/ui/ScrollToTop";
import { fetchProfile } from "@/lib/api";
import { defaultLocale, locales, rtlLocales, type Locale } from "@/i18n/config";
import "@/styles/globals.css";

const inter = localFont({
  src: "../fonts/Inter-Variable.ttf",
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = localFont({
  src: "../fonts/JetBrainsMono-Variable.ttf",
  variable: "--font-jetbrains",
  display: "swap",
});

async function getLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const cookie = cookieStore.get("NEXT_LOCALE")?.value as Locale | undefined;
  return cookie && locales.includes(cookie) ? cookie : defaultLocale;
}

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  try {
    const profile = await fetchProfile(locale);
    return {
      title: {
        default: profile.meta_title || `${profile.full_name} — Portfolio`,
        template: `%s | ${profile.full_name}`,
      },
      description: profile.meta_description || profile.headline,
      metadataBase: new URL(
        process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"
      ),
      openGraph: {
        title: profile.meta_title || `${profile.full_name} — Portfolio`,
        description: profile.meta_description || profile.headline,
        images: profile.og_image ? [{ url: profile.og_image }] : [],
        type: "website",
      },
      twitter: {
        card: "summary_large_image",
        title: profile.meta_title || `${profile.full_name} — Portfolio`,
        description: profile.meta_description || profile.headline,
        images: profile.og_image ? [profile.og_image] : [],
      },
    };
  } catch {
    return {
      title: "Portfolio",
      description: "Software Engineer Portfolio",
    };
  }
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();
  const dir = rtlLocales.includes(locale) ? "rtl" : "ltr";

  let profile = null;
  try {
    profile = await fetchProfile(locale);
  } catch {
    // Backend may not be running yet
  }

  return (
    <html
      lang={locale}
      dir={dir}
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-bg font-sans text-text antialiased">
        <NextIntlClientProvider messages={messages}>
          <ThemeProvider>
            <Header />
            <main className="pt-16">{children}</main>
            <Footer profile={profile} />
            <ScrollToTop />
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
