"""
Audit logging model for regulatory compliance and traceability.

Every edit to an emission record is logged with:
- what changed
- who changed it
- when
- old and new values

This creates an immutable audit trail for ESG reporting.
"""

from django.db import models


class AuditLog(models.Model):
    """
    Immutable record of every change to an EmissionRecord.
    
    Used for:
    - Compliance reporting (trace edits)
    - Dispute resolution (who changed what)
    - Quality assurance (reviewing corrections)
    - Regulatory audits
    """
    
    ACTION_CHOICES = [
        ('created', 'Record created'),
        ('edited', 'Field edited'),
        ('approved', 'Record approved'),
        ('rejected', 'Record rejected'),
        ('validation_updated', 'Validation status changed'),
        ('locked', 'Record locked for audit'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    emission_record = models.ForeignKey(
        'emissions.EmissionRecord',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text="The record this log entry refers to"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Type of change"
    )
    field_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Which field was changed (if applicable)"
    )
    old_value = models.TextField(
        blank=True,
        help_text="Previous value"
    )
    new_value = models.TextField(
        blank=True,
        help_text="New value"
    )
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs_created',
        help_text="User who made the change"
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When change was made"
    )
    reason = models.TextField(
        blank=True,
        help_text="Why this change was made"
    )
    
    class Meta:
        db_table = 'audit_auditlog'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['emission_record', '-changed_at']),
            models.Index(fields=['changed_by', '-changed_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.action} on {self.emission_record} by {self.changed_by}"