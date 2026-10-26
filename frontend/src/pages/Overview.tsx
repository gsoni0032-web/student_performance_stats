import { Link, useNavigate } from "react-router-dom";

import { useCohort, useDrivers, useRiskByGrade, useSummary, useWatchlist } from "@/api/hooks";
import { AttendanceScoreScatter, RiskByYearBars } from "@/components/Charts";
import { CohortRegister, RegisterLegend } from "@/components/CohortRegister";
import { KpiBand } from "@/components/KpiBand";
import { PageHeader } from "@/components/PageHeader";
import { RiskBadge } from "@/components/RiskBadge";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { useAuth } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { STATUS_LABELS } from "@/lib/format";

export function OverviewPage() {
  useDocumentTitle("Overview");
  const navigate = useNavigate();
  const { can } = useAuth();
  const summary = useSummary();
  const cohort = useCohort();
  const byGrade = useRiskByGrade();
  const drivers = useDrivers();
  const watchlist = useWatchlist();

  const noStudents = summary.data?.studentsTracked === 0;
  const notScored =
    summary.data !== undefined &&
    summary.data.studentsTracked > 0 &&
    summary.data.unscored === summary.data.studentsTracked;

  return (
    <>
      <PageHeader title="Overview" eyebrow="Cohort at a glance">
        Who is likely to need support before next term. A prediction starts a conversation; it is never the whole
        decision.
      </PageHeader>

      {summary.isError ? (
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      ) : (
        <KpiBand summary={summary.data} />
      )}

      {noStudents && (
        <div className="mt-6">
          <EmptyState
            title="No students yet"
            action={
              can("admin", "teacher") ? (
                <Link to="/students/new" className="btn btn-primary">
                  Add a student
                </Link>
              ) : undefined
            }
          >
            Add students one at a time, or ask an administrator to import a CSV file of monthly records.
          </EmptyState>
        </div>
      )}

      {notScored && (
        <p className="mt-6 border-l-4 border-medium bg-medium-bg px-3 py-2 text-sm font-medium">
          No student has a risk score yet.{" "}
          {can("admin")
            ? "Train a model on the Model page to score the cohort."
            : "An administrator needs to train a model first."}
        </p>
      )}

      {!noStudents && (
        <div className="mt-8 grid gap-8 lg:grid-cols-[1.5fr_1fr]">
          <section aria-labelledby="register-h">
            <h2 id="register-h" className="section-title">
              Cohort register
            </h2>
            <p className="mb-3 text-sm text-muted">
              One square per student, riskiest first. Open a square to see the student.
            </p>
            {cohort.isError ? (
              <ErrorState error={cohort.error} onRetry={() => void cohort.refetch()} />
            ) : cohort.data ? (
              <>
                <CohortRegister points={cohort.data} onOpen={(id) => navigate(`/students/${id}`)} />
                <div className="mt-4">
                  <RegisterLegend />
                </div>
              </>
            ) : (
              <Skeleton className="h-48 w-full" />
            )}
          </section>

          <section aria-labelledby="watch-h">
            <h2 id="watch-h" className="section-title">
              Needs attention first
            </h2>
            <p className="mb-3 text-sm text-muted">Highest estimated risk of leaving, with the main reason.</p>
            {watchlist.isError ? (
              <ErrorState error={watchlist.error} onRetry={() => void watchlist.refetch()} />
            ) : watchlist.data ? (
              watchlist.data.length === 0 ? (
                <p className="rule-top pt-3 text-muted">Nobody is flagged right now.</p>
              ) : (
                <ol className="rule-top">
                  {watchlist.data.map((item) => (
                    <li key={item.id} className="border-b border-line py-3">
                      <Link to={`/students/${item.id}`} className="font-semibold underline-offset-2 hover:underline">
                        {item.name}
                      </Link>
                      <div className="text-sm text-muted">
                        {item.studentCode} · {item.department} · Year {item.grade}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                        <RiskBadge level={item.riskLevel} prob={item.prob} />
                        {item.topFactor && <span className="text-sm">{item.topFactor}</span>}
                      </div>
                      <div className="mt-0.5 text-sm text-muted">Follow-up: {STATUS_LABELS[item.followUpStatus]}</div>
                    </li>
                  ))}
                </ol>
              )
            ) : (
              <div className="space-y-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {!noStudents && (
        <div className="mt-10 grid gap-8 lg:grid-cols-2">
          <section aria-labelledby="scatter-h">
            <h2 id="scatter-h" className="section-title">
              Attendance against score
            </h2>
            <p className="mb-3 text-sm text-muted">Each mark is a student. Shape shows the risk band.</p>
            {cohort.isError ? (
              <ErrorState error={cohort.error} onRetry={() => void cohort.refetch()} />
            ) : cohort.data ? (
              <AttendanceScoreScatter points={cohort.data} />
            ) : (
              <Skeleton className="h-72 w-full" />
            )}
          </section>

          <section aria-labelledby="grade-h">
            <h2 id="grade-h" className="section-title">
              Risk by year of study
            </h2>
            <p className="mb-3 text-sm text-muted">Students in each risk band, year by year.</p>
            {byGrade.isError ? (
              <ErrorState error={byGrade.error} onRetry={() => void byGrade.refetch()} />
            ) : byGrade.data ? (
              <RiskByYearBars data={byGrade.data} />
            ) : (
              <Skeleton className="h-64 w-full" />
            )}
          </section>
        </div>
      )}

      {!noStudents && (
        <section aria-labelledby="drivers-h" className="mt-10">
          <h2 id="drivers-h" className="section-title">
            What is driving risk
          </h2>
          <p className="mb-3 text-sm text-muted">
            The reasons that most often raise risk among students flagged medium or high.
          </p>
          {drivers.isError ? (
            <ErrorState error={drivers.error} onRetry={() => void drivers.refetch()} />
          ) : drivers.data ? (
            drivers.data.length === 0 ? (
              <p className="text-muted">No drivers to show until students have been scored.</p>
            ) : (
              <ul className="rule-top max-w-3xl">
                {drivers.data.map((driver) => (
                  <li
                    key={driver.key}
                    className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 border-b border-line py-3"
                  >
                    <span className="font-semibold">{driver.label}</span>
                    <span className="num text-sm">
                      {driver.students} students · {Math.round(driver.share * 100)}%
                    </span>
                    <div className="col-span-2 h-2 rounded-sm bg-sunken" aria-hidden="true">
                      <div
                        className="h-full rounded-sm bg-high"
                        style={{ width: `${Math.max(3, driver.share * 100)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )
          ) : (
            <Skeleton className="h-40 w-full max-w-3xl" />
          )}
        </section>
      )}
    </>
  );
}
