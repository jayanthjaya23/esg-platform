# DECISIONS.md

# Engineering Decisions and Assumptions

## Why CSV ingestion?

Most enterprise ESG onboarding workflows begin with CSV exports before direct ERP integrations are approved.

CSV ingestion was therefore selected as the most realistic prototype entry point.

---

# Why separate raw and normalized records?

Raw records preserve immutable source-of-truth payloads.

Normalized records support:

* ESG calculations
* analytics
* validation
* approvals

Separating these layers improves auditability and replay capability.

---

# Why SQLite?

SQLite reduced operational complexity and accelerated development for the assignment timeline.

The architecture can later migrate to PostgreSQL with minimal model changes.

---

# Why use Django REST Framework?

DRF provided:

* rapid API development
* serialization
* validation support
* scalable REST architecture

---

# Why React frontend?

React enabled:

* modular dashboard design
* dynamic chart rendering
* responsive analyst workflows
* modern SPA experience

---

# Why Render + Vercel deployment?

The combination provided:

* free deployment tiers
* fast setup
* GitHub integration
* realistic cloud deployment workflow

---

# Scope Handling Decisions

## SAP Procurement/Fuel

Handled:

* fuel quantities
* procurement categories
* direct combustion examples

Ignored:

* highly nested SAP schemas
* SAP API integrations
* complex ERP joins

---

## Utility Consumption

Handled:

* electricity usage
* kWh normalization
* purchased energy mapping

Ignored:

* OCR bill parsing
* interval smart-meter datasets

---

## Corporate Travel

Handled:

* mileage-based emissions
* business travel examples

Ignored:

* airline-class emissions factors
* hotel emissions
* real-time travel APIs

---

# Ambiguities Resolved

## Missing Emission Factors

Simplified emission factors were used for prototype consistency.

In production:

* region-specific factors
* EPA datasets
* supplier-specific coefficients
  would be required.

---

# Questions for PM

If product discussions were available, I would ask:

* expected tenant scale
* required compliance standards
* regional emissions factor requirements
* expected ERP integrations
* approval workflow complexity
* retention requirements for audit logs
