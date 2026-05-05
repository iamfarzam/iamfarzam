import fs from "node:fs";
import path from "node:path";
import { describe, it, expect } from "vitest";

const MESSAGES_DIR = path.resolve(__dirname);

function readMessages(): Record<string, Record<string, unknown>> {
  const files = fs.readdirSync(MESSAGES_DIR).filter((f) => f.endsWith(".json"));
  const out: Record<string, Record<string, unknown>> = {};
  for (const f of files) {
    const code = path.basename(f, ".json");
    out[code] = JSON.parse(fs.readFileSync(path.join(MESSAGES_DIR, f), "utf-8"));
  }
  return out;
}

function flatten(obj: Record<string, unknown>, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      Object.assign(out, flatten(v as Record<string, unknown>, full));
    } else {
      out[full] = String(v);
    }
  }
  return out;
}

const all = readMessages();
const locales = Object.keys(all).sort();
const enFlat = flatten(all.en);

describe("translation parity", () => {
  it("includes all 20 supported locale files", () => {
    expect(locales).toHaveLength(20);
  });

  it.each(locales.filter((l) => l !== "en"))(
    "%s has every key that en has",
    (locale) => {
      const localeFlat = flatten(all[locale]);
      const missing = Object.keys(enFlat).filter((k) => !(k in localeFlat));
      expect(missing).toEqual([]);
    },
  );

  it.each(locales)("%s has no empty string values", (locale) => {
    const flat = flatten(all[locale]);
    const empty = Object.entries(flat)
      .filter(([, v]) => v.trim() === "")
      .map(([k]) => k);
    expect(empty).toEqual([]);
  });
});

describe("no English bleed-through in non-English locales", () => {
  // Keys whose values are intentionally identical across locales
  // (brand names, codes, universal-format placeholders).
  const KEYS_ALLOWED_TO_MATCH_ENGLISH = new Set<string>([
    "not_found.code",
    "card.github",
    "contact.email_placeholder",
  ]);

  // Brand-name strings that legitimately appear inside translated values
  // (e.g. "View on GitHub" → "GitHub에서 보기"). Stripped before computing
  // the ASCII-letter ratio so they don't false-positive as untranslated.
  const BRAND_TOKENS = [
    "GitHub", "LinkedIn", "Twitter", "Facebook",
    "Instagram", "YouTube", "Slack", "Discord",
  ];

  function stripPlaceholders(s: string): string {
    return s
      .replace(/<[^>]+>/g, "")
      .replace(/\{[^}]+\}/g, "")
      .trim();
  }

  function stripBrands(s: string): string {
    let out = s;
    for (const t of BRAND_TOKENS) {
      out = out.split(t).join("");
    }
    return out;
  }

  function asciiLetterRatio(s: string): number {
    if (!s) return 0;
    const ascii = s.match(/[A-Za-z]/g)?.length || 0;
    const total = s.match(/\p{L}/gu)?.length || 0;
    return total === 0 ? 0 : ascii / total;
  }

  // Locales whose script is NOT Latin — values should be mostly non-ASCII.
  const NON_LATIN = ["ar", "bn", "fa", "hi", "ja", "ko", "ru", "ur", "zh"];

  it.each(NON_LATIN)(
    "%s values are written in their native script, not English",
    (locale) => {
      const flat = flatten(all[locale]);
      const offenders: string[] = [];
      for (const [key, value] of Object.entries(flat)) {
        if (KEYS_ALLOWED_TO_MATCH_ENGLISH.has(key)) continue;
        const stripped = stripBrands(stripPlaceholders(value));
        if (!stripped || stripped.length <= 3) continue;
        const enStripped = stripBrands(stripPlaceholders(enFlat[key] || ""));
        if (stripped === enStripped) {
          offenders.push(`${key}: matches English verbatim ("${value}")`);
          continue;
        }
        if (asciiLetterRatio(stripped) > 0.5) {
          offenders.push(`${key}: looks untranslated ("${value}")`);
        }
      }
      expect(offenders).toEqual([]);
    },
  );
});
