import { useRef, useState, type KeyboardEvent } from "react";

import type { CohortPoint } from "@/api/types";
import { RISK_TEXT_CLASS, RiskGlyph } from "@/components/RiskGlyph";
import { RISK_LABELS, probability } from "@/lib/format";

interface Props {
  points: CohortPoint[];
  onOpen: (id: number) => void;
}

/** Solid with a heavy edge = high, diagonal hatch = medium, pale with a dot = low, dashed = not scored. */
const SQUARE: Record<string, string> = {
  high: "border-2 border-high bg-high text-brand-ink",
  medium: "border border-medium bg-medium-bg text-medium",
  low: "border border-low/40 bg-low-bg text-low",
  none: "border border-dashed border-muted bg-transparent text-muted",
};

const HATCH = "repeating-linear-gradient(45deg, rgb(var(--medium) / 0.4) 0 2px, transparent 2px 5px)";

/**
 * One square per student, riskiest first. The shape inside each square, not just its colour,
 * says which band it is in. Arrow keys move between squares; only one square is a tab stop.
 */
export function CohortRegister({ points, onOpen }: Props) {
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function columns(): number {
    const first = refs.current[0];
    if (!first) return 1;
    let count = 0;
    for (const button of refs.current) {
      if (!button) continue;
      if (button.offsetTop !== first.offsetTop) break;
      count += 1;
    }
    return Math.max(1, count);
  }

  function move(to: number) {
    const next = Math.max(0, Math.min(points.length - 1, to));
    setActive(next);
    refs.current[next]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const step: Record<string, number> = {
      ArrowRight: 1,
      ArrowLeft: -1,
      ArrowDown: columns(),
      ArrowUp: -columns(),
    };
    if (event.key in step) {
      event.preventDefault();
      move(active + step[event.key]);
    } else if (event.key === "Home") {
      event.preventDefault();
      move(0);
    } else if (event.key === "End") {
      event.preventDefault();
      move(points.length - 1);
    }
  }

  return (
    <div
      role="group"
      aria-label="Cohort register. Each square is one student, riskiest first. Use the arrow keys to move and Enter to open."
      onKeyDown={onKeyDown}
      className="flex flex-wrap gap-1"
    >
      {points.map((point, index) => {
        const key = point.riskLevel ?? "none";
        const text = `${point.name}, year ${point.grade}, ${point.riskLevel ? RISK_LABELS[point.riskLevel] : "not scored"}${
          point.prob != null ? ` ${probability(point.prob)}` : ""
        }`;
        return (
          <button
            key={point.id}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            tabIndex={index === active ? 0 : -1}
            aria-label={text}
            title={text}
            onFocus={() => setActive(index)}
            onClick={() => onOpen(point.id)}
            style={key === "medium" ? { backgroundImage: HATCH } : undefined}
            className={`flex h-[22px] w-[22px] items-center justify-center rounded-[2px] ${SQUARE[key]} hover:outline hover:outline-2 hover:outline-ink`}
          >
            <RiskGlyph level={point.riskLevel} size={10} />
          </button>
        );
      })}
    </div>
  );
}

export function RegisterLegend() {
  const items = [
    { level: "high" as const, text: "High" },
    { level: "medium" as const, text: "Medium" },
    { level: "low" as const, text: "Low" },
    { level: null, text: "Not scored" },
  ];
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Legend">
      {items.map((item) => (
        <li key={item.text} className={`flex items-center gap-1.5 ${RISK_TEXT_CLASS[item.level ?? "none"]}`}>
          <RiskGlyph level={item.level} />
          <span className="text-ink">{item.text}</span>
        </li>
      ))}
    </ul>
  );
}
