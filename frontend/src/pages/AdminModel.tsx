import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { messageOf } from "@/api/client";
import { useActivateModel, useModelInfo, useRetrain, useSaveThresholds } from "@/api/hooks";
import type { ModelInfo, ModelVersionInfo } from "@/api/types";
import { AdminTabs } from "@/components/AdminTabs";
import { ConfirmModal } from "@/components/ConfirmModal";
import { Field, describedBy } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/States";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useToast } from "@/hooks/useToast";
import { dateTime, number } from "@/lib/format";
import { thresholdsSchema, type ThresholdsForm } from "@/lib/schemas";

const MODEL_NAMES: Record<string, string> = {
  logreg: "Logistic regression",
  random_forest: "Random forest",
  xgboost: "XGBoost",
};

function modelName(type: string): string {
  return MODEL_NAMES[type] ?? type;
}

function ratio(value: number): string {
  return value.toFixed(3);
}

function ThresholdsPanel({ thresholds }: { thresholds: ModelInfo["thresholds"] }) {
  const toast = useToast();
  const save = useSaveThresholds();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ThresholdsForm>({
    resolver: zodResolver(thresholdsSchema),
    defaultValues: { medium: Math.round(thresholds.medium * 100), high: Math.round(thresholds.high * 100) },
  });

  useEffect(() => {
    reset({ medium: Math.round(thresholds.medium * 100), high: Math.round(thresholds.high * 100) });
  }, [thresholds.medium, thresholds.high, reset]);

  const onSubmit = handleSubmit(async (values) => {
    try {
      await save.mutateAsync({ medium: values.medium / 100, high: values.high / 100 });
      toast.success("Risk thresholds saved and every student relabelled.");
    } catch (error) {
      toast.error(messageOf(error));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-labelledby="thresholds-title">
      <h2 id="thresholds-title" className="section-title">
        Risk thresholds
      </h2>
      <p className="max-w-prose text-sm text-muted">
        A student is medium risk from the first value and high risk from the second. Lowering them flags more students,
        which catches more people who need help at the cost of more false alarms.
      </p>
      <div className="grid max-w-sm gap-4 sm:grid-cols-2">
        <Field id="t-medium" label="Medium from (%)" error={errors.medium?.message}>
          <input
            id="t-medium"
            type="number"
            className="input num"
            aria-invalid={errors.medium ? true : undefined}
            aria-describedby={describedBy("t-medium", errors.medium?.message)}
            {...register("medium", { valueAsNumber: true })}
          />
        </Field>
        <Field id="t-high" label="High from (%)" error={errors.high?.message}>
          <input
            id="t-high"
            type="number"
            className="input num"
            aria-invalid={errors.high ? true : undefined}
            aria-describedby={describedBy("t-high", errors.high?.message)}
            {...register("high", { valueAsNumber: true })}
          />
        </Field>
      </div>
      <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
        {isSubmitting ? "Saving…" : "Save thresholds"}
      </button>
    </form>
  );
}

function Metrics({ version }: { version: ModelVersionInfo }) {
  const m = version.metrics;
  const flag = m.test_at_flag_threshold;
  const cm = flag.confusion_matrix;
  const stats: [string, string][] = [
    ["Recall (dropouts caught)", ratio(flag.recall)],
    ["Precision", ratio(flag.precision)],
    ["F1", ratio(flag.f1)],
    ["Accuracy", ratio(flag.accuracy)],
    ["ROC-AUC", ratio(flag.roc_auc)],
    ["PR-AUC", ratio(flag.pr_auc)],
  ];
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-3 lg:grid-cols-6">
        {stats.map(([label, value]) => (
          <div key={label} className="bg-surface px-4 py-3">
            <dt className="eyebrow">{label}</dt>
            <dd className="num m-0 text-2xl font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="max-w-prose text-sm">
        <strong>Why recall comes first:</strong> {m.recall_note} Measured on {m.samples.test} held-out students at a
        flag threshold of {Math.round(m.recommended_flag_threshold * 100)}%.
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="font-semibold">Confusion matrix (test set)</h3>
          <table className="data-table mt-2 max-w-sm">
            <caption className="sr-only">Predicted against actual outcomes on the test set</caption>
            <thead>
              <tr>
                <th scope="col">
                  <span className="sr-only">Actual</span>
                </th>
                <th scope="col">Predicted: stays</th>
                <th scope="col">Predicted: drops out</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row" className="text-left font-semibold">
                  Actually stayed
                </th>
                <td className="num">{cm.tn}</td>
                <td className="num">{cm.fp}</td>
              </tr>
              <tr>
                <th scope="row" className="text-left font-semibold">
                  Actually dropped out
                </th>
                <td className="num">{cm.fn}</td>
                <td className="num font-semibold">{cm.tp}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div>
          <h3 className="font-semibold">Models compared (validation)</h3>
          <div className="table-wrap">
            <table className="data-table mt-2">
              <caption className="sr-only">Candidate models</caption>
              <thead>
                <tr>
                  <th scope="col">Model</th>
                  <th scope="col">PR-AUC</th>
                  <th scope="col">ROC-AUC</th>
                  <th scope="col">Recall</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(m.candidates).map(([type, scores]) => (
                  <tr key={type}>
                    <td className={type === m.model_type ? "font-semibold" : undefined}>
                      {modelName(type)}
                      {type === m.model_type ? " (chosen)" : ""}
                    </td>
                    <td className="num">{ratio(scores.val_pr_auc)}</td>
                    <td className="num">{ratio(scores.val_roc_auc)}</td>
                    <td className="num">{ratio(scores.val_recall_at_flag)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {m.regression && (
        <p className="text-sm">
          Next-term score model: typical error <strong className="num">{number(m.regression.mae)}</strong> points,
          against <span className="num">{number(m.regression.baseline_mae)}</span> if we simply repeated the current
          score.
        </p>
      )}
      <p className="text-sm text-muted">
        Trained on {m.samples.labelled} students with a known outcome ({Math.round(m.samples.dropout_rate * 100)}%
        dropped out).
      </p>
    </div>
  );
}

export function AdminModelPage() {
  useDocumentTitle("Model");
  const toast = useToast();
  const info = useModelInfo();
  const retrain = useRetrain();
  const activate = useActivateModel();
  const [pending, setPending] = useState<number | null>(null);
  const lastStatus = useRef<string | null>(null);

  const status = info.data?.training.status;
  useEffect(() => {
    if (lastStatus.current === "running" && status === "succeeded")
      toast.success("Training finished. The new model is active.");
    if (lastStatus.current === "running" && status === "failed")
      toast.error(info.data?.training.message ?? "Training failed.");
    lastStatus.current = status ?? null;
  }, [status, info.data?.training.message, toast]);

  async function onRetrain() {
    try {
      await retrain.mutateAsync();
      toast.success("Training started. This usually takes a minute or two.");
    } catch (error) {
      toast.error(messageOf(error));
    }
  }

  async function onActivate(version: number) {
    try {
      await activate.mutateAsync(version);
      toast.success(`Model v${version} is now active and every student has been rescored.`);
    } catch (error) {
      toast.error(messageOf(error));
    }
    setPending(null);
  }

  const running = status === "running";

  return (
    <>
      <PageHeader
        title="Administration"
        eyebrow="Model"
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void onRetrain()}
            disabled={running || retrain.isPending}
          >
            {running ? "Training…" : "Retrain model"}
          </button>
        }
      >
        The model behind every risk score. Retraining uses every student with a known outcome and keeps earlier versions
        so you can roll back.
      </PageHeader>
      <AdminTabs />

      {info.isError ? (
        <ErrorState error={info.error} onRetry={() => void info.refetch()} />
      ) : !info.data ? (
        <PanelSkeleton lines={6} />
      ) : (
        <div className="space-y-10">
          {running && (
            <p role="status" className="border-l-4 border-brand bg-sunken px-3 py-2 text-sm font-medium">
              Training is running. This page updates when it finishes.
            </p>
          )}
          {status === "failed" && info.data.training.message && (
            <p role="alert" className="border-l-4 border-high bg-high-bg px-3 py-2 text-sm font-medium">
              The last training run failed: {info.data.training.message}
            </p>
          )}

          <section aria-labelledby="active-title">
            <h2 id="active-title" className="section-title mb-3">
              Active model
            </h2>
            {info.data.active ? (
              <>
                <p className="mb-4 text-sm text-muted">
                  Version {info.data.active.version} · {modelName(info.data.active.modelType)} · trained{" "}
                  {dateTime(info.data.active.trainedAt)}
                </p>
                <Metrics version={info.data.active} />
              </>
            ) : (
              <p className="max-w-prose text-muted">
                No model has been trained. Press “Retrain model” to train the first one from the students in the
                register. At least a few hundred students with a known outcome (<code>dropped_out</code>) are needed for
                a useful model.
              </p>
            )}
          </section>

          <section aria-labelledby="versions-title">
            <h2 id="versions-title" className="section-title mb-3">
              Saved versions
            </h2>
            {info.data.versions.length === 0 ? (
              <p className="text-muted">Nothing saved yet.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table min-w-[40rem]">
                  <caption className="sr-only">Saved model versions</caption>
                  <thead>
                    <tr>
                      <th scope="col">Version</th>
                      <th scope="col">Model</th>
                      <th scope="col">Trained</th>
                      <th scope="col">Recall</th>
                      <th scope="col">PR-AUC</th>
                      <th scope="col">Status</th>
                      <th scope="col">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {info.data.versions.map((v) => (
                      <tr key={v.version}>
                        <td className="num font-semibold">v{v.version}</td>
                        <td>{modelName(v.modelType)}</td>
                        <td className="text-sm">{dateTime(v.trainedAt)}</td>
                        <td className="num">{ratio(v.metrics.test_at_flag_threshold.recall)}</td>
                        <td className="num">{ratio(v.metrics.test_at_flag_threshold.pr_auc)}</td>
                        <td>{v.isActive ? "● Active" : "Saved"}</td>
                        <td className="text-right">
                          {!v.isActive && (
                            <button
                              type="button"
                              className="btn !min-h-8 !px-3"
                              onClick={() => setPending(v.version)}
                              aria-label={`Make version ${v.version} active`}
                            >
                              Make active
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <ThresholdsPanel thresholds={info.data.thresholds} />
        </div>
      )}

      {pending !== null && (
        <ConfirmModal
          title={`Make version ${pending} active?`}
          message="Every student will be rescored with this version, and their risk levels may change."
          confirmLabel="Make active"
          busy={activate.isPending}
          onConfirm={() => void onActivate(pending)}
          onCancel={() => setPending(null)}
        />
      )}
    </>
  );
}
