import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { messageOf } from "@/api/client";
import { useClasses, useDeleteUser, useSaveUser, useUsers } from "@/api/hooks";
import type { ClassOut, Role, User } from "@/api/types";
import { AdminTabs } from "@/components/AdminTabs";
import { ConfirmModal } from "@/components/ConfirmModal";
import { Field, describedBy } from "@/components/Field";
import { Modal } from "@/components/Modal";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { useAuth } from "@/hooks/useAuth";
import { useDebounced } from "@/hooks/useDebounced";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";
import { classLabel, dateTime } from "@/lib/format";
import { userCreateSchema, userEditSchema, type UserCreateForm, type UserEditForm } from "@/lib/schemas";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "admin", label: "Administrator" },
  { value: "teacher", label: "Faculty mentor" },
  { value: "viewer", label: "Viewer (read-only)" },
];

function ClassPicker({
  classes,
  selected,
  onChange,
}: {
  classes: ClassOut[];
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  if (classes.length === 0)
    return <p className="text-sm text-muted">No classes exist yet. Create some on the Classes tab.</p>;
  return (
    <fieldset>
      <legend className="field-label">Assigned classes</legend>
      <p className="field-hint mb-2 mt-0">Faculty mentors only see students in these classes.</p>
      <div className="max-h-44 space-y-1 overflow-y-auto border border-line p-2">
        {classes.map((klass) => (
          <label key={klass.id} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 accent-brand"
              checked={selected.includes(klass.id)}
              onChange={(e) =>
                onChange(e.target.checked ? [...selected, klass.id] : selected.filter((id) => id !== klass.id))
              }
            />
            {classLabel(klass)} <span className="text-muted">({klass.academicYear})</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function CreateUserModal({ classes, onClose }: { classes: ClassOut[]; onClose: () => void }) {
  const toast = useToast();
  const save = useSaveUser();
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UserCreateForm>({
    resolver: zodResolver(userCreateSchema),
    defaultValues: { name: "", email: "", password: "", role: "teacher", classIds: [] },
  });
  const classIds = watch("classIds");

  const onSubmit = handleSubmit(async (values) => {
    try {
      await save.mutateAsync(values);
      toast.success(`${values.name} can now sign in.`);
      onClose();
    } catch (error) {
      toast.error(messageOf(error));
    }
  });

  return (
    <Modal title="Add a user" onClose={onClose}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Field id="u-name" label="Full name" error={errors.name?.message}>
          <input
            id="u-name"
            className="input"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={describedBy("u-name", errors.name?.message)}
            {...register("name")}
          />
        </Field>
        <Field id="u-email" label="Email address" error={errors.email?.message}>
          <input
            id="u-email"
            type="email"
            autoComplete="off"
            className="input"
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={describedBy("u-email", errors.email?.message)}
            {...register("email")}
          />
        </Field>
        <Field
          id="u-password"
          label="Temporary password"
          hint="At least 10 characters with an uppercase letter, a lowercase letter and a digit."
          error={errors.password?.message}
        >
          <input
            id="u-password"
            type="password"
            autoComplete="new-password"
            className="input"
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={describedBy("u-password", errors.password?.message, "hint")}
            {...register("password")}
          />
        </Field>
        <Field id="u-role" label="Role">
          <select id="u-role" className="input" {...register("role")}>
            {ROLE_OPTIONS.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </Field>
        <ClassPicker classes={classes} selected={classIds} onChange={(ids) => setValue("classIds", ids)} />
        <div className="flex justify-end gap-2">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Create user"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EditUserModal({ user, classes, onClose }: { user: User; classes: ClassOut[]; onClose: () => void }) {
  const toast = useToast();
  const save = useSaveUser(user.id);
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<UserEditForm>({
    resolver: zodResolver(userEditSchema),
    defaultValues: { name: user.name, role: user.role, isActive: user.isActive, password: "", classIds: user.classIds },
  });
  const classIds = watch("classIds");

  const onSubmit = handleSubmit(async (values) => {
    try {
      await save.mutateAsync({
        name: values.name,
        role: values.role,
        isActive: values.isActive,
        classIds: values.classIds,
        ...(values.password ? { password: values.password } : {}),
      });
      toast.success(`${values.name} updated.`);
      onClose();
    } catch (error) {
      toast.error(messageOf(error));
    }
  });

  return (
    <Modal title={`Edit ${user.name}`} onClose={onClose}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <p className="text-sm text-muted">{user.email}</p>
        <Field id="e-name" label="Full name" error={errors.name?.message}>
          <input
            id="e-name"
            className="input"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={describedBy("e-name", errors.name?.message)}
            {...register("name")}
          />
        </Field>
        <Field id="e-role" label="Role">
          <select id="e-role" className="input" {...register("role")}>
            {ROLE_OPTIONS.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </Field>
        <label className="flex items-center gap-2">
          <input type="checkbox" className="h-4 w-4 accent-brand" {...register("isActive")} />
          <span className="font-semibold">Account is active</span>
        </label>
        <Field
          id="e-password"
          label="New password (optional)"
          hint="Leave blank to keep the current password."
          error={errors.password?.message}
        >
          <input
            id="e-password"
            type="password"
            autoComplete="new-password"
            className="input"
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={describedBy("e-password", errors.password?.message, "hint")}
            {...register("password")}
          />
        </Field>
        <ClassPicker classes={classes} selected={classIds} onChange={(ids) => setValue("classIds", ids)} />
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

export function AdminUsersPage() {
  useDocumentTitle("Users");
  const { user: me } = useAuth();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounced(search.trim(), 300);
  const users = useUsers(page, q);
  const classes = useClasses();
  const remove = useDeleteUser();
  const [dialog, setDialog] = useState<
    { kind: "create" } | { kind: "edit"; user: User } | { kind: "delete"; user: User } | null
  >(null);

  const classList = classes.data?.items ?? [];

  async function onDelete(target: User) {
    try {
      await remove.mutateAsync(target.id);
      toast.success(`${target.name} was deleted.`);
    } catch (error) {
      toast.error(messageOf(error));
    }
    setDialog(null);
  }

  return (
    <>
      <PageHeader
        title="Administration"
        eyebrow="Users"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setDialog({ kind: "create" })}>
            Add user
          </button>
        }
      >
        Who can sign in, and which classes each faculty mentor can see.
      </PageHeader>
      <AdminTabs />

      <div className="mb-4 max-w-sm">
        <label htmlFor="user-search" className="field-label">
          Search users
        </label>
        <input
          id="user-search"
          type="search"
          className="input"
          placeholder="Name or email"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {users.isError ? (
        <ErrorState error={users.error} onRetry={() => void users.refetch()} />
      ) : !users.data ? (
        <div className="space-y-2" role="status" aria-label="Loading users">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : users.data.items.length === 0 ? (
        <EmptyState title="No users found">Try a different search.</EmptyState>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table min-w-[44rem]">
              <caption className="sr-only">User accounts</caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Role</th>
                  <th scope="col">Classes</th>
                  <th scope="col">Status</th>
                  <th scope="col">Created</th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.data.items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <span className="font-semibold">{row.name}</span>
                      <br />
                      <span className="text-sm text-muted">{row.email}</span>
                    </td>
                    <td>{ROLE_OPTIONS.find((r) => r.value === row.role)?.label}</td>
                    <td className="num">{row.role === "admin" ? "All" : row.classIds.length}</td>
                    <td>{row.isActive ? "Active" : "Disabled"}</td>
                    <td className="text-sm">{dateTime(row.createdAt)}</td>
                    <td className="whitespace-nowrap text-right">
                      <button
                        type="button"
                        className="btn !min-h-8 !px-3"
                        onClick={() => setDialog({ kind: "edit", user: row })}
                        aria-label={`Edit ${row.name}`}
                      >
                        Edit
                      </button>{" "}
                      {row.id !== me?.id && (
                        <button
                          type="button"
                          className="btn btn-danger !min-h-8 !px-3"
                          onClick={() => setDialog({ kind: "delete", user: row })}
                          aria-label={`Delete ${row.name}`}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={users.data.page}
            pages={users.data.pages}
            total={users.data.total}
            pageSize={users.data.pageSize}
            onPage={setPage}
          />
        </>
      )}

      {dialog?.kind === "create" && <CreateUserModal classes={classList} onClose={() => setDialog(null)} />}
      {dialog?.kind === "edit" && (
        <EditUserModal user={dialog.user} classes={classList} onClose={() => setDialog(null)} />
      )}
      {dialog?.kind === "delete" && (
        <ConfirmModal
          title="Delete this user?"
          message={`${dialog.user.name} will no longer be able to sign in. Their audit log entries are kept.`}
          confirmLabel="Delete user"
          busy={remove.isPending}
          onConfirm={() => void onDelete(dialog.user)}
          onCancel={() => setDialog(null)}
        />
      )}
    </>
  );
}
