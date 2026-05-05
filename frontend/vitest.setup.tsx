import "@testing-library/jest-dom/vitest";
import React from "react";
import { vi } from "vitest";

/**
 * Stub next-intl so component tests don't need a NextIntlClientProvider.
 * `useTranslations(ns?)` returns a function that echoes the key (prefixed
 * with the namespace if provided), so tests can assert on stable keys.
 */
vi.mock("next-intl", () => ({
  useTranslations: (namespace?: string) =>
    (key: string) => (namespace ? `${namespace}.${key}` : key),
  useLocale: () => "en",
}));

/** next/image — render a plain <img>. */
vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    const { fill, sizes, priority, placeholder, blurDataURL, ...rest } =
      props as Record<string, unknown>;
    void fill; void sizes; void priority; void placeholder; void blurDataURL;
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...(rest as React.ImgHTMLAttributes<HTMLImageElement>)} />;
  },
}));

/** next/link — render a plain <a>. */
vi.mock("next/link", () => ({
  __esModule: true,
  default: ({
    children,
    href,
    ...rest
  }: { children: React.ReactNode; href: string } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

/** framer-motion — render the underlying tag without animation. */
vi.mock("framer-motion", () => {
  const make = (tag: string) =>
    React.forwardRef<HTMLElement, Record<string, unknown>>((props, ref) => {
      const {
        initial, animate, whileInView, whileHover, whileTap, viewport,
        transition, layout, exit, variants, ...rest
      } = props;
      void initial; void animate; void whileInView; void whileHover;
      void whileTap; void viewport; void transition; void layout;
      void exit; void variants;
      return React.createElement(tag, { ref, ...rest });
    });
  const motion = new Proxy({}, { get: (_, tag: string) => make(tag) });
  return {
    motion,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});
