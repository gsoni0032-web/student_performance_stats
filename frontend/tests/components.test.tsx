import { render, screen } from "@testing-library/react";

import type { Factor } from "@/api/types";
import { FactorBars } from "@/components/FactorBars";
import { RiskBadge } from "@/components/RiskBadge";
import { RiskGauge } from "@/components/RiskGauge";
import { Sparkline, trendLabel } from "@/components/Sparkline";

describe("risk is never shown by colour alone", () => {
  it("writes the band and the percentage in the badge", () => {
    render(<RiskBadge level="high" prob={0.72} />);
    expect(screen.getByText("High risk")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
  });

  it("says when a student has not been scored", () => {
    render(<RiskBadge level={null} />);
    expect(screen.getByText("Not scored")).toBeInTheDocument();
  });

  it("describes the gauge to assistive technology", () => {
    render(<RiskGauge prob={0.45} level="medium" />);
    expect(screen.getByRole("img", { name: /Medium risk: 45% chance of dropping out/ })).toBeInTheDocument();
    expect(screen.getByTestId("risk-prob")).toHaveTextContent("45%");
  });
});

describe("FactorBars", () => {
  const factors: Factor[] = [
    { key: "attendance", label: "Low attendance", display: "61%", impact: 18, driver: "raises" },
    { key: "assignments", label: "Assignments on time", display: "92%", impact: 6, driver: "lowers" },
  ];

  it("labels the direction of each factor in words", () => {
    render(<FactorBars factors={factors} />);
    expect(screen.getByText(/▲ raises/)).toBeInTheDocument();
    expect(screen.getByText(/▼ lowers/)).toBeInTheDocument();
    expect(screen.getByText("Low attendance")).toBeInTheDocument();
  });

  it("explains why there is nothing to show", () => {
    render(<FactorBars factors={[]} />);
    expect(screen.getByText(/until the student has been scored/)).toBeInTheDocument();
  });
});

describe("Sparkline", () => {
  it("summarises the trend in its label", () => {
    expect(trendLabel("Score", [50, 55, 61])).toBe("Score up, from 50 to 61");
    expect(trendLabel("Score", [70, 70.2])).toBe("Score steady, from 70 to 70");
    expect(trendLabel("Score", [70])).toBe("Score: not enough data");
  });

  it("renders nothing drawn for a single point", () => {
    render(<Sparkline values={[5]} label="x" />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
