import { z } from "zod";

function bounded(label: string, min: number, max: number, whole = false) {
  const required = `${label}: enter a number`;
  const base = z
    .number({ required_error: required, invalid_type_error: required })
    .min(min, `${label} must be at least ${min}`)
    .max(max, `${label} must be at most ${max}`);
  return whole ? base.int(`${label} must be a whole number`) : base;
}

export const passwordSchema = z
  .string()
  .min(10, "Use at least 10 characters")
  .max(72, "Use at most 72 characters")
  .regex(/[a-z]/, "Add a lowercase letter")
  .regex(/[A-Z]/, "Add an uppercase letter")
  .regex(/\d/, "Add a digit");

export const loginSchema = z.object({
  email: z.string().trim().min(1, "Enter your email address").email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
export type LoginForm = z.infer<typeof loginSchema>;

export const monthlyRecordSchema = z.object({
  month: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/, "Choose a month"),
  avgScore: bounded("Average score", 0, 100),
  attendancePct: bounded("Attendance", 0, 100),
  assignmentsPct: bounded("Assignments", 0, 100),
  lateArrivals: bounded("Late arrivals", 0, 31, true),
  failedSubjects: bounded("Backlogs", 0, 12, true),
  guardianEngagement: bounded("Guardian engagement", 1, 5, true),
});
export type MonthlyRecordForm = z.infer<typeof monthlyRecordSchema>;

export const addStudentSchema = z.object({
  studentCode: z
    .string()
    .trim()
    .min(2, "Enter the student ID (at least 2 characters)")
    .max(30, "Student ID can be at most 30 characters")
    .regex(/^[A-Za-z0-9][A-Za-z0-9._-]*$/, "Use letters, digits, dots, dashes or underscores, with no spaces"),
  name: z.string().trim().min(1, "Enter the student's name").max(120, "Name can be at most 120 characters"),
  classId: z
    .number({ required_error: "Choose a class", invalid_type_error: "Choose a class" })
    .int()
    .positive("Choose a class"),
  guardianContact: z.string().trim().max(120, "Guardian contact can be at most 120 characters"),
  records: z
    .array(monthlyRecordSchema)
    .max(12, "Add at most 12 months")
    .superRefine((rows, ctx) => {
      const seen = new Set<string>();
      rows.forEach((row, index) => {
        if (seen.has(row.month)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Each month can appear only once",
            path: [index, "month"],
          });
        }
        seen.add(row.month);
      });
    }),
});
export type AddStudentForm = z.infer<typeof addStudentSchema>;

export const editStudentSchema = z.object({
  name: z.string().trim().min(1, "Enter the student's name").max(120),
  classId: z.number({ invalid_type_error: "Choose a class", required_error: "Choose a class" }).int().positive(),
  guardianContact: z.string().trim().max(120),
});
export type EditStudentForm = z.infer<typeof editStudentSchema>;

export const classSchema = z.object({
  department: z.string().trim().min(1, "Enter the programme or department").max(120),
  grade: z.number({ invalid_type_error: "Choose a year", required_error: "Choose a year" }).int().min(1).max(6),
  section: z.string().trim().min(1, "Enter the section").max(10, "Section can be at most 10 characters"),
  academicYear: z
    .string()
    .trim()
    .regex(/^\d{4}-\d{2}$/, "Use the form 2026-27"),
});
export type ClassForm = z.infer<typeof classSchema>;

const roleSchema = z.enum(["admin", "teacher", "viewer"]);

export const userCreateSchema = z.object({
  name: z.string().trim().min(1, "Enter a name").max(120),
  email: z.string().trim().min(1, "Enter an email address").email("Enter a valid email address"),
  password: passwordSchema,
  role: roleSchema,
  classIds: z.array(z.number()),
});
export type UserCreateForm = z.infer<typeof userCreateSchema>;

export const userEditSchema = z.object({
  name: z.string().trim().min(1, "Enter a name").max(120),
  role: roleSchema,
  isActive: z.boolean(),
  password: z.union([z.literal(""), passwordSchema]),
  classIds: z.array(z.number()),
});
export type UserEditForm = z.infer<typeof userEditSchema>;

export const thresholdsSchema = z
  .object({
    medium: bounded("Medium threshold", 1, 98, true),
    high: bounded("High threshold", 2, 99, true),
  })
  .refine((v) => v.medium < v.high, {
    message: "The medium threshold must be lower than the high threshold",
    path: ["medium"],
  });
export type ThresholdsForm = z.infer<typeof thresholdsSchema>;

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Enter your current password"),
    newPassword: passwordSchema,
    confirm: z.string(),
  })
  .refine((v) => v.newPassword === v.confirm, { message: "The two passwords don't match", path: ["confirm"] });
export type ChangePasswordForm = z.infer<typeof changePasswordSchema>;
