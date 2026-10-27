import { Link, Outlet, useLocation } from "react-router-dom";

import { Wordmark } from "@/components/Logo";
import { useAuth } from "@/hooks/useAuth";

interface Item {
  to: string;
  label: string;
  /** Extra rule for when the item counts as the current section. */
  section?: string;
  end?: boolean;
}

const ROLE_LABELS = { admin: "Administrator", teacher: "Faculty mentor", viewer: "Viewer" } as const;

export function AppShell() {
  const { user, can, signOut } = useAuth();
  const { pathname } = useLocation();

  const items: Item[] = [
    { to: "/", label: "Overview", end: true },
    { to: "/students", label: "Students", section: "/students" },
    { to: "/what-if", label: "What-if", section: "/what-if" },
    { to: "/settings", label: "Settings", section: "/settings" },
  ];
  if (can("admin")) items.push({ to: "/admin/users", label: "Admin", section: "/admin" });

  function isCurrent(item: Item): boolean {
    return item.end ? pathname === item.to : pathname.startsWith(item.section ?? item.to);
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <a
        href="#main"
        className="sr-only rounded-sm bg-brand px-4 py-2 font-semibold text-brand-ink focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50"
      >
        Skip to main content
      </a>

      <aside className="hidden border-r border-line lg:block">
        <div className="sticky top-0 flex h-screen flex-col px-5 py-6">
          <Link to="/" aria-label="Pathway, go to overview">
            <Wordmark />
          </Link>
          <p className="eyebrow mt-1 pl-0.5">Student success</p>
          <nav aria-label="Main" className="mt-8 flex-1">
            <ul className="space-y-0.5">
              {items.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    aria-current={isCurrent(item) ? "page" : undefined}
                    className={`block border-l-2 py-1.5 pl-3 text-[0.95rem] ${
                      isCurrent(item)
                        ? "border-brand font-semibold text-ink"
                        : "border-transparent text-muted hover:text-ink"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <div className="rule-top pt-4 text-sm">
            <p className="font-semibold">{user?.name}</p>
            <p className="text-muted">{user ? ROLE_LABELS[user.role] : ""}</p>
            <button
              type="button"
              className="mt-2 font-semibold underline underline-offset-2"
              onClick={() => void signOut()}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <div className="min-w-0">
        <div className="flex items-center justify-between border-b border-line px-4 py-3 lg:hidden">
          <Wordmark />
          <button
            type="button"
            className="text-sm font-semibold underline underline-offset-2"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
        </div>
        <main
          id="main"
          tabIndex={-1}
          className="mx-auto w-full max-w-6xl px-4 pb-28 pt-6 outline-none sm:px-6 lg:px-10 lg:pb-12 lg:pt-8"
        >
          <Outlet />
        </main>
      </div>

      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 border-t border-ink/60 bg-surface lg:hidden">
        <ul className="grid" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
          {items.map((item) => (
            <li key={item.to}>
              <Link
                to={item.to}
                aria-current={isCurrent(item) ? "page" : undefined}
                className={`flex min-h-[3.25rem] items-center justify-center border-t-2 px-1 text-center text-xs font-semibold ${
                  isCurrent(item) ? "border-brand text-ink" : "border-transparent text-muted"
                }`}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
