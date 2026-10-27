import { Navigate, Outlet, useLocation } from "react-router-dom";

import type { Role } from "@/api/types";
import { PanelSkeleton } from "@/components/Skeleton";
import { useAuth } from "@/hooks/useAuth";

/** Everything below this route needs a signed-in user. */
export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="mx-auto max-w-md p-8">
        <PanelSkeleton lines={3} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <Outlet />;
}

/** Everything below this route is limited to the listed roles. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { can } = useAuth();
  if (!can(...roles)) {
    return (
      <div role="alert" className="panel max-w-xl p-6">
        <h1 className="section-title">You don't have access to this page</h1>
        <p className="mt-1 text-muted">Ask an administrator if you need it.</p>
      </div>
    );
  }
  return <Outlet />;
}
