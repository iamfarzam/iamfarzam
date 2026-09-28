export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const base = process.env.INTERNAL_API_URL || "http://localhost:8000/api/v1";
    const url = new URL("/healthz/", base);
    const headers: Record<string, string> = {};
    if (process.env.NEXT_PUBLIC_SITE_URL) {
      headers.Host = new URL(process.env.NEXT_PUBLIC_SITE_URL).host;
    }
    if (process.env.INTERNAL_API_FORWARD_PROTO === "https") {
      headers["X-Forwarded-Proto"] = "https";
    }
    const response = await fetch(url, {
      headers,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(3000),
    });
    const ready = response.ok && (await response.json()).ready === true;
    return Response.json({ ready }, {
      status: ready ? 200 : 503,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ ready: false }, {
      status: 503,
      headers: { "Cache-Control": "no-store" },
    });
  }
}
