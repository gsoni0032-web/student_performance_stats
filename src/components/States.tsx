import type { ReactNode } from "react";

import { ApiError, messageOf } from "@/api/client";

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="panel flex flex-col items-start gap-2 p-6">
      <h2 className="section-title">{title}</h2>
      {children && <p className="max-w-prose text-muted">{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const offline = error instanceof ApiError && error.status === 0;
  return (
    <div role="alert" className="panel border-high p-5">
      <h2 className="section-title text-high">{offline ? "Can't reach the server" : "This didn't load"}</h2>
      <p className="mt-1 text-sm">{messageOf(error)}</p>
      {onRetry && (
        <button type="button" className="btn mt-3" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** The model has not been trained yet: scores are missing but everything else works. */
export function isNoModel(error: unknown): boolean {
  return error instanceof ApiError && error.code === "no_model";
}
