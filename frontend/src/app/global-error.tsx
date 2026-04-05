"use client";

import { useEffect } from "react";

/**
 * Global error boundary — completely standalone.
 * Renders when the root layout itself fails, so it must provide
 * its own <html> and <body> with all styles inlined.
 * No external CSS, no theme provider, no layout components.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Something Went Wrong</title>
        <style
          dangerouslySetInnerHTML={{
            __html: `
              *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
              @media (prefers-color-scheme: dark) {
                :root {
                  --bg: #0b1121;
                  --bg-secondary: #111827;
                  --text: #f1f5f9;
                  --text-secondary: #94a3b8;
                  --accent: #3b82f6;
                  --accent-hover: #60a5fa;
                  --accent-light: #1e3a5f;
                  --border: #1e293b;
                }
              }
              @media (prefers-color-scheme: light) {
                :root {
                  --bg: #ffffff;
                  --bg-secondary: #f8fafc;
                  --text: #0f172a;
                  --text-secondary: #475569;
                  --accent: #2563eb;
                  --accent-hover: #1d4ed8;
                  --accent-light: #dbeafe;
                  --border: #e2e8f0;
                }
              }
              :root {
                --bg: #ffffff;
                --bg-secondary: #f8fafc;
                --text: #0f172a;
                --text-secondary: #475569;
                --accent: #2563eb;
                --accent-hover: #1d4ed8;
                --accent-light: #dbeafe;
                --border: #e2e8f0;
              }
              body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
              }
              .container {
                text-align: center;
                padding: 2rem;
                max-width: 480px;
              }
              .icon-wrapper {
                width: 80px;
                height: 80px;
                margin: 0 auto 1.5rem;
                border-radius: 50%;
                background-color: var(--accent-light);
                display: flex;
                align-items: center;
                justify-content: center;
              }
              .icon-wrapper svg {
                width: 40px;
                height: 40px;
                color: var(--accent);
              }
              h1 {
                font-size: 1.875rem;
                font-weight: 700;
                line-height: 1.2;
                margin-bottom: 0.75rem;
              }
              p {
                font-size: 1rem;
                line-height: 1.6;
                color: var(--text-secondary);
                margin-bottom: 2rem;
              }
              .actions {
                display: flex;
                gap: 0.75rem;
                justify-content: center;
                flex-wrap: wrap;
              }
              .btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0.625rem 1.25rem;
                font-size: 0.875rem;
                font-weight: 500;
                border-radius: 0.5rem;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
              }
              .btn-primary {
                background-color: var(--accent);
                color: #ffffff;
              }
              .btn-primary:hover {
                background-color: var(--accent-hover);
              }
              .btn-outline {
                background-color: transparent;
                color: var(--text);
                border: 1px solid var(--border);
              }
              .btn-outline:hover {
                border-color: var(--accent);
                color: var(--accent);
              }
            `,
          }}
        />
      </head>
      <body>
        <div className="container">
          <div className="icon-wrapper">
            <svg
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
              />
            </svg>
          </div>
          <h1>Something Went Wrong</h1>
          <p>
            An unexpected error occurred. We apologize for the inconvenience.
            Please try again or return to the homepage.
          </p>
          <div className="actions">
            <button className="btn btn-primary" onClick={() => reset()}>
              Try Again
            </button>
            <a className="btn btn-outline" href="/">
              Go Home
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
