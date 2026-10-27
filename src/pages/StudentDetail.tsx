import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";

import { messageOf } from "@/api/client";
import {
  useClasses,
  useDeleteStudent,
  useRecompute,
  useSaveFollowUp,
  useSaveRecord,
  useStudent,
  useUpdateStudent,
} from "@/api/hooks";
import type { FollowUpStatus, StudentDetail } from "@/api/types";
import { SeriesChart } from "@/components/Charts";
import { ConfirmModal } from "@/components/ConfirmModal";
import { FactorBars } from "@/components/FactorBars";
import { Field, describedBy } from "@/components/Field";
import { Modal } from "@/components/Modal";
import { RiskGauge } from "@/components/RiskGauge";
import { PanelSkeleton } from "@/components/Skeleton";
import { ErrorState, isNoModel } from "@/components/States";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";
import {
  STATUS_LABELS,
  classLabel,
  dateTime,
  monthLabel,
  number,
  percent,
  recentMonths,
  toApiMonth,
} from "@/lib/format";
import { editStudentSchema, monthlyRecordSchema, type EditStudentForm, type MonthlyRecordForm } from "@/lib/schemas";

const STATUSES = Object.keys(STATUS_LABELS) as FollowUpStatus[];

function whatIfLink(student: StudentDetail): string {
  const f = student.features;
  if (!f) return "/what-if";
  const params = new URLSearchParams({
    attendance: f.attendance.toFixed(0),
    score: f.score.toFixed(0),
    assignments: f.assignments.toFixed(0),
    failures: String(Math.round(f.failures)),
    late: f.late.toFixed(0),
    parent: String(Math.round(f.parent)),
    trend: f.trend.toFixed(1),
    grade: String(student.grade),
  });
  return `/what-if?${params.toString()}`;
}

function FollowUpPanel({ student, canEdit }: { student: StudentDetail; canEdit: boolean }) {
  const toast = useToast();
  const save = useSaveFollowUp(student.id);
  const [status, setStatus] = useState<FollowUpStatus>(student.followUp.status);
  const [notes, setNotes] = useState(student.followUp.notes);

  useEffect(() => {
    setStatus(student.followUp.status);
    setNotes(student.followUp.notes);
  }, [student.followUp.status, student.followUp.notes]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await save.mutateAsync({ status, notes });
      toast.success("Follow-up saved.");
    } catch (error) {
      toast.error(messageOf(error));
    }
  }

  const { updatedAt, updatedBy } = student.followUp;
  return (
    <section aria-labelledby="followup-title" className="panel p-5">
      <h2 id="followup-title" className="section-title">
        Follow-up
      </h2>
      <form onSubmit={(e) => void onSubmit(e)} className="mt-3 space-y-4">
        <Field id="followup-status" label="Status">
          <select
            id="followup-status"
            className="input"
            value={status}
            disabled={!canEdit}
            onChange={(e) => setStatus(e.target.value as FollowUpStatus)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </Field>
        <Field id="followup-notes" label="Notes" hint="Who you spoke to, what was agreed, when to look again.">
          <textarea
            id="followup-notes"
            className="input"
            maxLength={2000}
            value={notes}
            readOnly={!canEdit}
            aria-describedby="followup-notes-hint"
            onChange={(e) => setNotes(e.target.value)}
          />
        </Field>
        {canEdit ? (
          <button type="submit" className="btn btn-primary" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save follow-up"}
          </button>
        ) : (
          <p className="text-sm text-muted">You have read-only access, so follow-ups can't be changed.</p>
        )}
        {updatedAt && (
          <p className="text-sm text-muted">
            Last updated {dateTime(updatedAt)}
            {updatedBy ? ` by ${updatedBy}` : ""}.
          </p>
        )}
      </form>
    </section>
  );
}

function RecordModal({ student, onClose }: { student: StudentDetail; onClose: () => void }) {
  const toast = useToast();
  const save = useSaveRecord(student.id);
  const latest = student.months[student.months.length - 1];
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<MonthlyRecordForm>({
    resolver: zodResolver(monthlyRecordSchema),
    defaultValues: {
      month: recentMonths(1)[0],
      avgScore: student.features ? Math.round(student.features.score) : Number.NaN,
      attendancePct: student.features ? Math.round(student.features.attendance) : Number.NaN,
      assignmentsPct: student.features ? Math.round(student.features.assignments) : Number.NaN,
      lateArrivals: student.features ? Math.round(student.features.late) : Number.NaN,
      failedSubjects: student.features ? Math.round(student.features.failures) : Number.NaN,
      guardianEngagement: student.features ? Math.round(student.features.parent) : Number.NaN,
    },
  });

  const fields: { key: Exclude<keyof MonthlyRecordForm, "month">; label: string; step: string }[] = [
    { key: "avgScore", label: "Average score (0–100)", step: "0.1" },
    { key: "attendancePct", label: "Attendance % (0–100)", step: "0.1" },
    { key: "assignmentsPct", label: "Assignments submitted % (0–100)", step: "0.1" },
    { key: "lateArrivals", label: "Late arrivals", step: "1" },
    { key: "failedSubjects", label: "Backlogs", step: "1" },
    { key: "guardianEngagement", label: "Guardian engagement (1–5)", step: "1" },
  ];

  const onSubmit = handleSubmit(async (values) => {
    try {
      await save.mutateAsync({ ...values, month: toApiMonth(values.month) });
      toast.success(`${monthLabel(values.month)} saved and ${student.name} re-scored.`);
      onClose();
    } catch (error) {
      toast.error(messageOf(error));
    }
  });

  return (
    <Modal title="Add or replace a month" onClose={onClose}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Field
          id="rec-month"
          label="Month"
          error={errors.month?.message}
          hint={latest ? `Latest on record: ${monthLabel(latest)}. Saving a month that exists replaces it.` : undefined}
        >
          <input
            id="rec-month"
            type="month"
            className="input"
            aria-invalid={errors.month ? true : undefined}
            aria-describedby={describedBy("rec-month", errors.month?.message)}
            {...register("month")}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => (
            <Field key={f.key} id={`rec-${f.key}`} label={f.label} error={errors[f.key]?.message}>
              <input
                id={`rec-${f.key}`}
                type="number"
                inputMode="decimal"
                step={f.step}
                className="input num"
                aria-invalid={errors[f.key] ? true : undefined}
                aria-describedby={describedBy(`rec-${f.key}`, errors[f.key]?.message)}
                {...register(f.key, { valueAsNumber: true })}
              />
            </Field>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save month"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EditModal({ student, onClose }: { student: StudentDetail; onClose: () => void }) {
  const toast = useToast();
  const classes = useClasses();
  const update = useUpdateStudent(student.id);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EditStudentForm>({
    resolver: zodResolver(editStudentSchema),
    defaultValues: { name: student.name, classId: student.classId, guardianContact: student.guardianContact ?? "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await update.mutateAsync({
        name: values.name,
        classId: values.classId,
        guardianContact: values.guardianContact || null,
      });
      toast.success("Student details updated.");
      onClose();
    } catch (error) {
      toast.error(messageOf(error));
    }
  });

  return (
    <Modal title="Edit student" onClose={onClose}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Field id="edit-name" label="Full name" error={errors.name?.message}>
          <input
            id="edit-name"
            className="input"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={describedBy("edit-name", errors.name?.message)}
            {...register("name")}
          />
        </Field>
        <Field id="edit-class" label="Class" error={errors.classId?.message}>
          <select id="edit-class" className="input" {...register("classId", { valueAsNumber: true })}>
            {classes.data?.items.map((klass) => (
              <option key={klass.id} value={klass.id}>
                {classLabel(klass)} ({klass.academicYear})
              </option>
            ))}
          </select>
        </Field>
        <Field id="edit-guardian" label="Guardian contact" error={errors.guardianContact?.message}>
          <input id="edit-guardian" className="input" {...register("guardianContact")} />
        </Field>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function StudentDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const student = useStudent(id);
  const recompute = useRecompute(id);
  const remove = useDeleteStudent();
  const [dialog, setDialog] = useState<"record" | "edit" | "delete" | null>(null);

  useDocumentTitle(student.data?.name ?? "Student");

  if (student.isError) {
    return (
      <>
        <Link to="/students" className="mb-4 inline-block font-semibold underline underline-offset-2">
          ← All students
        </Link>
        <ErrorState error={student.error} onRetry={() => void student.refetch()} />
      </>
    );
  }
  if (!student.data) {
    return (
      <div className="space-y-4">
        <PanelSkeleton lines={2} />
        <PanelSkeleton lines={6} />
      </div>
    );
  }

  const data = student.data;
  const canWrite = can("admin", "teacher");
  const f = data.features;

  async function onRecompute() {
    try {
      await recompute.mutateAsync();
      toast.success("Score refreshed.");
    } catch (error) {
      toast.error(
        isNoModel(error)
          ? "There is no trained model yet. An administrator can train one on the Model page."
          : messageOf(error),
      );
    }
  }

  async function onDelete() {
    try {
      await remove.mutateAsync(data.id);
      toast.success(`${data.name} was removed from the register.`);
      navigate("/students", { replace: true });
    } catch (error) {
      toast.error(messageOf(error));
      setDialog(null);
    }
  }

  const rows: [string, string][] = f
    ? [
        ["Attendance", percent(f.attendance, 1)],
        ["Average score", number(f.score)],
        ["Assignments submitted", percent(f.assignments, 1)],
        ["Backlogs", number(f.failures, 0)],
        ["Late arrivals a month", number(f.late)],
        ["Guardian engagement", `${number(f.parent, 1)} of 5`],
        ["Score trend a month", `${f.trend > 0 ? "+" : ""}${number(f.trend)} points`],
      ]
    : [];

  return (
    <>
      <Link to="/students" className="mb-4 inline-block font-semibold underline underline-offset-2">
        ← All students
      </Link>

      <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-ink/60 pb-4">
        <div>
          <p className="eyebrow mb-1">
            {data.studentCode} · {data.department} · Year {data.grade} · Section {data.section}
          </p>
          <h1 className="page-title">{data.name}</h1>
          {data.guardianContact && <p className="mt-1 text-muted">Guardian: {data.guardianContact}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {f && (
            <Link to={whatIfLink(data)} className="btn">
              Try what-if
            </Link>
          )}
          {canWrite && (
            <>
              <button type="button" className="btn" onClick={() => setDialog("record")}>
                Add month
              </button>
              <button type="button" className="btn" onClick={() => void onRecompute()} disabled={recompute.isPending}>
                {recompute.isPending ? "Scoring…" : "Re-score"}
              </button>
              <button type="button" className="btn" onClick={() => setDialog("edit")}>
                Edit
              </button>
            </>
          )}
          {can("admin") && (
            <button type="button" className="btn btn-danger" onClick={() => setDialog("delete")}>
              Delete
            </button>
          )}
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_1fr]">
        <section aria-labelledby="risk-title" className="panel p-5">
          <h2 id="risk-title" className="section-title mb-3">
            Dropout risk
          </h2>
          <RiskGauge prob={data.prob} level={data.riskLevel} />
          {data.nextTermScore != null && (
            <p className="mt-4 border-t border-line pt-3 text-sm">
              Expected score next term: <strong className="num">{number(data.nextTermScore)}</strong>
            </p>
          )}
          {data.modelVersion != null && (
            <p className="mt-1 text-sm text-muted">
              Model v{data.modelVersion}, scored {dateTime(data.predictedAt)}
            </p>
          )}
          {data.prob == null && (
            <p className="mt-3 text-sm text-muted">
              {data.months.length === 0
                ? "No monthly records yet, so there is nothing to score."
                : "Not scored yet. An administrator needs to train a model."}
            </p>
          )}
          <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
            A prediction supports a conversation with the student. It should never be the only basis for action.
          </p>
        </section>

        <section aria-labelledby="series-title" className="panel p-5">
          <h2 id="series-title" className="section-title mb-3">
            Month by month
          </h2>
          {data.months.length >= 2 ? (
            <SeriesChart months={data.months} scores={data.scoreSeries} attendance={data.attSeries} />
          ) : (
            <p className="text-muted">Two or more months of records are needed to draw a trend.</p>
          )}
          {data.months.length > 0 && (
            <details className="mt-3 text-sm">
              <summary className="cursor-pointer font-semibold">Show the figures as a table</summary>
              <div className="table-wrap mt-2">
                <table className="data-table">
                  <caption className="sr-only">Monthly score and attendance</caption>
                  <thead>
                    <tr>
                      <th scope="col">Month</th>
                      <th scope="col">Score</th>
                      <th scope="col">Attendance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.months.map((month, i) => (
                      <tr key={month}>
                        <th scope="row" className="text-left font-normal">
                          {monthLabel(month)}
                        </th>
                        <td className="num">{number(data.scoreSeries[i])}</td>
                        <td className="num">{percent(data.attSeries[i], 1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </section>

        <section aria-labelledby="factors-title" className="panel p-5">
          <h2 id="factors-title" className="section-title mb-3">
            What is driving this score
          </h2>
          <FactorBars factors={data.factors} />
        </section>

        <section aria-labelledby="next-title" className="panel p-5">
          <h2 id="next-title" className="section-title mb-3">
            Suggested next steps
          </h2>
          {data.suggestedActions.length > 0 ? (
            <ul className="list-disc space-y-2 pl-5">
              {data.suggestedActions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">Suggestions appear once the student has been scored.</p>
          )}
        </section>

        {rows.length > 0 && (
          <section aria-labelledby="features-title" className="panel p-5">
            <h2 id="features-title" className="section-title mb-3">
              Current figures
            </h2>
            <dl className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-2 text-sm">
              {rows.map(([label, value]) => (
                <div key={label} className="contents">
                  <dt className="text-muted">{label}</dt>
                  <dd className="num text-right font-semibold">{value}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        <FollowUpPanel student={data} canEdit={canWrite} />
      </div>

      {dialog === "record" && <RecordModal student={data} onClose={() => setDialog(null)} />}
      {dialog === "edit" && <EditModal student={data} onClose={() => setDialog(null)} />}
      {dialog === "delete" && (
        <ConfirmModal
          title="Delete this student?"
          message={`${data.name} and all of their monthly records, predictions and notes will be permanently removed. This can't be undone.`}
          confirmLabel="Delete student"
          busy={remove.isPending}
          onConfirm={() => void onDelete()}
          onCancel={() => setDialog(null)}
        />
      )}
    </>
  );
}
