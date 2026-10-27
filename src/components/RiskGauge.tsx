import type { RiskLevel, Thresholds } from "@/api/types";
import { RISK_TEXT_CLASS, RiskGlyph } from "@/components/RiskGlyph";
import { RISK_LABELS, probability } from "@/lib/format";

interface Props {
  prob: number | null;
  level: RiskLevel | null;
  thresholds?: Thresholds;
}

const CX = 100;
const CY = 100;
const R = 78;

function point(fraction: number, radius = R): [number, number] {
  const angle = Math.PI * (1 - fraction);
  return [CX + radius * Math.cos(angle), CY - radius * Math.sin(angle)];
}

function arc(from: number, to: number): string {
  const [x1, y1] = point(from);
  const [x2, y2] = point(to);
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

/** A half-dial. The needle shows the probability; the band names and the big label say the same in words. */
export function RiskGauge({ prob, level, thresholds = { medium: 0.3, high: 0.6 } }: Props) {
  const value = prob ?? 0;
  const [nx, ny] = point(Math.min(1, Math.max(0, value)), R - 14);
  const description =
    prob == null
      ? "No prediction yet"
      : `${level ? RISK_LABELS[level] : ""}: ${probability(prob)} chance of dropping out`;
  return (
    <figure className="m-0 text-center">
      <svg viewBox="0 0 200 124" role="img" aria-label={description} className="mx-auto w-full max-w-[17rem]">
        <path d={arc(0, thresholds.medium)} fill="none" strokeWidth="14" className="stroke-low" />
        <path
          d={arc(thresholds.medium, thresholds.high)}
          fill="none"
          strokeWidth="14"
          strokeDasharray="7 3"
          className="stroke-medium"
        />
        <path d={arc(thresholds.high, 1)} fill="none" strokeWidth="14" strokeDasharray="2 3" className="stroke-high" />
        {[thresholds.medium, thresholds.high].map((t) => {
          const [x1, y1] = point(t, R - 11);
          const [x2, y2] = point(t, R + 11);
          return <line key={t} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth="2" className="stroke-ink" />;
        })}
        {prob != null && (
          <>
            <line x1={CX} y1={CY} x2={nx} y2={ny} strokeWidth="3" strokeLinecap="round" className="stroke-ink" />
            <circle cx={CX} cy={CY} r="6" className="fill-ink" />
          </>
        )}
        <text x="12" y="120" fontSize="10" className="fill-muted">
          0%
        </text>
        <text x="188" y="120" fontSize="10" textAnchor="end" className="fill-muted">
          100%
        </text>
      </svg>
      <figcaption className="-mt-1">
        <div data-testid="risk-prob" className="font-serif text-5xl font-semibold leading-none">
          {probability(prob)}
        </div>
        <div className={`mt-1 inline-flex items-center gap-1.5 font-semibold ${RISK_TEXT_CLASS[level ?? "none"]}`}>
          <RiskGlyph level={level} />
          {level ? RISK_LABELS[level] : "Not scored"}
        </div>
        <div className="mt-0.5 text-sm text-muted">
          Medium from {Math.round(thresholds.medium * 100)}%, high from {Math.round(thresholds.high * 100)}%
        </div>
      </figcaption>
    </figure>
  );
}
