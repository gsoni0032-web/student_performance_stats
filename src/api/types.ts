export type Role = "admin" | "teacher" | "viewer";
export type RiskLevel = "low" | "medium" | "high";
export type FollowUpStatus = "not_started" | "guardian_contacted" | "support_plan_active" | "resolved";

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  isActive: boolean;
  createdAt: string;
  classIds: number[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface Features {
  attendance: number;
  score: number;
  assignments: number;
  failures: number;
  late: number;
  parent: number;
  trend: number;
}

export interface Factor {
  key: string;
  label: string;
  display: string;
  impact: number;
  driver: "raises" | "lowers";
}

export interface StudentSummary {
  id: number;
  studentCode: string;
  name: string;
  department: string;
  grade: number;
  section: string;
  classId: number;
  scoreSeries: number[];
  attSeries: number[];
  features: Features | null;
  prob: number | null;
  riskLevel: RiskLevel | null;
  followUpStatus: FollowUpStatus;
}

export interface FollowUp {
  status: FollowUpStatus;
  notes: string;
  updatedAt: string | null;
  updatedBy: string | null;
}

export interface StudentDetail extends StudentSummary {
  guardianContact: string | null;
  droppedOut: boolean | null;
  months: string[];
  nextTermScore: number | null;
  modelVersion: number | null;
  predictedAt: string | null;
  factors: Factor[];
  suggestedActions: string[];
  followUp: FollowUp;
}

export interface MonthlyRecordInput {
  month: string;
  avgScore: number;
  attendancePct: number;
  assignmentsPct: number;
  lateArrivals: number;
  failedSubjects: number;
  guardianEngagement: number;
}

export interface StudentCreateInput {
  studentCode: string;
  name: string;
  classId: number;
  guardianContact?: string | null;
  record?: MonthlyRecordInput;
}

export interface StudentUpdateInput {
  name?: string;
  classId?: number;
  guardianContact?: string | null;
  droppedOut?: boolean | null;
}

export interface ClassOut {
  id: number;
  department: string;
  grade: number;
  section: string;
  academicYear: string;
  label: string;
  studentCount: number;
  teacherIds: number[];
}

export interface ClassInput {
  department: string;
  grade: number;
  section: string;
  academicYear: string;
}

export interface Summary {
  studentsTracked: number;
  avgAttendance: number | null;
  avgScore: number | null;
  highRisk: number;
  mediumRisk: number;
  lowRisk: number;
  unscored: number;
  attendanceChange: number | null;
  scoreChange: number | null;
  highRiskChange: number;
  latestMonth: string | null;
}

export interface GradeRisk {
  grade: number;
  low: number;
  medium: number;
  high: number;
  unscored: number;
}

export interface Driver {
  key: string;
  label: string;
  students: number;
  share: number;
  avgImpact: number;
}

export interface WatchlistItem {
  id: number;
  name: string;
  studentCode: string;
  department: string;
  grade: number;
  prob: number;
  riskLevel: RiskLevel;
  topFactor: string | null;
  followUpStatus: FollowUpStatus;
}

export interface CohortPoint {
  id: number;
  name: string;
  grade: number;
  prob: number | null;
  riskLevel: RiskLevel | null;
  attendance: number | null;
  score: number | null;
}

export interface WhatIfInput {
  attendance: number;
  score: number;
  assignments: number;
  failures: number;
  late: number;
  parent: number;
  trend: number;
  grade: number;
}

export interface Prediction {
  prob: number;
  riskLevel: RiskLevel;
  nextTermScore: number | null;
  factors: Factor[];
  suggestedActions: string[];
  modelVersion: number;
}

export interface Thresholds {
  medium: number;
  high: number;
}

export interface Confusion {
  tn: number;
  fp: number;
  fn: number;
  tp: number;
}

export interface TestMetrics {
  threshold: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
  confusion_matrix: Confusion;
}

export interface ModelMetrics {
  model_type: string;
  samples: { labelled: number; train: number; validation: number; test: number; dropout_rate: number };
  candidates: Record<
    string,
    { cv_pr_auc: number; val_pr_auc: number; val_roc_auc: number; val_recall_at_flag: number }
  >;
  test_at_flag_threshold: TestMetrics;
  test_at_high_threshold: TestMetrics;
  recommended_flag_threshold: number;
  recall_note: string;
  regression: { samples: number; mae: number; rmse: number; r2: number; baseline_mae: number; baseline: string } | null;
}

export interface ModelVersionInfo {
  version: number;
  modelType: string;
  trainedAt: string;
  isActive: boolean;
  metrics: ModelMetrics;
}

export interface TrainingState {
  status: "idle" | "running" | "succeeded" | "failed";
  message: string | null;
  started_at: string | null;
  finished_at: string | null;
  version: number | null;
}

export interface ModelInfo {
  active: ModelVersionInfo | null;
  versions: ModelVersionInfo[];
  training: TrainingState;
  thresholds: Thresholds;
}

export interface RowIssue {
  row: number;
  column: string | null;
  message: string;
}

export interface ImportResult {
  dryRun: boolean;
  imported: boolean;
  rowsRead: number;
  rowsValid: number;
  students: number;
  records: number;
  issues: RowIssue[];
  preview: Record<string, string | number>[];
}

export interface AuditEntry {
  id: number;
  userId: number | null;
  userName: string | null;
  action: string;
  entity: string;
  entityId: string | null;
  detail: Record<string, unknown> | null;
  timestamp: string;
}

export interface UserInput {
  name: string;
  email?: string;
  password?: string;
  role: Role;
  isActive?: boolean;
  classIds: number[];
}

export interface StudentFilters {
  q?: string;
  classId?: number;
  grade?: number;
  department?: string;
  risk?: RiskLevel | "unscored";
  status?: FollowUpStatus;
}
