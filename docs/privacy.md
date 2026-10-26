# Privacy note

Pathway holds academic records about identifiable students, so treat it as confidential personal data.
This note is a starting point for your institution's own policy; it is not legal advice.

## Data minimisation

- The model reads **eight academic signals** only: attendance, average score, assignments submitted, backlogs,
  late arrivals, guardian engagement, score trend and year of study. Names, contact details and any sensitive
  attribute (gender, religion, caste, ethnicity, disability) are never model inputs.
- The application does not collect sensitive attributes. If you hold such data for fairness auditing, keep it in a
  separate file and use it only with `ml/fairness_check.py`; never import it into Pathway.
- `guardian_contact` is optional. Leave it blank if the advisor can find the contact elsewhere.
- Follow-up notes should record actions and agreements, not health, family or disciplinary details.

## Access

- Faculty mentors see only the classes assigned to them; viewers are read-only.
- Passwords are hashed with bcrypt. Accounts lock after repeated failures and refresh tokens rotate on every use.
- The audit log records sign-ins, imports, exports, retraining, model changes and follow-up changes.
- Serve the app over HTTPS only (`FORCE_HTTPS=true` behind a TLS terminator).

## Retention (suggested defaults)

| Data | Keep | Then |
| --- | --- | --- |
| Active students' monthly records | While enrolled | Delete or anonymise within 12 months of leaving |
| Follow-up notes | While enrolled | Delete with the student |
| Predictions | Latest per student | Replaced on every re-score |
| Audit log | 12 months | Archive or delete |
| Database backups | 30 days | Delete |

An administrator can delete a student (and every record, prediction and note about them) from the student's page.
Decide who answers access and erasure requests before go-live, and tell students what the system is for.

## Using predictions fairly

A prediction is a prompt for a supportive conversation. It must not be used to deny a place, withdraw funding,
discipline or otherwise disadvantage a student. See [model-card.md](model-card.md).
