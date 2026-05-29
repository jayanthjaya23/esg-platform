# MODEL.md

# ESG Analytics Platform — Data Model Design

## Overview

The platform was designed to support enterprise ESG emissions ingestion workflows across multiple heterogeneous source systems while preserving auditability, traceability, normalization consistency, and analyst review workflows.

The system supports:

* Scope 1 / Scope 2 / Scope 3 classification
* Multi-source ingestion
* Source-of-truth preservation
* Immutable raw ingestion tracking
* Analyst audit workflows
* Unit normalization
* Validation status management
* Multi-tenant extensibility

---

# Core Models

## 1. DataSource

Purpose:
Tracks uploaded source files and ingestion metadata.

Fields:

* id
* source_type
* uploaded_at
* uploaded_by
* original_filename
* ingestion_status
* organization_name

Why:
This model preserves provenance and enables traceability back to the original uploaded source.

It supports:

* ingestion auditing
* upload history
* replayability
* future multi-tenant isolation

---

## 2. RawRecord

Purpose:
Stores immutable source-of-truth payloads before normalization.

Fields:

* id
* datasource_id
* raw_payload
* uploaded_at
* source_row_number

Why:
Enterprise ESG systems must preserve original source records for compliance and audit investigations.

This layer ensures:

* raw evidence retention
* replay capability
* debugging support
* schema drift analysis

---

## 3. EmissionRecord

Purpose:
Stores normalized ESG emission records.

Fields:

* id
* organization_name
* source_type
* scope
* category
* activity_value
* activity_unit
* normalized_unit
* co2e_kg
* validation_status
* approval_status
* created_at
* updated_at

Why:
This represents the analyst-facing ESG dataset after normalization and emissions calculations.

The model supports:

* ESG reporting
* dashboard analytics
* approvals/rejections
* filtering
* visualization

---

# Scope Classification

## Scope 1

Direct emissions:

* fuel combustion
* company-owned sources

## Scope 2

Indirect purchased electricity:

* utility consumption

## Scope 3

Indirect value-chain emissions:

* business travel
* procurement activities

The platform automatically maps source records into scopes using normalization rules.

---

# Unit Normalization

The platform normalizes heterogeneous source units into standardized ESG-compatible units.

Examples:

* liters
* kWh
* miles
* kilograms

Normalization was implemented before emissions calculation to ensure consistency across ingestion sources.

---

# Source-of-Truth Tracking

Each emission record maintains:

* originating source
* upload timestamp
* source file reference
* raw ingestion payload

This enables:

* traceability
* replayability
* analyst trust
* auditability

---

# Audit Trail

Audit logs capture:

* approval actions
* rejection actions
* analyst decisions
* timestamps

Why:
Enterprise ESG platforms require compliance traceability and reviewer accountability.

---

# Multi-Tenancy Considerations

Although the prototype uses a simplified single-tenant architecture, the schema supports future multi-tenancy via:

* organization_name
* datasource ownership
* tenant-level isolation

This design choice minimized prototype complexity while preserving scalability paths.
