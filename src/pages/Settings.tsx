import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { ApiError, messageOf } from "@/api/client";
import { useChangePassword } from "@/api/hooks";
import { Field, describedBy } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useTheme } from "@/hooks/useTheme";
import { useToast } from "@/hooks/useToast";
import { changePasswordSchema, type ChangePasswordForm } from "@/lib/schemas";
import type { ThemeChoice } from "@/lib/theme";

const THEMES: { value: ThemeChoice; label: string; hint: string }[] = [
  { value: "system", label: "Match my device", hint: "Follows your operating system's light or dark setting." },
  { value: "light", label: "Light", hint: "Warm paper background with dark text." },
  { value: "dark", label: "Dark", hint: "Dim background that is easier on the eyes at night." },
];

export function SettingsPage() {
  useDocumentTitle("Settings");
  const { user } = useAuth();
  const toast = useToast();
  const [theme, setTheme] = useTheme();
  const change = useChangePassword();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordForm>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirm: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await change.mutateAsync({ currentPassword: values.currentPassword, newPassword: values.newPassword });
      toast.success("Password changed. Other devices will need to sign in again.");
      reset();
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) setError("currentPassword", { message: error.message });
      toast.error(messageOf(error));
    }
  });

  return (
    <>
      <PageHeader title="Settings" eyebrow="Your account">
        Signed in as {user?.name} ({user?.email}).
      </PageHeader>

      <div className="grid max-w-4xl gap-10 lg:grid-cols-2">
        <fieldset>
          <legend className="section-title mb-3">Appearance</legend>
          <div className="space-y-2">
            {THEMES.map((option) => (
              <label
                key={option.value}
                className="panel flex cursor-pointer items-start gap-3 p-3 has-[:checked]:border-brand has-[:checked]:border-2"
              >
                <input
                  type="radio"
                  name="theme"
                  value={option.value}
                  checked={theme === option.value}
                  onChange={() => setTheme(option.value)}
                  className="mt-1 h-4 w-4 accent-brand"
                />
                <span>
                  <span className="block font-semibold">{option.label}</span>
                  <span className="block text-sm text-muted">{option.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <section aria-labelledby="password-title">
          <h2 id="password-title" className="section-title mb-3">
            Change password
          </h2>
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            <Field id="currentPassword" label="Current password" error={errors.currentPassword?.message}>
              <input
                id="currentPassword"
                type="password"
                autoComplete="current-password"
                className="input"
                aria-invalid={errors.currentPassword ? true : undefined}
                aria-describedby={describedBy("currentPassword", errors.currentPassword?.message)}
                {...register("currentPassword")}
              />
            </Field>
            <Field
              id="newPassword"
              label="New password"
              hint="At least 10 characters with an uppercase letter, a lowercase letter and a digit."
              error={errors.newPassword?.message}
            >
              <input
                id="newPassword"
                type="password"
                autoComplete="new-password"
                className="input"
                aria-invalid={errors.newPassword ? true : undefined}
                aria-describedby={describedBy("newPassword", errors.newPassword?.message, "hint")}
                {...register("newPassword")}
              />
            </Field>
            <Field id="confirm" label="Repeat new password" error={errors.confirm?.message}>
              <input
                id="confirm"
                type="password"
                autoComplete="new-password"
                className="input"
                aria-invalid={errors.confirm ? true : undefined}
                aria-describedby={describedBy("confirm", errors.confirm?.message)}
                {...register("confirm")}
              />
            </Field>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Change password"}
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
