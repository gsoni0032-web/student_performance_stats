import {
  classLabel,
  monthLabel,
  nextMonth,
  percent,
  probability,
  recentMonths,
  signed,
  toApiMonth,
} from "@/lib/format";

describe("format helpers", () => {
  it("shows a dash for missing values", () => {
    expect(percent(null)).toBe("–");
    expect(probability(undefined)).toBe("–");
    expect(signed(null)).toBe("–");
  });

  it("rounds probabilities to whole percentages", () => {
    expect(probability(0.4349)).toBe("43%");
    expect(probability(1)).toBe("100%");
  });

  it("signs changes with a real minus sign", () => {
    expect(signed(2.34)).toBe("+2.3");
    expect(signed(-1.26)).toBe("−1.3");
    expect(signed(0)).toBe("0.0");
  });

  it("names a class the way the interface does everywhere", () => {
    expect(classLabel({ department: "Computer Science", grade: 2, section: "B" })).toBe(
      "Computer Science · Year 2 · B",
    );
  });

  it("lists the months before a date, oldest first", () => {
    expect(recentMonths(3, new Date(2026, 9, 25))).toEqual(["2026-07", "2026-08", "2026-09"]);
    expect(recentMonths(2, new Date(2026, 0, 10))).toEqual(["2025-11", "2025-12"]);
  });

  it("rolls the year over when finding the next month", () => {
    expect(nextMonth("2026-12")).toBe("2027-01");
    expect(nextMonth("2026-04")).toBe("2026-05");
  });

  it("converts to the API month format", () => {
    expect(toApiMonth("2026-09")).toBe("2026-09-01");
  });

  it("returns a dash for an empty month label", () => {
    expect(monthLabel(null)).toBe("–");
  });
});
