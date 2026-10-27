import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { CohortPoint, GradeRisk, RiskLevel } from "@/api/types";
import { RiskGlyph } from "@/components/RiskGlyph";
import { RISK_LABELS, monthLabel } from "@/lib/format";

const AXIS = { fontSize: 12, fill: "currentColor" };
const TOOLTIP_STYLE = {
  background: "rgb(var(--surface))",
  border: "1px solid rgb(var(--line))",
  borderRadius: 6,
  color: "rgb(var(--ink))",
};

function dotFor(level: RiskLevel) {
  const cls = level === "high" ? "text-high" : level === "medium" ? "text-medium" : "text-low";
  return function Dot(props: unknown) {
    const { cx, cy } = props as { cx: number; cy: number };
    return (
      <g transform={`translate(${cx - 5} ${cy - 5})`} className={cls}>
        <RiskGlyph level={level} size={10} />
      </g>
    );
  };
}

/** Attendance against score. Each risk band has its own shape. */
export function AttendanceScoreScatter({ points }: { points: CohortPoint[] }) {
  const usable = points.filter((p) => p.attendance != null && p.score != null && p.riskLevel);
  const by = (level: RiskLevel) => usable.filter((p) => p.riskLevel === level);
  return (
    <figure className="m-0">
      <div
        className="h-72 text-muted"
        role="img"
        aria-label={`Scatter chart of attendance against average score for ${usable.length} scored students. Students with low attendance and low scores are more likely to be high risk.`}
      >
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 0 }}>
            <CartesianGrid stroke="currentColor" strokeOpacity={0.18} />
            <XAxis
              type="number"
              dataKey="attendance"
              name="Attendance"
              unit="%"
              domain={[40, 100]}
              tick={AXIS}
              label={{
                value: "Attendance (%)",
                position: "insideBottom",
                offset: -14,
                fill: "currentColor",
                fontSize: 12,
              }}
            />
            <YAxis
              type="number"
              dataKey="score"
              name="Average score"
              domain={[20, 100]}
              tick={AXIS}
              width={36}
              label={{ value: "Score", angle: -90, position: "insideLeft", fill: "currentColor", fontSize: 12 }}
            />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={TOOLTIP_STYLE} />
            <Scatter name="Low risk" data={by("low")} shape={dotFor("low")} isAnimationActive={false} />
            <Scatter name="Medium risk" data={by("medium")} shape={dotFor("medium")} isAnimationActive={false} />
            <Scatter name="High risk" data={by("high")} shape={dotFor("high")} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-2 flex flex-wrap gap-x-4 text-sm">
        {(["high", "medium", "low"] as const).map((level) => (
          <span
            key={level}
            className={`inline-flex items-center gap-1.5 ${level === "high" ? "text-high" : level === "medium" ? "text-medium" : "text-low"}`}
          >
            <RiskGlyph level={level} />
            <span className="text-ink">{RISK_LABELS[level]}</span>
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

/** Stacked bars per year of study. Bands differ by fill pattern as well as colour. */
export function RiskByYearBars({ data }: { data: GradeRisk[] }) {
  const rows = data.map((d) => ({ ...d, name: `Year ${d.grade}` }));
  return (
    <figure className="m-0">
      <div
        className="h-64 text-muted"
        role="img"
        aria-label="Stacked bar chart of students by risk band for each year of study. A table with the same numbers follows."
      >
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <pattern id="pat-high" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" style={{ fill: "rgb(var(--high))" }} />
                <rect width="2.2" height="6" style={{ fill: "rgb(var(--surface))" }} />
              </pattern>
              <pattern id="pat-medium" width="5" height="5" patternUnits="userSpaceOnUse">
                <rect width="5" height="5" style={{ fill: "rgb(var(--medium-bg))" }} />
                <circle cx="2.5" cy="2.5" r="1.4" style={{ fill: "rgb(var(--medium))" }} />
              </pattern>
            </defs>
            <CartesianGrid stroke="currentColor" strokeOpacity={0.18} vertical={false} />
            <XAxis dataKey="name" tick={AXIS} />
            <YAxis tick={AXIS} width={32} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "rgb(var(--sunken))", opacity: 0.5 }} />
            <Legend wrapperStyle={{ fontSize: 13 }} />
            <Bar
              dataKey="low"
              name="Low"
              stackId="a"
              fill="rgb(var(--low-bg))"
              stroke="rgb(var(--low))"
              strokeWidth={1}
              isAnimationActive={false}
            />
            <Bar
              dataKey="medium"
              name="Medium"
              stackId="a"
              fill="url(#pat-medium)"
              stroke="rgb(var(--medium))"
              strokeWidth={1}
              isAnimationActive={false}
            />
            <Bar
              dataKey="high"
              name="High"
              stackId="a"
              fill="url(#pat-high)"
              stroke="rgb(var(--high))"
              strokeWidth={1}
              isAnimationActive={false}
            >
              <LabelList
                dataKey="high"
                position="top"
                fontSize={12}
                fill="currentColor"
                formatter={(v: number) => (v > 0 ? v : "")}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>Students by risk band and year of study</caption>
        <thead>
          <tr>
            <th scope="col">Year</th>
            <th scope="col">Low</th>
            <th scope="col">Medium</th>
            <th scope="col">High</th>
            <th scope="col">Not scored</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.grade}>
              <th scope="row">{r.name}</th>
              <td>{r.low}</td>
              <td>{r.medium}</td>
              <td>{r.high}</td>
              <td>{r.unscored}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

/** Score and attendance over the months on record. Different line styles keep the two apart without colour. */
export function SeriesChart({
  months,
  scores,
  attendance,
}: {
  months: string[];
  scores: number[];
  attendance: number[];
}) {
  const rows = months.map((m, i) => ({ month: monthLabel(m), Score: scores[i], Attendance: attendance[i] }));
  return (
    <div
      className="h-64 text-muted"
      role="img"
      aria-label={`Line chart of monthly average score and attendance over the last ${rows.length} months.`}
    >
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.18} vertical={false} />
          <XAxis dataKey="month" tick={AXIS} />
          <YAxis domain={[0, 100]} tick={AXIS} width={34} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontSize: 13 }} />
          <Line
            type="monotone"
            dataKey="Score"
            strokeWidth={2.5}
            dot={{ r: 3 }}
            stroke="rgb(var(--brand))"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="Attendance"
            strokeWidth={2.5}
            strokeDasharray="6 4"
            dot={{ r: 3, strokeWidth: 0 }}
            stroke="rgb(var(--ink))"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
