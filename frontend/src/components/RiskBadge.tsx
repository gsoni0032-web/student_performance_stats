import type { RiskLevel } from "@/api/types";
import { RISK_BG_CLASS, RISK_TEXT_CLASS, RiskGlyph } from "@/components/RiskGlyph";
import { RISK_LABELS, probability } from "@/lib/format";

interface Props {
  level: RiskLevel | null;
  prob?: number | null;
  showPercent?: boolean;
}

export function RiskBadge({ level, prob, showPercent = true }: Props) {
  const key = level ?? "none";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-0.5 text-sm font-semibold ${RISK_BG_CLASS[key]} ${RISK_TEXT_CLASS[key]}`}
    >
      <RiskGlyph level={level} />
      <span>{level ? RISK_LABELS[level] : "Not scored"}</span>
      {showPercent && prob != null && <span className="font-normal">{probability(prob)}</span>}
    </span>
  );
}
