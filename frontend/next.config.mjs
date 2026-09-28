import createNextIntlPlugin from "next-intl/plugin";
import { fileURLToPath } from "node:url";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

// Uploaded media uses the public site origin or a configured storage origin.
const mediaPatterns = [process.env.NEXT_PUBLIC_SITE_URL, process.env.PUBLIC_MEDIA_BASE_URL]
  .filter(Boolean)
  .map((value) => {
    const url = new URL(value);
    return {
      protocol: url.protocol.slice(0, -1),
      hostname: url.hostname,
      port: url.port,
      pathname: `${url.pathname.replace(/\/$/, "")}/**`,
    };
  });

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  outputFileTracingRoot: fileURLToPath(new URL(".", import.meta.url)),
  images: {
    remotePatterns: [
      ...mediaPatterns,
      { protocol: "http", hostname: "localhost", port: "8000" },
      { protocol: "http", hostname: "backend", port: "8000" },
      { protocol: "https", hostname: "*.contabostorage.com" },
      { protocol: "https", hostname: "*.s3.amazonaws.com" },
      { protocol: "https", hostname: "*.s3.*.amazonaws.com" },
    ],
  },
};

export default withNextIntl(nextConfig);
