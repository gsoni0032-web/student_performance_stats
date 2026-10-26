import type { ClassOut, FollowUpStatus, RiskLevel } from "@/api/types";

export const STATUS_LABELS: Record<FollowUpStatus, string> = {
  not_started: "Not started",
  guardian_contacted: "Guardian contacted",
  support_plan_active: "Support plan active",
  resolved: "Resolved",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  high: "High risk",
  medium: "Medium risk",
  low: "Low risk",
};

export function percent(value: number | null | undefined, digits = 0): string {
  return value == null ? "–" : `${value.toFixed(digits)}%`;
}

export function probability(value: number | null | undefined): string {
  return value == null ? "–" : `${Math.round(value * 100)}%`;
}

export function number(value: number | null | undefined, digits = 1): string {
  return value == null ? "–" : value.toFixed(digits);
}

export function signed(value: number | null | undefined, digits = 1): string {
  if (value == null) return "–";
  const text = Math.abs(value).toFixed(digits);
  return value > 0 ? `+${text}` : value < 0 ? `−${text}` : text;
}

export function monthLabel(iso: string | null | undefined): string {
  if (!iso) return "–";
  const [year, month] = iso.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

export function dateTime(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "–";
}

export function ordinalYear(grade: number): string {
  return `Year ${grade}`;
}

/** "Computer Science · Year 2 · B" — how a class is named everywhere in the interface. */
export function classLabel(klass: Pick<ClassOut, "department" | "grade" | "section">): string {
  return `${klass.department} · Year ${klass.grade} · ${klass.section}`;
}

/** The `count` calendar months before `now`, oldest first, as YYYY-MM. */
export function recentMonths(count: number, now: Date = new Date()): string[] {
  const months: string[] = [];
  for (let back = count; back >= 1; back -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth() - back, 1);
    months.push(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`);
  }
  return months;
}

/** The API stores a month as its first day. */
export function toApiMonth(month: string): string {
  return `${month}-01`;
}

/** The month after a YYYY-MM value. */
export function nextMonth(month: string): string {
  const [year, number] = month.split("-").map(Number);
  const date = new Date(year, number, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}
