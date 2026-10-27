import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, download } from "@/api/client";
import type {
  AuditEntry,
  ClassInput,
  ClassOut,
  CohortPoint,
  Driver,
  FollowUp,
  FollowUpStatus,
  GradeRisk,
  ImportResult,
  ModelInfo,
  MonthlyRecordInput,
  Page,
  Prediction,
  StudentCreateInput,
  StudentDetail,
  StudentFilters,
  StudentSummary,
  StudentUpdateInput,
  Summary,
  Thresholds,
  User,
  UserInput,
  WatchlistItem,
  WhatIfInput,
} from "@/api/types";

export interface StudentListParams extends StudentFilters {
  page: number;
  pageSize: number;
  sort: "risk" | "name" | "code" | "grade" | "status";
  order: "asc" | "desc";
}

function filterQuery(f: StudentFilters) {
  return { q: f.q, class_id: f.classId, grade: f.grade, department: f.department, risk: f.risk, status: f.status };
}

// ---------------------------------------------------------------- dashboard

export const useSummary = () => useQuery({ queryKey: ["summary"], queryFn: () => api<Summary>("/dashboard/summary") });
export const useRiskByGrade = () =>
  useQuery({ queryKey: ["risk-by-grade"], queryFn: () => api<GradeRisk[]>("/dashboard/risk-by-grade") });
export const useDrivers = () => useQuery({ queryKey: ["drivers"], queryFn: () => api<Driver[]>("/dashboard/drivers") });
export const useWatchlist = () =>
  useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api<WatchlistItem[]>("/dashboard/watchlist", { query: { limit: 8 } }),
  });
export const useCohort = () =>
  useQuery({
    queryKey: ["cohort"],
    queryFn: () => api<CohortPoint[]>("/dashboard/cohort", { query: { limit: 2000 } }),
  });

// ---------------------------------------------------------------- students

export const useStudents = (params: StudentListParams) =>
  useQuery({
    queryKey: ["students", params],
    queryFn: () =>
      api<Page<StudentSummary>>("/students", {
        query: {
          ...filterQuery(params),
          page: params.page,
          page_size: params.pageSize,
          sort: params.sort,
          order: params.order,
        },
      }),
    placeholderData: keepPreviousData,
  });

export const useStudent = (id: number) =>
  useQuery({
    queryKey: ["student", id],
    queryFn: () => api<StudentDetail>(`/students/${id}`),
    enabled: Number.isFinite(id),
  });

export function exportStudents(filters: StudentFilters): Promise<void> {
  return download("/data/export", "pathway-students.csv", filterQuery(filters));
}

function useRefreshAll() {
  const client = useQueryClient();
  return () => client.invalidateQueries();
}

export function useCreateStudent() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: StudentCreateInput) => api<StudentDetail>("/students", { method: "POST", body: input }),
    onSuccess: refresh,
  });
}

export function useUpdateStudent(id: number) {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: StudentUpdateInput) => api<StudentDetail>(`/students/${id}`, { method: "PUT", body: input }),
    onSuccess: refresh,
  });
}

export function useDeleteStudent() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/students/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
}

export function useSaveRecord(id: number) {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: MonthlyRecordInput) =>
      api<StudentDetail>(`/students/${id}/records`, { method: "POST", body: input }),
    onSuccess: refresh,
  });
}

export function useRecompute(id: number) {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: () => api<StudentDetail>(`/students/${id}/predict`, { method: "POST" }),
    onSuccess: refresh,
  });
}

export function useSaveFollowUp(id: number) {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: { status: FollowUpStatus; notes: string }) =>
      api<FollowUp>(`/students/${id}/intervention`, { method: "PUT", body: input }),
    onSuccess: refresh,
  });
}

// ---------------------------------------------------------------- what-if

export const useWhatIf = (input: WhatIfInput) =>
  useQuery({
    queryKey: ["what-if", input],
    queryFn: () => api<Prediction>("/predict", { method: "POST", body: input }),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

// ---------------------------------------------------------------- classes and users

export const useClasses = () =>
  useQuery({ queryKey: ["classes"], queryFn: () => api<Page<ClassOut>>("/classes", { query: { page_size: 100 } }) });

export function useSaveClass(id?: number) {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: ClassInput) =>
      api<ClassOut>(id ? `/classes/${id}` : "/classes", { method: id ? "PUT" : "POST", body: input }),
    onSuccess: refresh,
  });
}

export function useDeleteClass() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/classes/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
}

export const useUsers = (page: number, q: string) =>
  useQuery({
    queryKey: ["users", page, q],
    queryFn: () => api<Page<User>>("/users", { query: { page, page_size: 25, q } }),
    placeholderData: keepPreviousData,
  });

export function useSaveUser(id?: number) {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: UserInput) =>
      api<User>(id ? `/users/${id}` : "/users", { method: id ? "PUT" : "POST", body: input }),
    onSuccess: refresh,
  });
}

export function useDeleteUser() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/users/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
}

export const useAudit = (page: number) =>
  useQuery({
    queryKey: ["audit", page],
    queryFn: () => api<Page<AuditEntry>>("/audit", { query: { page, page_size: 25 } }),
    placeholderData: keepPreviousData,
  });

// ---------------------------------------------------------------- data and model

export function useImport() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: ({ file, dryRun, skipInvalid }: { file: File; dryRun: boolean; skipInvalid: boolean }) => {
      const form = new FormData();
      form.append("file", file);
      return api<ImportResult>("/data/import", {
        method: "POST",
        form,
        query: { dry_run: dryRun, skip_invalid: skipInvalid },
      });
    },
    onSuccess: (result) => (result.imported ? refresh() : undefined),
  });
}

export const useModelInfo = () =>
  useQuery({
    queryKey: ["model-info"],
    queryFn: () => api<ModelInfo>("/model/info"),
    refetchInterval: (query) => (query.state.data?.training.status === "running" ? 2000 : false),
  });

export function useRetrain() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<unknown>("/model/retrain", { method: "POST" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["model-info"] }),
  });
}

export function useActivateModel() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (version: number) => api<ModelInfo>(`/model/activate/${version}`, { method: "POST" }),
    onSuccess: refresh,
  });
}

export function useSaveThresholds() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (input: Thresholds) => api<Thresholds>("/settings/thresholds", { method: "PUT", body: input }),
    onSuccess: refresh,
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (input: { currentPassword: string; newPassword: string }) =>
      api<void>("/auth/change-password", { method: "POST", body: input }),
  });
}
