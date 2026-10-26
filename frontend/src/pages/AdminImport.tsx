import { useRef, useState } from "react";

import { messageOf } from "@/api/client";
import { useImport } from "@/api/hooks";
import type { ImportResult } from "@/api/types";
import { AdminTabs } from "@/components/AdminTabs";
import { PageHeader } from "@/components/PageHeader";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";

const COLUMNS: [string, string][] = [
  ["student_code", "Student ID, unique per student (required)"],
  ["name", "Full name (required)"],
  ["department", "Programme or department (required)"],
  ["year", "Year of study, 1 to 6 (required)"],
  ["section", "Section (required)"],
  ["month", "YYYY-MM or YYYY-MM-DD (required)"],
  ["avg_score", "Average score, 0 to 100 (required)"],
  ["attendance_pct", "Attendance, 0 to 100 (required)"],
  ["assignments_pct", "Assignments submitted, 0 to 100 (required)"],
  ["late_arrivals", "Late arrivals that month (required)"],
  ["failed_subjects", "Backlogs, subjects failed (required)"],
  ["guardian_engagement", "1 to 5 (required)"],
  ["academic_year", "For example 2026-27 (optional)"],
  ["guardian_contact", "Phone or email (optional)"],
  ["dropped_out", "1 or 0, if the outcome is known. Used for training (optional)"],
];

const MAX_ISSUES_SHOWN = 200;

export function AdminImportPage() {
  useDocumentTitle("Import data");
  const toast = useToast();
  const run = useImport();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [skipInvalid, setSkipInvalid] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  async function check() {
    if (!file) return;
    try {
      setResult(await run.mutateAsync({ file, dryRun: true, skipInvalid }));
    } catch (error) {
      setResult(null);
      toast.error(messageOf(error));
    }
  }

  async function commit() {
    if (!file) return;
    try {
      const done = await run.mutateAsync({ file, dryRun: false, skipInvalid });
      setResult(done);
      if (done.imported) {
        toast.success(`Imported ${done.records} monthly records for ${done.students} students.`);
        setFile(null);
        if (input.current) input.current.value = "";
      } else {
        toast.error("Nothing was imported. Fix the problems below, or tick “skip rows with problems”.");
      }
    } catch (error) {
      toast.error(messageOf(error));
    }
  }

  const problems = result?.issues ?? [];
  const canImport = result !== null && result.dryRun && result.rowsValid > 0 && (problems.length === 0 || skipInvalid);
  const previewColumns = result && result.preview.length > 0 ? Object.keys(result.preview[0]) : [];

  return (
    <>
      <PageHeader title="Administration" eyebrow="Import data">
        Upload a CSV of monthly records. Every row is checked first, and nothing is saved until you confirm.
      </PageHeader>
      <AdminTabs />

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
        <div className="space-y-6">
          <form
            className="panel space-y-4 p-5"
            onSubmit={(e) => {
              e.preventDefault();
              void check();
            }}
          >
            <div>
              <label htmlFor="csv-file" className="field-label">
                CSV file (up to 5 MB)
              </label>
              <input
                ref={input}
                id="csv-file"
                type="file"
                accept=".csv,text/csv"
                className="input !py-1.5"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setResult(null);
                }}
              />
              <p className="field-hint">
                New to this?{" "}
                <a className="font-semibold underline" href="/import-template.csv" download>
                  Download the template
                </a>
                .
              </p>
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-brand"
                checked={skipInvalid}
                onChange={(e) => {
                  setSkipInvalid(e.target.checked);
                  setResult(null);
                }}
              />
              <span>Skip rows with problems and import the rest. Otherwise one bad row stops the whole import.</span>
            </label>
            <div className="flex flex-wrap gap-2">
              <button type="submit" className="btn" disabled={!file || run.isPending}>
                {run.isPending && result === null ? "Checking…" : "Check file"}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!canImport || run.isPending}
                onClick={() => void commit()}
              >
                {run.isPending && result !== null ? "Importing…" : "Import"}
              </button>
            </div>
          </form>

          {result && (
            <section aria-labelledby="result-title" aria-live="polite" className="space-y-4">
              <h2 id="result-title" className="section-title">
                {result.dryRun ? "Check result" : result.imported ? "Import finished" : "Nothing imported"}
              </h2>
              <dl className="grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
                {[
                  ["Rows read", result.rowsRead],
                  ["Rows valid", result.rowsValid],
                  ["Students", result.students],
                  ["Problems", problems.length],
                ].map(([label, value]) => (
                  <div key={label} className="bg-surface px-4 py-3">
                    <dt className="eyebrow">{label}</dt>
                    <dd className="num m-0 text-2xl font-semibold">{value}</dd>
                  </div>
                ))}
              </dl>

              {problems.length > 0 && (
                <div role="alert">
                  <h3 className="font-semibold text-high">
                    {problems.length} {problems.length === 1 ? "problem" : "problems"} found
                  </h3>
                  <div className="table-wrap mt-2 max-h-80 overflow-y-auto border border-line">
                    <table className="data-table">
                      <caption className="sr-only">Rows that failed validation</caption>
                      <thead>
                        <tr>
                          <th scope="col">Row</th>
                          <th scope="col">Column</th>
                          <th scope="col">Problem</th>
                        </tr>
                      </thead>
                      <tbody>
                        {problems.slice(0, MAX_ISSUES_SHOWN).map((issue, index) => (
                          <tr key={`${issue.row}-${issue.column}-${index}`}>
                            <td className="num">{issue.row}</td>
                            <td className="num text-sm">{issue.column ?? "–"}</td>
                            <td>{issue.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {problems.length > MAX_ISSUES_SHOWN && (
                    <p className="mt-1 text-sm text-muted">
                      Showing the first {MAX_ISSUES_SHOWN}. Fix these and check again to see the rest.
                    </p>
                  )}
                </div>
              )}

              {previewColumns.length > 0 && (
                <div>
                  <h3 className="font-semibold">Preview of the first rows</h3>
                  <div className="table-wrap mt-2 border border-line">
                    <table className="data-table">
                      <caption className="sr-only">First valid rows</caption>
                      <thead>
                        <tr>
                          {previewColumns.map((column) => (
                            <th key={column} scope="col">
                              {column}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.preview.map((row, index) => (
                          <tr key={index}>
                            {previewColumns.map((column) => (
                              <td key={column} className="num text-sm">
                                {row[column]}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}
        </div>

        <aside aria-labelledby="columns-title">
          <h2 id="columns-title" className="section-title mb-2">
            Columns
          </h2>
          <p className="mb-3 text-sm text-muted">
            One row per student per month. The header row must use these exact names.
          </p>
          <dl className="space-y-2 text-sm">
            {COLUMNS.map(([name, description]) => (
              <div key={name}>
                <dt className="num font-semibold">{name}</dt>
                <dd className="m-0 text-muted">{description}</dd>
              </div>
            ))}
          </dl>
        </aside>
      </div>
    </>
  );
}
