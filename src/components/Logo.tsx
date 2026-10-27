/** Three nodes joined by a path: where a student is, where they are heading, and the step in between. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true" focusable="false" className="text-brand">
      <path
        d="M4.5 22 13 13.5 23.5 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="4.5" cy="22" r="3" fill="rgb(var(--paper))" stroke="currentColor" strokeWidth="2" />
      <circle cx="13" cy="13.5" r="3" fill="currentColor" />
      <circle cx="23.5" cy="6" r="3" fill="rgb(var(--paper))" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark />
      <span className="font-serif text-xl font-semibold tracking-tightest">Pathway</span>
    </span>
  );
}
