# TRADEOFFS.md

# Deliberate Tradeoffs and Deferred Features

## 1. Real-Time ERP Integrations

Not implemented:

* SAP APIs
* Oracle ERP APIs
* Workday integrations

Why:
The prototype focused on ingestion architecture and normalization rather than enterprise authentication complexity.

CSV onboarding is also a realistic first-stage ESG implementation pattern.

---

# 2. Advanced Emission Factor Engine

Not implemented:

* region-specific emissions factors
* supplier-specific factors
* dynamic factor APIs

Why:
The goal was to demonstrate ingestion and workflow architecture within limited development time.

Simplified emissions calculations were sufficient for validating platform workflows.

---

# 3. Enterprise RBAC and Authentication

Not implemented:

* SSO
* RBAC
* tenant isolation
* granular permissions

Why:
The assignment emphasized ESG workflow handling rather than identity infrastructure.

The current architecture remains compatible with future RBAC integration.

---

# Additional Deferred Features

* OCR utility bill parsing
* AI anomaly detection
* automated ESG report generation
* real-time streaming ingestion
* PostgreSQL scaling
* Kubernetes deployment
* distributed job queues

These were intentionally deferred to prioritize:

* normalization quality
* auditability
* analyst UX
* deployment completeness
