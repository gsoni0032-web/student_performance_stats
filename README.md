# Pathway

**Student performance and dropout prediction for colleges.**

Pathway brings attendance, marks and follow-ups for every class into one register and estimates which students may leave
before the next term, with a plain-language reason for each score. It is built for faculty mentors and student-success
offices. A prediction starts a conversation; it is never the whole decision (see [docs/model-card.md](docs/model-card.md)).

- **Overview**: KPI band, a cohort register (one square per student, riskiest first), "needs attention first" list,
  attendance-vs-score scatter, risk by year of study and the top risk drivers.
- **Students**: searchable, sortable, filterable and paginated table with sparklines, risk badges and follow-up status, CSV export.
- **Add student**: a form for one student with up to twelve months of figures, scored the moment it is saved.
- **Student page**: risk gauge, month-by-month chart, SHAP factor bars, suggested next steps, follow-up status and notes, add a month, "try what-if".
- **What-if**: sliders for every input with a live gauge.
- **Admin**: users and class assignments, classes, CSV import with preview and per-row error report, model metrics with retrain and rollback, risk thresholds, audit log.
- **Roles**: administrator, faculty mentor (only their assigned classes) and read-only viewer, enforced on the backend.
- **Accessibility**: risk is always shown with a shape and a word as well as a colour; keyboard, screen-reader, dark mode and reduced-motion support; works from 360 px phones (bottom tab bar) to wide desktops.

| Layer | Stack |
| --- | --- |
| Frontend | React 18, TypeScript (strict), Vite, Tailwind CSS, React Router, TanStack Query, Recharts, React Hook Form + Zod |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Uvicorn |
| Database | PostgreSQL 16 (SQLite only for local development and tests) |
| ML | scikit-learn, XGBoost, pandas, NumPy, SHAP, joblib |
| Tooling | Docker and Compose, GitHub Actions, pytest, Vitest, Playwright, Ruff, ESLint, Prettier |

```
pathway/
  backend/    FastAPI app, migrations, tests, Dockerfile
  frontend/   React app, tests, e2e flows, Dockerfile, Vercel/Netlify config
  ml/         training, evaluation and fairness scripts, sample data
  docs/       architecture, API, model card, data format, privacy
  deploy/     Render blueprint, VPS compose override, host Nginx config
  docker-compose.yml   .env.example   .github/workflows/ci.yml
```

---

## 1. Run it locally

### Option A: Docker (one command)

Needs Docker with Compose v2.

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and SECRET_KEY. Generate a key with:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up --build -d          # db, backend (runs migrations) and frontend
docker compose ps                     # wait until all three show "healthy"

# Demo data: 600 synthetic students, demo accounts, and the first trained model (takes a minute or two)
docker compose exec backend python -m app.cli seed --demo-password 'Choose-A-Demo-Pass-1'
```

Open <http://localhost:8080> and sign in as `admin@pathway.example` with the demo password.
API docs: <http://localhost:8080/api/v1/docs>.

### Option B: without Docker (SQLite, hot reload)

```bash
# Terminal 1: backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                         # SQLite, local CORS: fine for development
alembic upgrade head
python -m app.cli seed --demo-password 'Choose-A-Demo-Pass-1'
uvicorn app.main:app --reload                                # http://localhost:8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev                                                  # http://localhost:5173 (proxies /api to :8000)
```

### Commands you will need

Run these from `backend/` (or prefix with `docker compose exec backend` when using Docker).

| Task | Command |
| --- | --- |
| Apply migrations | `alembic upgrade head` (the container does this on every start) |
| Create the first administrator | `python -m app.cli create-admin --email you@college.edu --name "Your Name"` (prompts for a password, or set `ADMIN_PASSWORD`) |
| Reset an administrator's password | `python -m app.cli create-admin --email you@college.edu --reset` |
| Load demo data and train | `python -m app.cli seed --demo-password '...'` (`--students 600 --months 6 --skip-train` are optional) |
| Import a CSV | `python -m app.cli import-csv path/to/file.csv --dry-run`, then again without `--dry-run` |
| Train a model from the data in the database | `python -m app.cli train` |
| Re-score every student | `python -m app.cli predict-all` |

**Starting with real data instead of the demo:** create an administrator, create your classes in the app (or let the import create them),
import your CSV (columns in [docs/data-format.md](docs/data-format.md)), then press **Retrain model** on Admin → Model. Only students with a
known outcome (`dropped_out`) train the model; the rest are scored by it.

---

## 2. Environment variables

Set these in `.env` (Docker) or in your host's dashboard. Never commit real values; `.gitignore` already excludes `.env`.

### Backend

| Variable | What it does | Example |
| --- | --- | --- |
| `APP_ENV` | `development`, `test` or `production`. Production refuses a `SECRET_KEY` that starts with `change-me`. | `production` |
| `SECRET_KEY` | Signs access tokens. At least 32 random characters. **Required.** | output of `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | SQLAlchemy URL. `postgres://` and `postgresql://` links from hosts are accepted. | `postgresql+psycopg://pathway:pw@db:5432/pathway` |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API. | `https://pathway.vercel.app` |
| `FORCE_HTTPS` | Redirect http to https and send HSTS. Turn on behind a TLS terminator. | `true` |
| `ENABLE_DOCS` | Serve Swagger at `/api/v1/docs`. | `true` |
| `ACCESS_TOKEN_MINUTES` | Access token lifetime. | `15` |
| `REFRESH_TOKEN_DAYS` | Refresh token lifetime. | `7` |
| `MAX_FAILED_LOGINS` | Failed sign-ins before an account locks. | `5` |
| `LOCKOUT_MINUTES` | How long a lock lasts. | `15` |
| `LOGIN_RATE_LIMIT` | Sign-in attempts per IP per window. | `10` |
| `LOGIN_RATE_WINDOW_SECONDS` | Rate-limit window. | `60` |
| `DASHBOARD_CACHE_SECONDS` | How long dashboard aggregates are cached. `0` disables. | `60` |
| `MODEL_DIR` | Where model files are written. Also stored in the database as a backup. | `/data/models` |
| `LOG_LEVEL` / `LOG_JSON` | Log verbosity, and JSON lines (`true`) or readable text (`false`). | `INFO` / `true` |
| `ML_CANDIDATES` | Model families to compare when training. | `logreg,random_forest,xgboost` |
| `TRAINING_SEARCH_ITERATIONS` | Hyper-parameter search draws per model. | `12` |
| `PORT` | Port Uvicorn binds (set by Render and Railway). | `8000` |

### Docker Compose only

| Variable | What it does | Example |
| --- | --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER` | Database name and user. | `pathway` |
| `POSTGRES_PASSWORD` | Database password. **Required.** | a long random string |
| `WEB_PORT` | Host port for the web app. | `8080` |

### Frontend (build time)

| Variable | What it does | Example |
| --- | --- | --- |
| `VITE_API_URL` | Base URL of the API. Leave as `/api/v1` when the web app and API share a domain. | `https://pathway-api.onrender.com/api/v1` |
| `VITE_DEV_API_TARGET` | Dev server proxy target. | `http://localhost:8000` |

### CLI and end-to-end tests

| Variable | What it does |
| --- | --- |
| `ADMIN_PASSWORD`, `SEED_DEMO_PASSWORD` | Non-interactive passwords for `create-admin` and `seed`. |
| `E2E_BASE_URL`, `E2E_EMAIL`, `E2E_PASSWORD` | Where Playwright runs and which demo account it signs in with (`http://localhost:8080`, `admin@pathway.example`, the demo password). |

---

## 3. Deploy

Two shapes work: **everything on one server** (section 3e) or **frontend on Vercel/Netlify and backend plus Postgres on Render/Railway**
(3b, 3c and 3d). Either way the order is: database, backend, migrations (automatic), first admin, frontend, CORS.

### 3a. Before you deploy

1. Push the repository to GitHub (section 6).
2. Generate a `SECRET_KEY` and keep it somewhere safe (changing it signs everyone out).
3. Decide who the first administrator is.

### 3b. Backend and Postgres on Render

1. In Render choose **New → Blueprint**, select your repository and set the blueprint path to `deploy/render.yaml`. It creates the Postgres
   database and the Docker web service (root directory `backend`) and fills `SECRET_KEY` and `DATABASE_URL` for you.
   *(Or create them by hand: a PostgreSQL instance, then a Web Service from the `backend` folder using its Dockerfile, health check path `/health`.)*
2. Set `CORS_ORIGINS` to your frontend's URL (for example `https://pathway.vercel.app`; you can set a placeholder and fix it after deploying the frontend in 3d).
3. Deploy. The container runs migrations, then starts. Check `https://<your-api>.onrender.com/health`.
4. Create the first admin. If your plan has a Shell tab, open it and run `python -m app.cli create-admin --email you@college.edu --name "Your Name"`.
   Otherwise run the same command on your own machine against the database: copy the database's **External** connection string and run, from `backend/`:

   ```bash
   DATABASE_URL='<external connection string>' SECRET_KEY='any-32-or-more-characters-for-the-cli-only' python -m app.cli create-admin --email you@college.edu --name "Your Name"
   ```

5. Sign in, import your CSV (or run `seed` the same way for demo data), and train the model from **Admin → Model**.

The model file is also kept in the database, so a restart that loses the disk does not lose the model. The login rate limiter and dashboard
cache live in one process, so keep a single instance.

### 3c. Backend and Postgres on Railway

1. **New Project → Deploy from GitHub repo**, then set the service's **Root Directory** to `backend` (Railway builds the Dockerfile).
2. **+ New → Database → PostgreSQL**.
3. On the backend service, add variables: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`, `SECRET_KEY`, `APP_ENV=production`,
   `FORCE_HTTPS=true`, `CORS_ORIGINS=https://your-frontend-url`. Railway supplies `PORT`.
4. Under **Settings → Networking** generate a public domain, and set the health check path to `/health`.
5. Create the first admin with the Railway CLI from `backend/`: `railway link`, then
   `railway run python -m app.cli create-admin --email you@college.edu --name "Your Name"`
   (`railway run` uses your service's variables; if the database host is internal-only, use the public `DATABASE_PUBLIC_URL` as `DATABASE_URL` for that command).

### 3d. Frontend on Vercel or Netlify

The API URL is baked in at build time, so set it before the first build.

**Vercel:** New Project → import the repo → **Root Directory `frontend`** → add environment variable
`VITE_API_URL=https://<your-api-domain>/api/v1` → Deploy. `vercel.json` handles the single-page-app rewrites and headers.

**Netlify:** Add new site → import the repo → **Base directory `frontend`** → add `VITE_API_URL` as above → Deploy.
`netlify.toml` sets the build command, publish directory and redirects.

Then go back to the backend and make sure `CORS_ORIGINS` is exactly the frontend's origin (scheme and host, no trailing slash, no path).
If you add a custom domain later, add it to `CORS_ORIGINS` too (comma-separated).

### 3e. A single VPS with Docker, Nginx and HTTPS (Let's Encrypt)

Works on any Ubuntu/Debian server with a domain pointing at it (an `A` record to the server's IP). Needs Docker with Compose 2.24 or newer.

```bash
# 1. Install Docker, Nginx and Certbot
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
curl -fsSL https://get.docker.com | sudo sh

# 2. Get the code and configure it
git clone https://github.com/<you>/pathway.git && cd pathway
cp .env.example .env
nano .env     # set POSTGRES_PASSWORD, SECRET_KEY, CORS_ORIGINS=https://pathway.example.com, FORCE_HTTPS=true

# 3. Start the stack; the web container listens on 127.0.0.1:8080 only
sudo docker compose -f docker-compose.yml -f deploy/docker-compose.vps.yml up -d --build

# 4. Put Nginx in front and add HTTPS
sudo cp deploy/nginx-host.conf /etc/nginx/sites-available/pathway
sudo sed -i 's/pathway.example.com/YOUR-DOMAIN/' /etc/nginx/sites-available/pathway
sudo ln -s /etc/nginx/sites-available/pathway /etc/nginx/sites-enabled/pathway
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR-DOMAIN --redirect       # installs the certificate and renews it automatically

# 5. First administrator, then (optionally) demo data
sudo docker compose exec backend python -m app.cli create-admin --email you@college.edu --name "Your Name"
sudo docker compose exec backend python -m app.cli seed --demo-password 'Choose-A-Demo-Pass-1'
```

Open the firewall for 80 and 443 only (`sudo ufw allow 'Nginx Full'`). **Back up the database** at least daily:
`sudo docker compose exec -T db pg_dump -U pathway pathway | gzip > pathway-$(date +%F).sql.gz`.
Update with `git pull && sudo docker compose -f docker-compose.yml -f deploy/docker-compose.vps.yml up -d --build`.

### 3f. Post-deploy checklist

1. **Health:** `curl https://<your-domain>/health` (or `<api>/health`) returns `{"status":"ok",...}`.
2. **Login:** sign in as the administrator. A wrong password shows a clear error, not a blank screen.
3. **Roles:** create a faculty mentor on Admin → Users, assign a class, sign in as them in a private window and confirm they see only that class.
4. **Add student:** add one student with a few months of figures; they appear on Students and are scored.
5. **Prediction:** open a student and check the gauge, factors and next steps; open What-if and move the attendance slider; the risk changes.
6. **Follow-up:** change a student's follow-up status, reload, and check it stuck. Check Admin → Audit log shows the sign-in and the change.
7. **Model:** Admin → Model shows recall, precision and PR-AUC for the active version.
8. **Security:** the address starts with `https://`, `FORCE_HTTPS=true`, `SECRET_KEY` is not the example, and `.env` is not in Git.
9. **Backups:** a database backup exists and you have tried restoring it once.

---

## 4. Tests and quality

```bash
# Backend: lint, then tests with coverage (the run fails below 80%)
cd backend && ruff check . && pytest

# Frontend: lint, types, unit tests, production build
cd frontend && npm run lint && npm run typecheck && npm test && npm run build

# End-to-end flows (login, open an at-risk student and update follow-up, run a what-if)
docker compose up --build -d
docker compose exec backend python -m app.cli seed --demo-password 'Choose-A-Demo-Pass-1'
cd frontend && npx playwright install chromium
E2E_PASSWORD='Choose-A-Demo-Pass-1' npm run e2e
```

Run `npm run format` once in `frontend/` before your first commit to apply Prettier (CI does not fail on formatting). GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the backend job, the frontend job
and the end-to-end flows against the Docker stack on every push and pull request.

**Tip:** run `npm install` once in `frontend/` and commit the generated `package-lock.json` so installs are reproducible
(the Dockerfile and CI work with or without it).

---

## 5. Assumptions

- "College students" means **year of study 1 to 6** replaces school grades, and a class is department + year + section + academic year.
- Faculty mentors are the `teacher` role. Teachers may add students to their own classes; only administrators delete students, manage users or retrain.
- A prediction is the probability of dropping out before the next term. The demo labels are synthetic.
- Demographic attributes are not collected. The fairness script takes a separate audit file.
- The bundled demo data is invented. Metrics on it show how the pipeline behaves, not how well it will do on your college.
- One backend instance. Moving to several needs the rate limiter and cache in Redis.
- Docs: [architecture](docs/architecture.md) · [API](docs/API.md) · [model card](docs/model-card.md) · [data format](docs/data-format.md) · [privacy](docs/privacy.md) · [ML scripts](ml/README.md).

## 6. Push to GitHub

```bash
git init -b main
git add .
git status            # check that no .env file is listed
git commit -m "Pathway: student performance and dropout prediction"
git remote add origin https://github.com/<you>/pathway.git
git push -u origin main
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Backend exits with "SECRET_KEY must be replaced" | Put a real random value in `.env` (it must not start with `change-me`). |
| Browser shows a CORS error | `CORS_ORIGINS` must equal the frontend's origin exactly, with no trailing slash. |
| Frontend calls itself instead of the API on Vercel/Netlify | `VITE_API_URL` was missing at build time. Set it and redeploy. |
| "There is no trained model yet" | Admin → Model → Retrain (needs students with a `dropped_out` value). |
| Training says too few students | Import more history; a few hundred labelled students is a sensible minimum. |
| Locked out after failed sign-ins | Wait `LOCKOUT_MINUTES`, or run `create-admin --reset` for an admin. |
| `docker compose` says `!override` is unknown | Upgrade Docker Compose to 2.24 or newer, or publish port 8080 on all interfaces and firewall it. |
