import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

import { api, ApiError, messageOf } from "@/api/client";
import { useClasses, useCreateStudent } from "@/api/hooks";
import type { MonthlyRecordInput, StudentDetail } from "@/api/types";
import { Field, describedBy } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/States";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";
import { classLabel, monthLabel, nextMonth, recentMonths, toApiMonth } from "@/lib/format";
import { addStudentSchema, type AddStudentForm, type MonthlyRecordForm } from "@/lib/schemas";

const COLUMNS = [
  { key: "avgScore", label: "Average score", short: "Score", step: "0.1" },
  { key: "attendancePct", label: "Attendance %", short: "Attendance %", step: "0.1" },
  { key: "assignmentsPct", label: "Assignments submitted %", short: "Assignments %", step: "0.1" },
  { key: "lateArrivals", label: "Late arrivals", short: "Late arrivals", step: "1" },
  { key: "failedSubjects", label: "Backlogs", short: "Backlogs", step: "1" },
  { key: "guardianEngagement", label: "Guardian engagement (1 to 5)", short: "Guardian (1–5)", step: "1" },
] as const;

function blankRow(month: string): MonthlyRecordForm {
  return {
    month,
    avgScore: Number.NaN,
    attendancePct: Number.NaN,
    assignmentsPct: Number.NaN,
    lateArrivals: Number.NaN,
    failedSubjects: Number.NaN,
    guardianEngagement: Number.NaN,
  };
}

function toInput(row: MonthlyRecordForm): MonthlyRecordInput {
  return { ...row, month: toApiMonth(row.month) };
}

export function StudentNewPage() {
  useDocumentTitle("Add student");
  const navigate = useNavigate();
  const toast = useToast();
  const client = useQueryClient();
  const classes = useClasses();
  const create = useCreateStudent();

  const {
    register,
    handleSubmit,
    control,
    getValues,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<AddStudentForm>({
    resolver: zodResolver(addStudentSchema),
    defaultValues: {
      studentCode: "",
      name: "",
      guardianContact: "",
      records: recentMonths(6).map(blankRow),
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "records" });

  function addMonth() {
    const rows = getValues("records");
    const last = rows[rows.length - 1]?.month;
    append(blankRow(last ? nextMonth(last) : (recentMonths(1)[0] ?? "")));
  }

  const onSubmit = handleSubmit(async (values) => {
    const [first, ...rest] = values.records.map(toInput);
    let created: StudentDetail;
    try {
      created = await create.mutateAsync({
        studentCode: values.studentCode,
        name: values.name,
        classId: values.classId,
        guardianContact: values.guardianContact || null,
        record: first,
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setError("studentCode", { message: error.message });
      }
      toast.error(messageOf(error));
      return;
    }

    for (const record of rest) {
      try {
        await api<StudentDetail>(`/students/${created.id}/records`, { method: "POST", body: record });
      } catch (error) {
        toast.error(
          `${values.name} was added, but ${monthLabel(record.month.slice(0, 7))} could not be saved: ${messageOf(error)}`,
        );
        await client.invalidateQueries();
        navigate(`/students/${created.id}`);
        return;
      }
    }
    if (rest.length > 0) await client.invalidateQueries();
    toast.success(`${values.name} was added to the register.`);
    navigate(`/students/${created.id}`);
  });

  const recordProblems: string[] = [];
  fields.forEach((_, index) => {
    const row = errors.records?.[index];
    if (!row) return;
    if (row.month?.message) recordProblems.push(`Row ${index + 1}: ${row.month.message}`);
    for (const column of COLUMNS) {
      const message = row[column.key]?.message;
      if (message) recordProblems.push(`Row ${index + 1}: ${message}`);
    }
  });

  return (
    <>
      <PageHeader title="Add student" eyebrow="Register">
        Enter the student's details, then the monthly figures you already hold. The student is scored as soon as the
        record is saved.
      </PageHeader>

      {classes.isError ? (
        <ErrorState error={classes.error} onRetry={() => void classes.refetch()} />
      ) : (
        <form onSubmit={onSubmit} noValidate className="max-w-4xl space-y-10">
          <fieldset className="space-y-5">
            <legend className="section-title mb-3">Student</legend>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field id="name" label="Full name" error={errors.name?.message}>
                <input
                  id="name"
                  className="input"
                  autoComplete="off"
                  aria-invalid={errors.name ? true : undefined}
                  aria-describedby={describedBy("name", errors.name?.message)}
                  {...register("name")}
                />
              </Field>
              <Field
                id="studentCode"
                label="Student ID"
                hint="The roll or enrolment number, for example CS24-0101."
                error={errors.studentCode?.message}
              >
                <input
                  id="studentCode"
                  className="input"
                  autoComplete="off"
                  aria-invalid={errors.studentCode ? true : undefined}
                  aria-describedby={describedBy(
                    "studentCode",
                    errors.studentCode?.message,
                    "The roll or enrolment number, for example CS24-0101.",
                  )}
                  {...register("studentCode")}
                />
              </Field>
              <Field
                id="classId"
                label="Class"
                error={errors.classId?.message}
                hint={
                  classes.data && classes.data.items.length === 0
                    ? "No classes are available to you. An administrator needs to create one or assign you to one."
                    : undefined
                }
              >
                <select
                  id="classId"
                  className="input"
                  aria-invalid={errors.classId ? true : undefined}
                  aria-describedby={describedBy("classId", errors.classId?.message)}
                  {...register("classId", { valueAsNumber: true })}
                >
                  <option value="">Choose a class</option>
                  {classes.data?.items.map((klass) => (
                    <option key={klass.id} value={klass.id}>
                      {classLabel(klass)} ({klass.academicYear})
                    </option>
                  ))}
                </select>
              </Field>
              <Field
                id="guardianContact"
                label="Guardian contact (optional)"
                hint="Phone number or email."
                error={errors.guardianContact?.message}
              >
                <input
                  id="guardianContact"
                  className="input"
                  autoComplete="off"
                  aria-invalid={errors.guardianContact ? true : undefined}
                  aria-describedby={describedBy(
                    "guardianContact",
                    errors.guardianContact?.message,
                    "Phone number or email.",
                  )}
                  {...register("guardianContact")}
                />
              </Field>
            </div>
          </fieldset>

          <fieldset>
            <legend className="section-title">First monthly records (optional)</legend>
            <p className="mb-3 mt-1 max-w-prose text-sm text-muted">
              Fill in each month you have figures for and delete the rows you don't. A student with no records is added
              but not scored until you save a month from their page.
            </p>
            {fields.length > 0 && (
              <div className="table-wrap">
                <table className="data-table min-w-[56rem]">
                  <caption className="sr-only">Monthly records for the new student</caption>
                  <thead>
                    <tr>
                      <th scope="col">Month</th>
                      {COLUMNS.map((column) => (
                        <th key={column.key} scope="col">
                          {column.short}
                        </th>
                      ))}
                      <th scope="col">
                        <span className="sr-only">Remove</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {fields.map((field, index) => (
                      <tr key={field.id}>
                        <td>
                          <input
                            type="month"
                            placeholder="YYYY-MM"
                            className="input !min-w-[9rem]"
                            aria-label={`Row ${index + 1} month`}
                            aria-invalid={errors.records?.[index]?.month ? true : undefined}
                            {...register(`records.${index}.month`)}
                          />
                        </td>
                        {COLUMNS.map((column) => (
                          <td key={column.key}>
                            <input
                              type="number"
                              inputMode="decimal"
                              step={column.step}
                              className="input num !min-w-[5.5rem]"
                              aria-label={`Row ${index + 1} ${column.label}`}
                              aria-invalid={errors.records?.[index]?.[column.key] ? true : undefined}
                              {...register(`records.${index}.${column.key}`, { valueAsNumber: true })}
                            />
                          </td>
                        ))}
                        <td>
                          <button
                            type="button"
                            className="btn !min-h-8 !px-3"
                            onClick={() => remove(index)}
                            aria-label={`Remove row ${index + 1}`}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {recordProblems.length > 0 && (
              <ul role="alert" className="field-error mt-3 list-disc space-y-0.5 pl-5">
                {recordProblems.map((problem) => (
                  <li key={problem}>{problem}</li>
                ))}
              </ul>
            )}
            {errors.records?.message && (
              <p role="alert" className="field-error">
                {errors.records.message}
              </p>
            )}
            {errors.records?.root?.message && (
              <p role="alert" className="field-error">
                {errors.records.root.message}
              </p>
            )}
            <button type="button" className="btn mt-3" onClick={addMonth} disabled={fields.length >= 12}>
              Add another month
            </button>
          </fieldset>

          <div className="flex flex-wrap gap-3 border-t border-line pt-5">
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Save student"}
            </button>
            <Link to="/students" className="btn">
              Cancel
            </Link>
          </div>
        </form>
      )}
    </>
  );
}
