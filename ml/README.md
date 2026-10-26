# ML scripts

Stand-alone tools that use the same pipeline as the web app, so you can train, evaluate and audit without a database.
Run them from the repository root with the backend dependencies installed (`pip install -r backend/requirements.txt`).

| Script | What it does |
| --- | --- |
| `generate_sample_data.py` | Writes `sample_data/students_sample.csv` (synthetic, import format) and `audit_groups_sample.csv` (a made-up group label for fairness demos). |
| `train_from_csv.py` | Trains and evaluates on a CSV and writes `model_vN.joblib` and `metrics_vN.json` to `--out`. |
| `evaluate_model.py` | Scores a saved model on a labelled CSV and prints the metrics. |
| `fairness_check.py` | Compares recall, false-positive rate and flag rate across groups from a separate audit file. |
| `map_uci_dataset.py` | Converts the public UCI dropout dataset into Pathway's import format. |

```bash
python ml/generate_sample_data.py --students 600
python ml/train_from_csv.py ml/sample_data/students_sample.csv --out ml/artifacts
python ml/evaluate_model.py ml/artifacts/model_v1.joblib ml/sample_data/students_sample.csv
python ml/fairness_check.py ml/artifacts/model_v1.joblib ml/sample_data/students_sample.csv ml/sample_data/audit_groups_sample.csv
```

The sample data is entirely synthetic: names are random combinations from short word lists, and no real person is represented.

## Training on the UCI dataset

The UCI dataset ["Predict Students' Dropout and Academic Success"](https://archive.ics.uci.edu/dataset/697) (CC BY 4.0) describes
about 4,400 Portuguese higher-education students. Download `data.csv` yourself, then:

```bash
python ml/map_uci_dataset.py data.csv ml/sample_data/uci_import.csv
python ml/train_from_csv.py ml/sample_data/uci_import.csv --out ml/artifacts/uci
# or load it into the app: cd backend && python -m app.cli import-csv ../ml/sample_data/uci_import.csv
```

Only students whose target is `Dropout` or `Graduate` are kept (still-enrolled students have no outcome yet). Each student becomes two
rows, one per semester, with the semester standing in for a month:

| Pathway column | Built from |
| --- | --- |
| `avg_score` | semester grade (0 to 20) × 5 |
| `attendance_pct` | evaluated units not skipped ÷ units evaluated |
| `assignments_pct` | units approved ÷ units enrolled |
| `failed_subjects` | units enrolled − units approved |
| `department` | `Course` code |
| `dropped_out` | 1 for `Dropout`, 0 for `Graduate` |
| `late_arrivals`, `guardian_engagement` | not in the dataset: set to 0 and 3 (constant, so they carry no signal) |

Expect a weaker result than on Pathway's monthly data: two time points give a poor trend, and attendance and assignments are
approximations. It is useful for checking the pipeline on real-world labels, not as a production model.
