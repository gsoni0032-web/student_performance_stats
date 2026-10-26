const channel = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    borderRadius: { none: "0", sm: "2px", DEFAULT: "3px", md: "4px", lg: "4px", full: "9999px" },
    extend: {
      colors: {
        paper: channel("paper"),
        surface: channel("surface"),
        sunken: channel("sunken"),
        line: channel("line"),
        ink: channel("ink"),
        muted: channel("muted"),
        brand: channel("brand"),
        "brand-ink": channel("brand-ink"),
        high: channel("high"),
        "high-bg": channel("high-bg"),
        medium: channel("medium"),
        "medium-bg": channel("medium-bg"),
        low: channel("low"),
        "low-bg": channel("low-bg"),
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      letterSpacing: { tightest: "-0.025em", label: "0.08em" },
    },
  },
  plugins: [],
};
