import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant =
  | "primary"
  | "outline"
  | "subtle"
  | "ghost"
  | "ghostDark";
export type ButtonSize = "sm" | "md" | "icon";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
}

const baseClass =
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-bold uppercase transition focus:outline-none focus-visible:ring-2 focus-visible:ring-b2b-red/30 disabled:cursor-not-allowed disabled:opacity-60";

const variantClass: Record<ButtonVariant, string> = {
  primary: "border border-b2b-red bg-b2b-red text-white hover:brightness-95",
  outline: "border border-b2b-red bg-white text-b2b-red hover:bg-b2b-red-soft",
  subtle:
    "border border-b2b-red bg-[#f2f2f2] text-b2b-red hover:bg-b2b-red-soft",
  ghost:
    "border border-[#ebebeb] bg-white text-[#666666] hover:bg-[#f2f2f2] hover:text-[#414041]",
  ghostDark:
    "border border-white/25 bg-transparent text-white hover:bg-white/10 hover:text-white",
};

const sizeClass: Record<ButtonSize, string> = {
  sm: "min-h-9 px-3 py-1.5",
  md: "min-h-11 px-5 py-2",
  icon: "h-9 w-9 p-0",
};

export function Button({
  variant = "primary",
  size = "md",
  icon,
  className = "",
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={[baseClass, variantClass[variant], sizeClass[size], className]
        .filter(Boolean)
        .join(" ")}
      type={type}
      {...rest}
    >
      {icon}
      {children}
    </button>
  );
}
