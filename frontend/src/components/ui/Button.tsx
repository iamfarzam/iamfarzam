import { type ComponentPropsWithoutRef, type ElementType } from "react";

type Variant = "primary" | "secondary" | "outline" | "ghost";

type ButtonProps<T extends ElementType = "button"> = {
  variant?: Variant;
  as?: T;
} & ComponentPropsWithoutRef<T>;

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover shadow-sm hover:shadow-md",
  secondary:
    "bg-bg-tertiary text-text hover:bg-border",
  outline:
    "border border-border text-text hover:border-accent hover:text-accent",
  ghost:
    "text-text-secondary hover:text-accent hover:bg-bg-tertiary",
};

export default function Button<T extends ElementType = "button">({
  variant = "primary",
  as,
  className = "",
  children,
  ...props
}: ButtonProps<T>) {
  const Component = as || "button";
  return (
    <Component
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-200 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}
