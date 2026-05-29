"""
ESG Analytics Platform — Data Models
"""

from django.db import models
from django.utils import timezone


class EmissionSource(models.Model):
    """Master list of emission sources / facilities."""

    SOURCE_TYPES = [
        ("electricity", "Electricity"),
        ("natural_gas", "Natural Gas"),
        ("fleet", "Fleet / Vehicle"),
        ("air_travel", "Air Travel"),
        ("rail_travel", "Rail Travel"),
        ("hotel", "Hotel Stay"),
        ("waste", "Waste"),
        ("water", "Water"),
        ("refrigerant", "Refrigerant"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    location = models.CharField(max_length=255, blank=True, default="")
    department = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.source_type})"


class EmissionRecord(models.Model):
    """Individual emission record after CSV ingestion & normalisation."""

    SCOPE_CHOICES = [
        ("scope1", "Scope 1 — Direct"),
        ("scope2", "Scope 2 — Indirect (Energy)"),
        ("scope3", "Scope 3 — Value Chain"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("flagged", "Flagged"),
    ]

    SOURCE_TYPES = [
        ("sap", "SAP Export"),
        ("utility", "Utility Bill"),
        ("travel", "Travel / Expense"),
        ("manual", "Manual Entry"),
    ]

    # Core data
    source = models.ForeignKey(
        EmissionSource, null=True, blank=True, on_delete=models.SET_NULL
    )
    data_source_type = models.CharField(
        max_length=20, choices=SOURCE_TYPES, default="manual"
    )
    description = models.CharField(max_length=500, blank=True, default="")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Quantities
    quantity = models.FloatField(default=0.0)
    unit = models.CharField(max_length=50, blank=True, default="")
    emission_factor = models.FloatField(default=0.0)
    co2e_tonnes = models.FloatField(default=0.0)

    # Classification
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default="scope3")
    category = models.CharField(max_length=255, blank=True, default="")
    department = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")

    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    validation_warnings = models.JSONField(default=list, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")

    # Timestamps
    upload_batch = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.scope} | {self.co2e_tonnes:.4f} tCO₂e | {self.status}"


class AuditLog(models.Model):
    """Immutable audit trail for every workflow action."""

    ACTION_CHOICES = [
        ("upload", "CSV Upload"),
        ("create", "Record Created"),
        ("approve", "Record Approved"),
        ("reject", "Record Rejected"),
        ("flag", "Record Flagged"),
        ("edit", "Record Edited"),
        ("delete", "Record Deleted"),
        ("bulk_approve", "Bulk Approve"),
        ("bulk_reject", "Bulk Reject"),
    ]

    record = models.ForeignKey(
        EmissionRecord, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    actor = models.CharField(max_length=255, default="system")
    detail = models.TextField(blank=True, default="")
    previous_status = models.CharField(max_length=20, blank=True, default="")
    new_status = models.CharField(max_length=20, blank=True, default="")
    batch_id = models.CharField(max_length=100, blank=True, default="")
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} — {self.actor} @ {self.timestamp:%Y-%m-%d %H:%M}"