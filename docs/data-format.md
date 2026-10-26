# CSV import format

One row per **student per month**. The first row must be a header using exactly these column names
(order does not matter). A ready-made template is in `frontend/public/import-template.csv`, and
`ml/sample_data/students_sample.csv` holds 600 synthetic students.

| Column | Required | Meaning | Allowed values |
| --- | --- | --- | --- |
| `student_code` | yes | Student ID or roll number, unique per student | 2 to 30 characters: letters, digits, `.`, `_`, `-` |
| `name` | yes | Full name | up to 120 characters |
| `department` | yes | Programme or department | up to 80 characters |
| `year` | yes | Year of study | whole number 1 to 6 |
| `section` | yes | Section | up to 10 characters |
| `month` | yes | The month the figures describe | `YYYY-MM` or `YYYY-MM-DD` |
| `avg_score` | yes | Average mark across subjects | 0 to 100 |
| `attendance_pct` | yes | Share of classes attended | 0 to 100 |
| `assignments_pct` | yes | Share of assignments submitted | 0 to 100 |
| `late_arrivals` | yes | Late arrivals in the month | whole number 0 to 31 |
| `failed_subjects` | yes | Backlogs: subjects currently failed or carried | whole number 0 to 12 |
| `guardian_engagement` | yes | How engaged the guardian is | whole number 1 to 5 |
| `academic_year` | no | Academic year of the class | `2026-27` (derived from `month` when blank) |
| `guardian_contact` | no | Phone or email | up to 120 characters |
| `dropped_out` | no | Known outcome, used to train the model | `1`/`0`, `yes`/`no`, `true`/`false` |

## How rows are handled

- Classes are created automatically from `department` + `year` + `section` + academic year.
- A student that already exists (same `student_code`) is updated, and a month that already exists is replaced.
- Every row is validated. Problems are reported with the **row number, column and a plain-language message**.
  By default one bad row stops the whole import; tick "skip rows with problems" (or pass `--skip-invalid`)
  to import the valid rows and get a report for the rest.
- Files are limited to 5 MB. The admin page always runs a dry run first and shows a preview.

## Command line

```bash
cd backend
python -m app.cli import-csv ../ml/sample_data/students_sample.csv --dry-run
python -m app.cli import-csv ../ml/sample_data/students_sample.csv
```

Exit code is 0 when every row was valid, 2 when any row had a problem.

## Which students train the model

Only students with a `dropped_out` value are used for training. Students without one are still scored.
