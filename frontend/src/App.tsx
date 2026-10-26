import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { RequireAuth, RequireRole } from "@/components/Guards";
import { AdminAuditPage } from "@/pages/AdminAudit";
import { AdminClassesPage } from "@/pages/AdminClasses";
import { AdminImportPage } from "@/pages/AdminImport";
import { AdminModelPage } from "@/pages/AdminModel";
import { AdminUsersPage } from "@/pages/AdminUsers";
import { LoginPage } from "@/pages/Login";
import { NotFoundPage } from "@/pages/NotFound";
import { OverviewPage } from "@/pages/Overview";
import { SettingsPage } from "@/pages/Settings";
import { StudentDetailPage } from "@/pages/StudentDetail";
import { StudentNewPage } from "@/pages/StudentNew";
import { StudentsPage } from "@/pages/Students";
import { WhatIfPage } from "@/pages/WhatIf";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<OverviewPage />} />
          <Route path="students" element={<StudentsPage />} />
          <Route element={<RequireRole roles={["admin", "teacher"]} />}>
            <Route path="students/new" element={<StudentNewPage />} />
          </Route>
          <Route path="students/:id" element={<StudentDetailPage />} />
          <Route path="what-if" element={<WhatIfPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route element={<RequireRole roles={["admin"]} />}>
            <Route path="admin" element={<Navigate to="/admin/users" replace />} />
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/classes" element={<AdminClassesPage />} />
            <Route path="admin/import" element={<AdminImportPage />} />
            <Route path="admin/model" element={<AdminModelPage />} />
            <Route path="admin/audit" element={<AdminAuditPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
