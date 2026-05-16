import type { Metadata, Viewport } from "next";
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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const baseDefaults: Metadata = {
    metadataBase: new URL(SITE_URL),
    alternates: { canonical: "/" },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-snippet": -1,
        "max-image-preview": "large",
        "max-video-preview": -1,
      },
    },
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
  };

  try {
    const profile = await fetchProfile(locale);
    const fallbackTitle = `${profile.full_name} | Portfolio`;
    const title = profile.meta_title || fallbackTitle;
    const description = profile.meta_description || profile.headline;
    const ogImage = profile.og_image || undefined;

    return {
      ...baseDefaults,
      title: {
        default: title,
        template: `%s | ${profile.full_name}`,
      },
      description,
      applicationName: profile.full_name,
      authors: [{ name: profile.full_name, url: SITE_URL }],
      creator: profile.full_name,
      publisher: profile.full_name,
      openGraph: {
        title,
        description,
        url: "/",
        siteName: profile.full_name,
        locale: "en_US",
        images: ogImage ? [{ url: ogImage, width: 1200, height: 630, alt: title }] : [],
        type: "website",
      },
      twitter: {
        card: "summary_large_image",
        title,
        description,
        images: ogImage ? [ogImage] : [],
      },
    };
  } catch {
    return {
      ...baseDefaults,
      title: "Portfolio",
      description: "Software engineer portfolio.",
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
