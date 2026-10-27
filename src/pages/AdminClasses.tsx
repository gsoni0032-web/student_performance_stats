import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { messageOf } from "@/api/client";
import { useClasses, useDeleteClass, useSaveClass } from "@/api/hooks";
import type { ClassOut } from "@/api/types";
import { AdminTabs } from "@/components/AdminTabs";
import { ConfirmModal } from "@/components/ConfirmModal";
import { Field, describedBy } from "@/components/Field";
import { Modal } from "@/components/Modal";
import { PageHeader } from "@/components/PageHeader";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";
import { classSchema, type ClassForm } from "@/lib/schemas";

function currentAcademicYear(now = new Date()): string {
  const start = now.getMonth() >= 5 ? now.getFullYear() : now.getFullYear() - 1;
  return `${start}-${String((start + 1) % 100).padStart(2, "0")}`;
}

function ClassModal({ klass, onClose }: { klass?: ClassOut; onClose: () => void }) {
  const toast = useToast();
  const save = useSaveClass(klass?.id);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ClassForm>({
    resolver: zodResolver(classSchema),
    defaultValues: klass
      ? { department: klass.department, grade: klass.grade, section: klass.section, academicYear: klass.academicYear }
      : { department: "", grade: 1, section: "A", academicYear: currentAcademicYear() },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await save.mutateAsync(values);
      toast.success(klass ? "Class updated." : "Class created.");
      onClose();
    } catch (error) {
      toast.error(messageOf(error));
    }
  });

  return (
    <Modal title={klass ? "Edit class" : "Add a class"} onClose={onClose}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Field
          id="c-department"
          label="Programme or department"
          hint="For example Computer Science or B.Com."
          error={errors.department?.message}
        >
          <input
            id="c-department"
            className="input"
            aria-invalid={errors.department ? true : undefined}
            aria-describedby={describedBy("c-department", errors.department?.message, "hint")}
            {...register("department")}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field id="c-grade" label="Year of study" error={errors.grade?.message}>
            <select id="c-grade" className="input" {...register("grade", { valueAsNumber: true })}>
              {[1, 2, 3, 4, 5, 6].map((year) => (
                <option key={year} value={year}>
                  Year {year}
                </option>
              ))}
            </select>
          </Field>
          <Field id="c-section" label="Section" error={errors.section?.message}>
            <input
              id="c-section"
              className="input"
              aria-invalid={errors.section ? true : undefined}
              aria-describedby={describedBy("c-section", errors.section?.message)}
              {...register("section")}
            />
          </Field>
          <Field id="c-year" label="Academic year" error={errors.academicYear?.message}>
            <input
              id="c-year"
              className="input num"
              placeholder="2026-27"
              aria-invalid={errors.academicYear ? true : undefined}
              aria-describedby={describedBy("c-year", errors.academicYear?.message)}
              {...register("academicYear")}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save class"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function AdminClassesPage() {
  useDocumentTitle("Classes");
  const toast = useToast();
  const classes = useClasses();
  const remove = useDeleteClass();
  const [dialog, setDialog] = useState<{ kind: "edit"; klass?: ClassOut } | { kind: "delete"; klass: ClassOut } | null>(
    null,
  );

  async function onDelete(klass: ClassOut) {
    try {
      await remove.mutateAsync(klass.id);
      toast.success(`${klass.label} was deleted.`);
    } catch (error) {
      toast.error(messageOf(error));
    }
    setDialog(null);
  }

  return (
    <>
      <PageHeader
        title="Administration"
        eyebrow="Classes"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setDialog({ kind: "edit" })}>
            Add class
          </button>
        }
      >
        A class is a programme, a year of study and a section. Students belong to exactly one.
      </PageHeader>
      <AdminTabs />

      {classes.isError ? (
        <ErrorState error={classes.error} onRetry={() => void classes.refetch()} />
      ) : !classes.data ? (
        <div className="space-y-2" role="status" aria-label="Loading classes">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : classes.data.items.length === 0 ? (
        <EmptyState
          title="No classes yet"
          action={
            <button type="button" className="btn btn-primary" onClick={() => setDialog({ kind: "edit" })}>
              Add the first class
            </button>
          }
        >
          Create a class before adding students or importing a CSV.
        </EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="data-table min-w-[40rem]">
            <caption className="sr-only">Classes</caption>
            <thead>
              <tr>
                <th scope="col">Programme</th>
                <th scope="col">Year</th>
                <th scope="col">Section</th>
                <th scope="col">Academic year</th>
                <th scope="col">Students</th>
                <th scope="col">Mentors</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {classes.data.items.map((klass) => (
                <tr key={klass.id}>
                  <td className="font-semibold">{klass.department}</td>
                  <td className="num">{klass.grade}</td>
                  <td>{klass.section}</td>
                  <td className="num">{klass.academicYear}</td>
                  <td className="num">{klass.studentCount}</td>
                  <td className="num">{klass.teacherIds.length}</td>
                  <td className="whitespace-nowrap text-right">
                    <button
                      type="button"
                      className="btn !min-h-8 !px-3"
                      onClick={() => setDialog({ kind: "edit", klass })}
                      aria-label={`Edit ${klass.label}`}
                    >
                      Edit
                    </button>{" "}
                    <button
                      type="button"
                      className="btn btn-danger !min-h-8 !px-3"
                      onClick={() => setDialog({ kind: "delete", klass })}
                      aria-label={`Delete ${klass.label}`}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialog?.kind === "edit" && <ClassModal klass={dialog.klass} onClose={() => setDialog(null)} />}
      {dialog?.kind === "delete" && (
        <ConfirmModal
          title="Delete this class?"
          message={
            dialog.klass.studentCount > 0
              ? `${dialog.klass.label} still has ${dialog.klass.studentCount} students. Move or delete them first; the server will refuse otherwise.`
              : `${dialog.klass.label} will be removed.`
          }
          confirmLabel="Delete class"
          busy={remove.isPending}
          onConfirm={() => void onDelete(dialog.klass)}
          onCancel={() => setDialog(null)}
        />
      )}
    </>
  );
}
