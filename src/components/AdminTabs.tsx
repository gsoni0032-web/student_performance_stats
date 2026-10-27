import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/admin/users", label: "Users" },
  { to: "/admin/classes", label: "Classes" },
  { to: "/admin/import", label: "Import data" },
  { to: "/admin/model", label: "Model" },
  { to: "/admin/audit", label: "Audit log" },
];

/** Sub-navigation shared by the administration pages. */
export function AdminTabs() {
  return (
    <nav aria-label="Administration" className="-mt-2 mb-6 flex gap-1 overflow-x-auto border-b border-line">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            `whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold ${
              isActive ? "border-brand text-ink" : "border-transparent text-muted hover:text-ink"
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
