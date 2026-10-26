import type { ReactNode } from "react";

import type { Summary } from "@/api/types";
import { Skeleton } from "@/components/Skeleton";
import { number, percent, signed } from "@/lib/format";

interface CellProps {
  label: string;
  value: ReactNode;
  change?: { text: string; good: boolean | null };
}

function Cell({ label, value, change }: CellProps) {
  return (
    <div className="px-4 py-4 sm:px-5">
      <dt className="eyebrow">{label}</dt>
      <dd className="m-0">
        <div className="font-serif text-4xl font-semibold leading-tight">{value}</div>
        {change && (
          <div
            className={`text-sm font-medium ${change.good === null ? "text-muted" : change.good ? "text-low" : "text-high"}`}
          >
            {change.text}
          </div>
        )}
      </dd>
    </div>
  );
}

function trend(delta: number | null, unit: string, higherIsBetter: boolean): CellProps["change"] {
  if (delta == null) return { text: "No earlier month to compare", good: null };
  if (Math.abs(delta) < 0.05) return { text: "Unchanged since last month", good: null };
  const arrow = delta > 0 ? "▲" : "▼";
  return { text: `${arrow} ${signed(delta)}${unit} since last month`, good: delta > 0 === higherIsBetter };
}

export function KpiBand({ summary }: { summary: Summary | undefined }) {
  if (!summary) {
    return (
      <div className="panel grid grid-cols-2 gap-4 p-5 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }
  const highDelta = summary.highRiskChange;
  return (
    <dl className="panel m-0 grid grid-cols-2 divide-line lg:grid-cols-4 lg:divide-x [&>div]:border-line [&>div:nth-child(n+3)]:border-t lg:[&>div:nth-child(n+3)]:border-t-0 [&>div:nth-child(even)]:border-l lg:[&>div:nth-child(even)]:border-l-0 lg:[&>div:not(:first-child)]:border-l">
      <Cell label="Students tracked" value={summary.studentsTracked.toLocaleString()} />
      <Cell
        label="Average attendance"
        value={percent(summary.avgAttendance)}
        change={trend(summary.attendanceChange, " pts", true)}
      />
      <Cell label="Average score" value={number(summary.avgScore)} change={trend(summary.scoreChange, "", true)} />
      <Cell
        label="High risk"
        value={summary.highRisk.toLocaleString()}
        change={
          summary.unscored === summary.studentsTracked
            ? { text: "Train a model to score students", good: null }
            : highDelta === 0
              ? { text: "Unchanged since last month", good: null }
              : { text: `${highDelta > 0 ? "▲" : "▼"} ${Math.abs(highDelta)} since last month`, good: highDelta < 0 }
        }
      />
    </dl>
  );
}
