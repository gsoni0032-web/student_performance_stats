import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { exportStudents, useClasses, useStudents, type StudentListParams } from "@/api/hooks";
import { messageOf } from "@/api/client";
import type { FollowUpStatus, RiskLevel, StudentFilters } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { RiskBadge } from "@/components/RiskBadge";
import { Skeleton } from "@/components/Skeleton";
import { Sparkline, trendLabel } from "@/components/Sparkline";
import { EmptyState, ErrorState } from "@/components/States";
import { useAuth } from "@/hooks/useAuth";
import { useDebounced } from "@/hooks/useDebounced";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";
import { STATUS_LABELS, classLabel, number, percent } from "@/lib/format";

type SortKey = StudentListParams["sort"];

const SORTS: readonly SortKey[] = ["risk", "name", "code", "grade", "status"];
const RISKS: readonly (RiskLevel | "unscored")[] = ["high", "medium", "low", "unscored"];
const STATUSES = Object.keys(STATUS_LABELS) as FollowUpStatus[];
const PAGE_SIZE = 20;

function pick<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return allowed.find((item) => item === value);
}

interface SortHeaderProps {
  label: string;
  field: SortKey;
  sort: SortKey;
  order: "asc" | "desc";
  onSort: (field: SortKey) => void;
}

function SortHeader({ label, field, sort, order, onSort }: SortHeaderProps) {
  const active = sort === field;
  return (
    <th scope="col" aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}>
      <button
        type="button"
        className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-label hover:text-ink"
        onClick={() => onSort(field)}
      >
        {label}
        <span aria-hidden="true" className="w-3">
          {active ? (order === "asc" ? "▲" : "▼") : ""}
        </span>
      </button>
    </th>
  );
}

export function StudentsPage() {
  useDocumentTitle("Students");
  const { can } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const classes = useClasses();
  const [exporting, setExporting] = useState(false);

  const query = params.get("q") ?? "";
  const debouncedQuery = useDebounced(query, 300);
  const page = Math.max(1, Number(params.get("page")) || 1);
  const sort = pick(params.get("sort"), SORTS) ?? "risk";
  const order =
    params.get("order") === "asc" ? "asc" : params.get("order") === "desc" ? "desc" : sort === "risk" ? "desc" : "asc";
  const classId = Number(params.get("classId")) || undefined;
  const risk = pick(params.get("risk"), RISKS);
  const status = pick(params.get("status"), STATUSES);

  const filters: StudentFilters = { q: debouncedQuery.trim() || undefined, classId, risk, status };
  const students = useStudents({ ...filters, page, pageSize: PAGE_SIZE, sort, order });
  const filtered = Boolean(query || classId || risk || status);

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next, { replace: true });
  }

  function onSort(field: SortKey) {
    if (field === sort) update({ sort: field, order: order === "asc" ? "desc" : "asc", page: null });
    else update({ sort: field, order: field === "risk" ? "desc" : "asc", page: null });
  }

  async function onExport() {
    setExporting(true);
    try {
      await exportStudents(filters);
    } catch (error) {
      toast.error(messageOf(error));
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Students"
        eyebrow="Register"
        actions={
          <>
            <button type="button" className="btn" onClick={() => void onExport()} disabled={exporting}>
              {exporting ? "Preparing…" : "Export CSV"}
            </button>
            {can("admin", "teacher") && (
              <Link to="/students/new" className="btn btn-primary">
                Add student
              </Link>
            )}
          </>
        }
      >
        Search the register, filter by class or risk, and open a student to log a follow-up.
      </PageHeader>

      <form
        role="search"
        aria-label="Filter students"
        className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <div>
          <label htmlFor="q" className="field-label">
            Search
          </label>
          <input
            id="q"
            type="search"
            className="input"
            placeholder="Name or student ID"
            value={query}
            onChange={(e) => update({ q: e.target.value })}
          />
        </div>
        <div>
          <label htmlFor="classId" className="field-label">
            Class
          </label>
          <select
            id="classId"
            className="input"
            value={classId ?? ""}
            onChange={(e) => update({ classId: e.target.value })}
          >
            <option value="">All classes</option>
            {classes.data?.items.map((klass) => (
              <option key={klass.id} value={klass.id}>
                {classLabel(klass)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="risk" className="field-label">
            Risk
          </label>
          <select id="risk" className="input" value={risk ?? ""} onChange={(e) => update({ risk: e.target.value })}>
            <option value="">All students</option>
            <option value="high">High risk</option>
            <option value="medium">Medium risk</option>
            <option value="low">Low risk</option>
            <option value="unscored">Not scored</option>
          </select>
        </div>
        <div>
          <label htmlFor="status" className="field-label">
            Follow-up
          </label>
          <select
            id="status"
            className="input"
            value={status ?? ""}
            onChange={(e) => update({ status: e.target.value })}
          >
            <option value="">Any status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
      </form>

      {students.isError ? (
        <ErrorState error={students.error} onRetry={() => void students.refetch()} />
      ) : !students.data ? (
        <div className="space-y-2" role="status" aria-label="Loading students">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : students.data.items.length === 0 ? (
        <EmptyState
          title={filtered ? "No students match these filters" : "No students yet"}
          action={
            filtered ? (
              <button type="button" className="btn" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                Clear filters
              </button>
            ) : can("admin", "teacher") ? (
              <Link to="/students/new" className="btn btn-primary">
                Add a student
              </Link>
            ) : undefined
          }
        >
          {filtered
            ? "Try a different search, or clear the filters to see everyone."
            : "Add students one at a time, or ask an administrator to import a CSV."}
        </EmptyState>
      ) : (
        <>
          <div className="table-wrap" aria-busy={students.isFetching}>
            <table className="data-table min-w-[54rem]">
              <caption className="sr-only">
                Students, page {students.data.page} of {students.data.pages}, sorted by {sort}{" "}
                {order === "asc" ? "ascending" : "descending"}
              </caption>
              <thead>
                <tr>
                  <SortHeader label="Student" field="name" sort={sort} order={order} onSort={onSort} />
                  <SortHeader label="ID" field="code" sort={sort} order={order} onSort={onSort} />
                  <SortHeader label="Class" field="grade" sort={sort} order={order} onSort={onSort} />
                  <th scope="col">Attendance</th>
                  <th scope="col">Score</th>
                  <th scope="col">Score trend</th>
                  <SortHeader label="Risk" field="risk" sort={sort} order={order} onSort={onSort} />
                  <SortHeader label="Follow-up" field="status" sort={sort} order={order} onSort={onSort} />
                </tr>
              </thead>
              <tbody>
                {students.data.items.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <Link to={`/students/${student.id}`} className="font-semibold underline-offset-2 hover:underline">
                        {student.name}
                      </Link>
                    </td>
                    <td className="num text-sm">{student.studentCode}</td>
                    <td className="text-sm">
                      {student.department}
                      <br />
                      <span className="text-muted">
                        Year {student.grade} · {student.section}
                      </span>
                    </td>
                    <td className="num">{percent(student.features?.attendance)}</td>
                    <td className="num">{number(student.features?.score)}</td>
                    <td>
                      <Sparkline values={student.scoreSeries} label={trendLabel("Score", student.scoreSeries)} />
                    </td>
                    <td>
                      <RiskBadge level={student.riskLevel} prob={student.prob} />
                    </td>
                    <td className="text-sm">{STATUS_LABELS[student.followUpStatus]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={students.data.page}
            pages={students.data.pages}
            total={students.data.total}
            pageSize={students.data.pageSize}
            onPage={(next) => update({ page: String(next) })}
          />
        </>
      )}
    </>
  );
}
