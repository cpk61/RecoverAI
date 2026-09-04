# RecoverAI — 5 Minute Pitch Script

## 0:00–0:30 — Problem
Hi, this is RecoverAI, my Track 03 AI Revenue Recovery project. A failed payment is not just a classification problem: a useful system has to decide whether to retry, wait, switch the payment path, nudge the customer, or stop. Blind retries can create poor customer experience and unsafe money-adjacent automation.

## 0:30–1:05 — What the agent does
RecoverAI takes failed-payment records and runs a closed recovery loop. It scores recovery probability, then a bounded policy chooses a failure-specific intervention. Network failures can get a short retry, insufficient-funds cases wait before another attempt, bank declines prefer an alternate payment path, expired cards get an update-payment link, and abandoned checkouts get one bounded reminder.

The important part is what it refuses to do. After the retry ceiling is reached, it stops and escalates. Low-confidence cases also go to human review.

## 1:05–1:45 — Model
The recovery scorer is logistic regression trained on synthetic failed-payment data. Features include amount, failure reason, payment channel, customer segment, successful payment history, retry count, and time since failure.

The dataset is split into training and held-out test data. In the current reproducible run, ROC-AUC is about 0.77. These are synthetic-data metrics, not merchant performance claims.

## 1:45–2:35 — Bounded policy and audit trail
The model does not directly move money. Its score enters a deterministic policy layer with explicit gates. Every decision records payment ID, recovery probability, action, reasoning, stop status, and simulated outcome.

A payment with too many retries becomes STOP_AND_ESCALATE. A low-confidence case becomes HUMAN_REVIEW. Every money-adjacent action is intended to be explainable, bounded, and auditable.

## 2:35–3:20 — Batch measurement
The demo processes an 80-record synthetic batch. The simulator uses the same random draw for baseline and intervention so comparison is controlled. The dashboard reports attempted actions, stopped or escalated cases, recovered count, simulated recovered amount, and simulated incremental amount over baseline.

Again, the rupee values are simulation outputs only.

## 3:20–4:05 — Architecture
The architecture has failed-payment ingestion, feature extraction, ML scoring, bounded policy, isolated action boundary, verification, audit log, and dashboard/API.

The current action boundary is simulated. The next iteration is to connect Razorpay test-mode events and gated test actions while keeping secrets outside the repository.

## 4:05–4:35 — Why this design
I did not want to build a chatbot around payments. The harder problem is control: when should the system act, when should it stop, and can a reviewer understand why it made a decision? RecoverAI separates prediction from policy and keeps a full audit trail.

## 4:35–5:00 — Close
RecoverAI is a working prototype with FastAPI, reproducible synthetic data, held-out metrics, smoke tests, APIs, and an auditable recovery loop. The next iteration is Razorpay test-mode integration and end-to-end exception handling.
