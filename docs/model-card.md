# Model card: Pathway dropout-risk model

## Intended use

Help advisors and faculty mentors notice college students who may leave before the next term, early enough for a
supportive conversation. It ranks students for attention; it does not decide anything about them.

**Out of scope:** admissions, scholarships or funding decisions, discipline, grading, or any use where a student could be
disadvantaged by a score alone.

> **Predictions support human decisions and must not be the only basis for action.** Always combine a score with what the
> student and their mentors know. Tell students that such a tool is used.

## What the model is

- **Task:** binary classification, with "dropped out" as the positive class, plus a secondary regression for next-term average score.
- **Candidates:** logistic regression, random forest and XGBoost, each tuned with randomised, cross-validated search.
- **Selection:** best PR-AUC on a validation split. The winner's probabilities are **calibrated** (sigmoid / Platt scaling) on that split.
- **Imbalance:** class weights (balanced weights, or `scale_pos_weight` for XGBoost), not synthetic oversampling.
- **Split:** stratified train, validation and test sets. Test numbers are measured once, on data never used for tuning.
- **Explanations:** SHAP values give each student's top factors, whether each raises or lowers risk, and a readable label such as "Low attendance (61%)".

### Inputs (eight academic signals)

`attendance`, `score`, `assignments`, `failures` (backlogs), `late` (arrivals per month), `parent` (guardian engagement, 1 to 5),
`trend` (score change per month, from a least-squares slope over recent months) and `grade` (year of study).
Rolling averages over the latest three months smooth single-month noise.

### Never used

Name, guardian contact, gender, religion, caste, ethnicity, disability, nationality or any other sensitive attribute.

## Why recall comes first

A missed student loses support they would have welcomed; a false alarm costs one check-in conversation. The flagging threshold is
therefore chosen to reach a target recall (85%) on the validation set, and the metrics screen shows recall and precision at that
threshold beside the threshold-free ROC-AUC and PR-AUC. Raising the thresholds in Admin trades recall for fewer false alarms.

## Metrics

Accuracy, precision, recall, F1, ROC-AUC, PR-AUC and the confusion matrix are stored with every model version and shown on the
**Admin → Model** page. Numbers on the bundled synthetic data say how the pipeline behaves, not how well it will work for your
college. **Retrain on your own history and read your own metrics before relying on any score.**

## Limitations

- Trained on whatever outcomes you import. Few labelled students, or labels from a different era, give a weak model.
- Bundled demo data is synthetic; its signal is stronger and cleaner than real records will be.
- Scores describe association, not cause. "Low attendance raises risk" does not mean fixing attendance alone removes the risk.
- Calibration can drift when teaching, assessment or the student mix changes. Retrain each term and watch the metrics.
- Small cohorts (a class of 20) make any single probability uncertain.
- Dropout depends on things the system cannot see: finances, health, family, accommodation, belonging.

## Fairness

The model never receives sensitive attributes, but proxies can exist (a department or year may correlate with a group).
`ml/fairness_check.py` compares recall (dropouts caught), false-positive rate and flag rate across groups using a **separate audit file**
that is never an input to the model:

```bash
python ml/fairness_check.py ml/artifacts/model_v1.joblib ml/sample_data/students_sample.csv ml/sample_data/audit_groups_sample.csv
```

It exits with code 2 when a gap in recall or false-positive rate exceeds `--max-gap` (default 0.10) between groups of at least `--min-group-size` students, so it can sit in a release checklist. If a group's recall is
much lower, investigate the data, consider a lower threshold or better features, and involve the people affected before using the model.

## Monitoring checklist

1. After each retrain: read recall, precision and PR-AUC; compare with the previous version; roll back if they dropped.
2. Each term: run the fairness check on a current audit file.
3. Review a sample of high-risk students with their mentors: do the listed factors match reality?
4. Record who acted on scores and what happened, so the next model can learn from outcomes.
