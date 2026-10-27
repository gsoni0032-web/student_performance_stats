import type { ReactNode } from "react";

interface Props {
  title: string;
  eyebrow?: string;
  children?: ReactNode;
  actions?: ReactNode;
}

/** Page title block: small label, serif heading, optional description and actions on the right. */
export function PageHeader({ title, eyebrow, children, actions }: Props) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-ink/60 pb-4">
      <div className="min-w-0">
        {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {children && <div className="mt-1 max-w-prose text-muted">{children}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
