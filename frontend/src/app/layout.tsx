import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import ThemeProvider from "@/components/layout/ThemeProvider";
import ScrollToTop from "@/components/ui/ScrollToTop";
import { fetchProfile } from "@/lib/api";
import "@/styles/globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  try {
    const profile = await fetchProfile();
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
  let profile = null;
  try {
    profile = await fetchProfile();
  } catch {
    // Backend may not be running yet
  }

  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-bg font-sans text-text antialiased">
        <ThemeProvider>
          <Header />
          <main className="pt-16">{children}</main>
          <Footer profile={profile} />
          <ScrollToTop />
        </ThemeProvider>
      </body>
    </html>
  );
}
