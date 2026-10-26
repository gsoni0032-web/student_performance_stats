# Pathway API reference

Base path: `/api/v1`. Interactive OpenAPI docs are served at `/api/v1/docs` (unless `ENABLE_DOCS=false`).
JSON bodies and responses use **camelCase**; query parameters use **snake_case** (`class_id`, `page_size`).
Authenticated routes need `Authorization: Bearer <accessToken>`.

Pathway is built for colleges. A "grade" in the data is the **year of study (1 to 6)**; a class is
`department + year + section + academic year` (for example Computer Science, year 2, section A, 2026-27).

## Conventions

**Errors** always have one shape:

```json
{ "error": { "code": "validation_error", "message": "Invalid input", "details": [{ "field": "body.email", "message": "..." }] } }
```

Common codes: `validation_error` (422), `bad_request` (400), `unauthorized` / `token_invalid` / `invalid_credentials`
(401), `forbidden` (403), `not_found` (404), `conflict` (409), `account_locked` (423), `rate_limited` (429, with a
`Retry-After` header), `no_model` (409, no trained model yet), `server_error` (500).

**Pagination**: every list returns `{ "items": [], "total": 0, "page": 1, "pageSize": 25, "pages": 1 }` and accepts
`page` (from 1) and `page_size` (1 to 100).

**Roles**

| Role | Can do |
| --- | --- |
| `admin` | Everything: users, classes, imports, retraining, thresholds, deleting students. Sees every student. |
| `teacher` (faculty mentor) | Sees only students in assigned classes. Can add students to those classes, add monthly records, re-score, edit students and update follow-ups. |
| `viewer` | Read-only, assigned classes. |

**Risk levels**: `low`, `medium`, `high`. Defaults: medium from 0.30, high from 0.60 (admin-editable). `prob` is the
calibrated probability of dropping out before the next term.

## Auth

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | `/auth/login` | `{ email, password }` | `{ accessToken, refreshToken, tokenType, expiresIn }` |
| POST | `/auth/refresh` | `{ refreshToken }` | New token pair. The refresh token rotates; reusing an old one revokes the session. |
| POST | `/auth/logout` | `{ refreshToken }` | 204 |
| GET | `/auth/me` | | `User` |
| POST | `/auth/change-password` | `{ currentPassword, newPassword }` | 204. Revokes other sessions. |

`User = { id, name, email, role, isActive, createdAt, classIds: number[] }`

Login is rate limited per IP (`LOGIN_RATE_LIMIT` per minute). An account locks for `LOCKOUT_MINUTES` after
`MAX_FAILED_LOGINS` consecutive failures.

## Students

`StudentSummary` (list items):

```json
{
  "id": 1, "studentCode": "CS24-0001", "name": "Asha Verma",
  "department": "Computer Science", "grade": 2, "section": "A", "classId": 3,
  "scoreSeries": [71.2, 68.0], "attSeries": [88.0, 84.5],
  "features": { "attendance": 86.3, "score": 69.6, "assignments": 80.0, "failures": 1, "late": 2.5, "parent": 3, "trend": -1.7 },
  "prob": 0.41, "riskLevel": "medium", "followUpStatus": "not_started"
}
```

`features`, `prob` and `riskLevel` are `null` when a student has no records or has not been scored.

`StudentDetail = StudentSummary + { guardianContact, droppedOut, months: ["2026-05", ...], nextTermScore, modelVersion, predictedAt, factors: Factor[], suggestedActions: string[], followUp: FollowUp }`

`Factor = { key, label, display, impact, driver }`: `label` reads like "Low attendance", `display` is the value ("61%"),
`impact` is the factor's share (percent) of the total SHAP movement, and `driver` is `raises` or `lowers`.

`FollowUp = { status: "not_started" | "guardian_contacted" | "support_plan_active" | "resolved", notes, updatedAt, updatedBy }`

`MonthlyRecord = { month: "YYYY-MM-DD", avgScore (0-100), attendancePct (0-100), assignmentsPct (0-100), lateArrivals (0-31), failedSubjects (0-12), guardianEngagement (1-5) }`

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/students` | Query: `q, class_id, grade, department, risk (low/medium/high/unscored), status, page, page_size, sort (risk/name/code/grade/status), order (asc/desc)`. |
| POST | `/students` | **Add a student.** Admin, or teacher for an assigned class. Body `{ studentCode, name, classId, guardianContact?, record? }`. Scores the student when a record and an active model exist. Returns `StudentDetail`, 201. 409 if the code exists. |
| GET | `/students/{id}` | `StudentDetail` |
| PUT | `/students/{id}` | Admin or teacher. `{ name?, classId?, guardianContact?, droppedOut? }` |
| DELETE | `/students/{id}` | Admin only. 204. |
| POST | `/students/{id}/records` | Admin or teacher. Body `MonthlyRecord`; upserts by month, re-scores, returns `StudentDetail`. |
| POST | `/students/{id}/predict` | Admin or teacher. Re-score one student. |
| GET | `/students/{id}/intervention` | `FollowUp` |
| PUT | `/students/{id}/intervention` | Admin or teacher. `{ status, notes }` (notes up to 2000 characters). |

## Predictions

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/predict` | What-if. Body `{ attendance, score, assignments, failures, late, parent, trend, grade? }` with ranges 0-100, 0-100, 0-100, 0-12, 0-31, 1-5, -20 to 20, year 1-6. Returns `{ prob, riskLevel, nextTermScore, factors, suggestedActions, modelVersion }`. Nothing is stored. |
| POST | `/predictions/batch` | Admin. Re-score every student. Returns `{ updated, skipped, modelVersion }`. |

## Dashboard (scoped to the students the caller may see)

| Path | Response |
| --- | --- |
| `GET /dashboard/summary` | `{ studentsTracked, avgAttendance, avgScore, highRisk, mediumRisk, lowRisk, unscored, attendanceChange, scoreChange, highRiskChange, latestMonth }` (changes are against the previous month) |
| `GET /dashboard/cohort?limit=` | `[{ id, name, grade, prob, riskLevel, attendance, score }]`, riskiest first |
| `GET /dashboard/risk-by-grade` | `[{ grade, low, medium, high, unscored }]` |
| `GET /dashboard/drivers` | `[{ key, label, students, share, avgImpact }]` |
| `GET /dashboard/watchlist?limit=8` | `[{ id, name, studentCode, department, grade, prob, riskLevel, topFactor, followUpStatus }]` |

Aggregates are cached for `DASHBOARD_CACHE_SECONDS` and cleared on any write.

## Classes

`Class = { id, department, grade, section, academicYear, label, studentCount, teacherIds }`

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/classes` | Paginated. Teachers and viewers see only assigned classes. |
| POST | `/classes` | Admin. `{ department, grade (1-6), section, academicYear: "2026-27" }` |
| PUT | `/classes/{id}` | Admin. Same body. |
| DELETE | `/classes/{id}` | Admin. 409 while the class still has students. |

## Users (admin)

| Method | Path | Body |
| --- | --- | --- |
| GET | `/users` | Query `page, page_size, q`. |
| POST | `/users` | `{ name, email, password, role, classIds? }` |
| PUT | `/users/{id}` | `{ name?, role?, isActive?, password?, classIds? }` |
| DELETE | `/users/{id}` | 204. You cannot delete yourself. |
| GET | `/audit` | Paginated audit log, newest first. |

Password policy: 10 to 72 characters with an upper-case letter, a lower-case letter and a digit.

## Data (admin imports, anyone exports their own scope)

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/data/import?dry_run=true&skip_invalid=false` | Multipart field `file` (CSV, up to 5 MB). Returns `{ dryRun, imported, rowsRead, rowsValid, students, records, issues: [{ row, column, message }], preview }`. With `dry_run=true` nothing is written. Without `skip_invalid`, any bad row stops the import. |
| GET | `/data/export` | CSV of the students matching the same filters as `/students`. |

Columns are documented in [data-format.md](data-format.md).

## Model and settings

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/model/info` | `{ active, versions, training: { status, message, started_at, finished_at, version }, thresholds }` |
| POST | `/model/retrain` | Admin. 202; training runs in the background. Poll `/model/info`. |
| POST | `/model/activate/{version}` | Admin. Roll back or forward; every student is re-scored. |
| GET | `/settings/thresholds` | `{ medium, high }` |
| PUT | `/settings/thresholds` | Admin. `{ medium, high }` with `0 < medium < high < 1`; stored predictions are relabelled. |

## Health

`GET /health` (also `/api/v1/health`) returns `{ "status": "ok", "version": "..." }` after a database round trip.
