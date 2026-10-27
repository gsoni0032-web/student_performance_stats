import type { RiskLevel } from "@/api/types";

interface Props {
  level: RiskLevel | null;
  size?: number;
}

/** Risk is always a shape as well as a colour: triangle = high, diamond = medium, circle = low. */
export function RiskGlyph({ level, size = 12 }: Props) {
  const common = { width: size, height: size, viewBox: "0 0 12 12", "aria-hidden": true, focusable: false } as const;
  switch (level) {
    case "high":
      return (
        <svg {...common} fill="currentColor">
          <path d="M6 1 11.5 10.5H0.5Z" />
        </svg>
      );
    case "medium":
      return (
        <svg {...common} fill="currentColor">
          <path d="M6 0.5 11.5 6 6 11.5 0.5 6Z" />
        </svg>
      );
    case "low":
      return (
        <svg {...common} fill="currentColor">
          <circle cx="6" cy="6" r="4.6" />
        </svg>
      );
    default:
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M2 6h8" />
        </svg>
      );
  }
}

export const RISK_TEXT_CLASS: Record<RiskLevel | "none", string> = {
  high: "text-high",
  medium: "text-medium",
  low: "text-low",
  none: "text-muted",
};
export const RISK_BG_CLASS: Record<RiskLevel | "none", string> = {
  high: "bg-high-bg",
  medium: "bg-medium-bg",
  low: "bg-low-bg",
  none: "bg-sunken",
};
