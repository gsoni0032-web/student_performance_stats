import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation } from "react-router-dom";

import { messageOf } from "@/api/client";
import { Field, describedBy } from "@/components/Field";
import { Wordmark } from "@/components/Logo";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { loginSchema, type LoginForm } from "@/lib/schemas";

export function LoginPage() {
  useDocumentTitle("Sign in");
  const { user, signIn } = useAuth();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });

  const from = (location.state as { from?: string } | null)?.from ?? "/";
  if (user) return <Navigate to={from} replace />;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await signIn(values.email, values.password);
    } catch (error) {
      setFormError(messageOf(error));
    }
  });

  return (
    <main id="main" className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="flex flex-col justify-between border-b border-line px-6 py-8 sm:px-12 lg:border-b-0 lg:border-r lg:py-12">
        <Wordmark />
        <div className="my-10 max-w-lg lg:my-0">
          <p className="eyebrow mb-3">Student success office</p>
          <p className="font-serif text-3xl font-semibold leading-tight tracking-tightest sm:text-4xl">
            Notice who is slipping while there is still time for a conversation.
          </p>
          <p className="mt-4 text-muted">
            Pathway brings attendance, marks and follow-ups for each class into one register, and estimates who may
            leave before the next term. It supports an advisor's judgement; it never replaces it.
          </p>
        </div>
        <p className="text-sm text-muted">Student records are confidential. Access is logged.</p>
      </section>

      <section className="flex items-center px-6 py-10 sm:px-12">
        <form
          onSubmit={onSubmit}
          noValidate
          className="mx-auto w-full max-w-sm space-y-5"
          aria-labelledby="signin-title"
        >
          <h1 id="signin-title" className="page-title">
            Sign in
          </h1>
          {formError && (
            <p role="alert" className="border-l-4 border-high bg-high-bg px-3 py-2 text-sm font-medium">
              {formError}
            </p>
          )}
          <Field id="email" label="Email" error={errors.email?.message}>
            <input
              id="email"
              type="email"
              autoComplete="username"
              className="input"
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={describedBy("email", errors.email?.message)}
              {...register("email")}
            />
          </Field>
          <Field id="password" label="Password" error={errors.password?.message}>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="input"
              aria-invalid={errors.password ? true : undefined}
              aria-describedby={describedBy("password", errors.password?.message)}
              {...register("password")}
            />
          </Field>
          <button type="submit" className="btn btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-sm text-muted">Forgotten your password? Ask an administrator to reset it.</p>
        </form>
      </section>
    </main>
  );
}
