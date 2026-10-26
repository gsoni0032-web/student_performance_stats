import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useModelInfo, useWhatIf } from "@/api/hooks";
import type { WhatIfInput } from "@/api/types";
import { FactorBars } from "@/components/FactorBars";
import { PageHeader } from "@/components/PageHeader";
import { RiskGauge } from "@/components/RiskGauge";
import { Skeleton } from "@/components/Skeleton";
import { ErrorState, isNoModel } from "@/components/States";
import { useDebounced } from "@/hooks/useDebounced";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { number } from "@/lib/format";

interface Control {
  key: keyof WhatIfInput;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  help: string;
}

const CONTROLS: Control[] = [
  { key: "attendance", label: "Attendance", min: 0, max: 100, step: 1, unit: "%", help: "Share of classes attended." },
  {
    key: "score",
    label: "Average score",
    min: 0,
    max: 100,
    step: 1,
    unit: "",
    help: "Mean mark across subjects this month.",
  },
  {
    key: "assignments",
    label: "Assignments submitted",
    min: 0,
    max: 100,
    step: 1,
    unit: "%",
    help: "Share of assignments handed in.",
  },
  {
    key: "failures",
    label: "Backlogs",
    min: 0,
    max: 12,
    step: 1,
    unit: "",
    help: "Subjects currently failed or carried over.",
  },
  {
    key: "late",
    label: "Late arrivals a month",
    min: 0,
    max: 31,
    step: 1,
    unit: "",
    help: "Times the student arrived after the start.",
  },
  {
    key: "parent",
    label: "Guardian engagement",
    min: 1,
    max: 5,
    step: 1,
    unit: " of 5",
    help: "1 is no contact, 5 is regular and responsive.",
  },
  {
    key: "trend",
    label: "Score trend a month",
    min: -20,
    max: 20,
    step: 0.5,
    unit: " pts",
    help: "Average change in score from one month to the next.",
  },
  {
    key: "grade",
    label: "Year of study",
    min: 1,
    max: 6,
    step: 1,
    unit: "",
    help: "Which year of the programme the student is in.",
  },
];

const DEFAULTS: WhatIfInput = {
  attendance: 78,
  score: 62,
  assignments: 70,
  failures: 1,
  late: 3,
  parent: 3,
  trend: 0,
  grade: 2,
};

function startingValues(params: URLSearchParams): WhatIfInput {
  const values = { ...DEFAULTS };
  for (const control of CONTROLS) {
    const raw = params.get(control.key);
    const parsed = raw === null ? Number.NaN : Number(raw);
    if (Number.isFinite(parsed)) values[control.key] = Math.min(control.max, Math.max(control.min, parsed));
  }
  return values;
}

export function WhatIfPage() {
  useDocumentTitle("What-if");
  const [params] = useSearchParams();
  const [initial] = useState(() => startingValues(params));
  const [values, setValues] = useState<WhatIfInput>(initial);
  const settled = useDebounced(values, 250);
  const prediction = useWhatIf(settled);
  const info = useModelInfo();

  const noModel = prediction.isError && isNoModel(prediction.error);
  const waiting = prediction.isFetching;

  return (
    <>
      <PageHeader title="What-if" eyebrow="Explore">
        Move the sliders to see how the predicted risk responds. Nothing here is saved, and no student is changed.
      </PageHeader>

      <div className="grid gap-8 lg:grid-cols-[1fr_minmax(0,22rem)]">
        <form aria-label="Student figures" className="space-y-5" onSubmit={(e) => e.preventDefault()}>
          {CONTROLS.map((control) => {
            const id = `wi-${control.key}`;
            const value = values[control.key];
            return (
              <div key={control.key}>
                <div className="flex items-baseline justify-between gap-3">
                  <label htmlFor={id} className="field-label !mb-0">
                    {control.label}
                  </label>
                  <output htmlFor={id} className="num font-semibold">
                    {number(value, control.step < 1 ? 1 : 0)}
                    {control.unit}
                  </output>
                </div>
                <input
                  id={id}
                  type="range"
                  className="mt-1 h-2 w-full cursor-pointer accent-brand"
                  min={control.min}
                  max={control.max}
                  step={control.step}
                  value={value}
                  aria-describedby={`${id}-help`}
                  onChange={(e) => setValues((current) => ({ ...current, [control.key]: Number(e.target.value) }))}
                />
                <p id={`${id}-help`} className="field-hint">
                  {control.help}
                </p>
              </div>
            );
          })}
          <button type="button" className="btn" onClick={() => setValues(initial)}>
            Reset to starting values
          </button>
        </form>

        <aside aria-label="Predicted risk" className="lg:sticky lg:top-6 lg:self-start">
          <div className="panel p-5" aria-busy={waiting}>
            <h2 className="section-title mb-3">Predicted risk</h2>
            {prediction.isError ? (
              noModel ? (
                <p className="text-muted">
                  There is no trained model yet. An administrator can train one on the Model page.
                </p>
              ) : (
                <ErrorState error={prediction.error} onRetry={() => void prediction.refetch()} />
              )
            ) : !prediction.data ? (
              <div role="status" aria-label="Calculating" className="space-y-3">
                <Skeleton className="h-28 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ) : (
              <div className={waiting ? "opacity-70" : undefined}>
                <RiskGauge
                  prob={prediction.data.prob}
                  level={prediction.data.riskLevel}
                  thresholds={info.data?.thresholds}
                />
                {prediction.data.nextTermScore != null && (
                  <p className="mt-4 border-t border-line pt-3 text-sm">
                    Expected score next term: <strong className="num">{number(prediction.data.nextTermScore)}</strong>
                  </p>
                )}
                <h3 className="eyebrow mb-2 mt-5">Main factors</h3>
                <FactorBars factors={prediction.data.factors} />
                {prediction.data.suggestedActions.length > 0 && (
                  <>
                    <h3 className="eyebrow mb-2 mt-5">What would help</h3>
                    <ul className="list-disc space-y-1 pl-5 text-sm">
                      {prediction.data.suggestedActions.map((action) => (
                        <li key={action}>{action}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
