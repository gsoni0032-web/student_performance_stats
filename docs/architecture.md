# Architecture

```
Browser (React, Vite build)
   │  HTTPS, JSON (camelCase), Bearer access token
   ▼
Nginx (frontend container) ──/api──▶ FastAPI (backend container) ──▶ PostgreSQL
   serves the static app                │                              (volume: pgdata)
                                        ├─ services/   business rules, scoping by role
                                        ├─ ml/         features, training, SHAP, model registry
                                        └─ model files (volume: modelstore, joblib + metrics JSON)
```

## Backend (`backend/app`)

| Folder | Role |
| --- | --- |
| `api/v1` | Thin routers: parse input, call a service, shape the response. `deps.py` holds auth and role checks. |
| `core` | Settings, database, security (bcrypt, JWT), errors, logging, rate limiting, cache. |
| `models` | SQLAlchemy 2 tables (`users`, `classes`, `students`, `monthly_records`, `predictions`, `interventions`, `model_versions`, `settings`, `audit_log`, `refresh_tokens`). |
| `schemas` | Pydantic v2 request and response models. |
| `services` | Everything that decides things: student scope per role, imports, predictions, dashboard aggregates, audit. |
| `ml` | `features.py` (feature engineering shared by training and serving), `pipeline.py` (train, compare, calibrate), `explain.py` (SHAP factors and suggested actions), `registry.py` (versioned model files), `synthetic.py` (demo data). |
| `alembic` | Migrations. The container runs `alembic upgrade head` on every start. |

### Decisions worth knowing

- **Role scoping lives in `student_service.class_scope`**; every list, detail, export and dashboard query goes through it, so a
  mentor cannot see another class by guessing an ID (they get a 404).
- **Predictions are stored.** Lists and dashboards read the latest stored prediction instead of running the model per
  request. Saving a month, re-scoring, retraining or rolling back refreshes them.
- **Risk labels are derived from thresholds at write time** and relabelled when an admin changes the thresholds.
- **Training runs in a background thread** and reports progress through `GET /model/info`. Only one run can be active.
- **Model versions are immutable files** (`model_vN.joblib`, `metrics_vN.json`). Rolling back flips the active flag and re-scores.
- **Refresh tokens are random, stored hashed and rotated.** Reusing an old token revokes the whole session.
- **The login rate limiter and dashboard cache are in process.** Run one backend instance (or move both to Redis) if you scale out.

## Frontend (`frontend/src`)

| Folder | Role |
| --- | --- |
| `api` | `client.ts` (fetch wrapper with token refresh and error mapping), `hooks.ts` (TanStack Query hooks), `types.ts`. |
| `pages` | One file per screen: Overview, Students, Student detail, Add student, What-if, Settings and the admin pages. |
| `components` | Shared pieces: risk badge, gauge, cohort register, charts, modal, form field. |
| `hooks`, `lib` | Auth, toast and theme state; formatting and Zod schemas. |

Accessibility is built in rather than added later: risk always has a shape and a word as well as a colour, every control is
reachable by keyboard, charts have text alternatives and tables, dialogs are native `<dialog>` elements, and animation stops
when the system asks for reduced motion.

## Data flow for "Add student"

1. `StudentNewPage` validates the form with Zod (ID format, ranges, one entry per month).
2. `POST /students` creates the student with the first month; the service scores them if a model is active.
3. Remaining months are saved with `POST /students/{id}/records`, each one refreshing the score.
4. Cached dashboard aggregates are cleared, so the new student shows up on the Overview straight away.
