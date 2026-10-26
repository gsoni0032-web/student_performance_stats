import { useState } from "react";

import { useAudit } from "@/api/hooks";
import { AdminTabs } from "@/components/AdminTabs";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { dateTime } from "@/lib/format";

function detailText(detail: Record<string, unknown> | null): string {
  if (!detail) return "";
  return Object.entries(detail)
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`)
    .join(", ");
}

export function AdminAuditPage() {
  useDocumentTitle("Audit log");
  const [page, setPage] = useState(1);
  const audit = useAudit(page);

  return (
    <>
      <PageHeader title="Administration" eyebrow="Audit log">
        Sign-ins, exports, imports, retraining and follow-up changes, newest first.
      </PageHeader>
      <AdminTabs />

      {audit.isError ? (
        <ErrorState error={audit.error} onRetry={() => void audit.refetch()} />
      ) : !audit.data ? (
        <div className="space-y-2" role="status" aria-label="Loading audit log">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : audit.data.items.length === 0 ? (
        <EmptyState title="Nothing recorded yet">Actions will appear here as people use the system.</EmptyState>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table min-w-[44rem]">
              <caption className="sr-only">Audit log</caption>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Who</th>
                  <th scope="col">Action</th>
                  <th scope="col">Record</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.items.map((entry) => (
                  <tr key={entry.id}>
                    <td className="whitespace-nowrap text-sm">{dateTime(entry.timestamp)}</td>
                    <td>{entry.userName ?? "System"}</td>
                    <td className="num text-sm">{entry.action}</td>
                    <td className="num text-sm">
                      {entry.entity}
                      {entry.entityId ? ` #${entry.entityId}` : ""}
                    </td>
                    <td className="text-sm text-muted">{detailText(entry.detail)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={audit.data.page}
            pages={audit.data.pages}
            total={audit.data.total}
            pageSize={audit.data.pageSize}
            onPage={setPage}
          />
        </>
      )}
    </>
  );
}
