import { addStudentSchema, classSchema, loginSchema, passwordSchema, thresholdsSchema } from "@/lib/schemas";

const record = {
  month: "2026-09",
  avgScore: 70,
  attendancePct: 88,
  assignmentsPct: 90,
  lateArrivals: 1,
  failedSubjects: 0,
  guardianEngagement: 4,
};

describe("form schemas", () => {
  it("requires a well-formed email to sign in", () => {
    expect(loginSchema.safeParse({ email: "nope", password: "x" }).success).toBe(false);
    expect(loginSchema.safeParse({ email: "a@b.co", password: "x" }).success).toBe(true);
  });

  it("enforces the password policy", () => {
    expect(passwordSchema.safeParse("short1A").success).toBe(false);
    expect(passwordSchema.safeParse("alllowercase123").success).toBe(false);
    expect(passwordSchema.safeParse("Sturdy-Pass-123").success).toBe(true);
  });

  it("accepts a complete new student", () => {
    const result = addStudentSchema.safeParse({
      studentCode: "CS24-0101",
      name: "Asha Verma",
      classId: 3,
      guardianContact: "",
      records: [record],
    });
    expect(result.success).toBe(true);
  });

  it("rejects a student id with spaces", () => {
    const result = addStudentSchema.safeParse({
      studentCode: "CS 24",
      name: "A",
      classId: 1,
      guardianContact: "",
      records: [],
    });
    expect(result.success).toBe(false);
  });

  it("rejects repeated months and out-of-range figures", () => {
    const base = { studentCode: "CS24-0101", name: "A", classId: 1, guardianContact: "" };
    expect(addStudentSchema.safeParse({ ...base, records: [record, record] }).success).toBe(false);
    expect(addStudentSchema.safeParse({ ...base, records: [{ ...record, attendancePct: 120 }] }).success).toBe(false);
    expect(addStudentSchema.safeParse({ ...base, records: [{ ...record, guardianEngagement: 0 }] }).success).toBe(
      false,
    );
  });

  it("checks the academic year format of a class", () => {
    const klass = { department: "Commerce", grade: 1, section: "A", academicYear: "2026-27" };
    expect(classSchema.safeParse(klass).success).toBe(true);
    expect(classSchema.safeParse({ ...klass, academicYear: "2026" }).success).toBe(false);
  });

  it("needs the medium threshold below the high one", () => {
    expect(thresholdsSchema.safeParse({ medium: 30, high: 60 }).success).toBe(true);
    expect(thresholdsSchema.safeParse({ medium: 60, high: 60 }).success).toBe(false);
  });
});
