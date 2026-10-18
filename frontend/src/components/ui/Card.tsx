import type { ReactNode } from "react";

export type CardPadding = "none" | "sm" | "md";

interface CardProps {
  children: ReactNode;
  padding?: CardPadding;
  className?: string;
}

const paddingClass: Record<CardPadding, string> = {
  none: "",
  sm: "p-5",
  md: "p-6",
};

export function Card({ children, padding = "md", className = "" }: CardProps) {
  return (
    <div
      className={[
        "rounded-xl border border-black/5 bg-white shadow-b2b",
        paddingClass[padding],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}
