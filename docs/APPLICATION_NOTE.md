# Short Application Note

I built RecoverAI for the AI Revenue Recovery track: a bounded agent that predicts recoverability of failed payments, selects a failure-specific recovery action, enforces retry/confidence stopping rules, and records a full decision audit trail.

The prototype includes a reproducible synthetic dataset, held-out model metrics, an 80-record batch recovery simulation, FastAPI dashboard/API, smoke tests, and explicit human escalation. The current action boundary is simulated; the next iteration is a Razorpay test-mode adapter with secrets kept outside the public repo.

I deliberately separated ML prediction from the money-action policy so every action can be explained, bounded, stopped, and audited.
