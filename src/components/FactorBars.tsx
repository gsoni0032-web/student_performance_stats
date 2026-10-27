import type { Factor } from "@/api/types";

/** Why the score is what it is. Raising factors are solid red bars, lowering ones are hatched green. */
export function FactorBars({ factors }: { factors: Factor[] }) {
  if (factors.length === 0) {
    return <p className="text-muted">No explanation is available until the student has been scored.</p>;
  }
  const largest = Math.max(...factors.map((f) => f.impact));
  return (
    <ul className="space-y-3" aria-label="Factors behind this score">
      {factors.map((factor) => {
        const raises = factor.driver === "raises";
        return (
          <li key={factor.key}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span>
                <span className="font-semibold">{factor.label}</span>{" "}
                <span className="text-muted">({factor.display})</span>
              </span>
              <span className={`whitespace-nowrap font-semibold ${raises ? "text-high" : "text-low"}`}>
                {raises ? "▲ raises" : "▼ lowers"} · {factor.impact.toFixed(0)}%
              </span>
            </div>
            <div className="mt-1 h-2.5 rounded-sm bg-sunken" aria-hidden="true">
              <div
                className={`h-full rounded-sm ${raises ? "bg-high" : "bg-low"}`}
                style={{
                  width: `${Math.max(4, (factor.impact / largest) * 100)}%`,
                  backgroundImage: raises
                    ? undefined
                    : "repeating-linear-gradient(135deg, transparent 0 3px, rgb(var(--surface)) 3px 5px)",
                }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
