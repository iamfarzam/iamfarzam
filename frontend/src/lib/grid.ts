/**
 * Picks responsive Tailwind grid classes based on item count so that
 * sections with 1 or 2 items don't sit lonely inside a 3-column grid.
 *
 * - 0 items: caller should render an empty state instead of calling this.
 * - 1 item:  single centered column, capped width.
 * - 2 items: two columns on >= sm, capped width.
 * - 3+ items: full responsive grid (1 / 2 / 3).
 */
export function gridClassesForCount(count: number): string {
  if (count <= 1) return "grid gap-6 grid-cols-1 max-w-md mx-auto";
  if (count === 2) return "grid gap-6 grid-cols-1 sm:grid-cols-2 max-w-3xl mx-auto";
  return "grid gap-6 sm:grid-cols-2 lg:grid-cols-3";
}
