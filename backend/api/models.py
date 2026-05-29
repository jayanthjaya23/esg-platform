from django.db import models


class EmissionRecord(models.Model):

    source_type = models.CharField(
        max_length=50
    )

    scope = models.CharField(
        max_length=50
    )

    category = models.CharField(
        max_length=100
    )

    activity_value = models.FloatField()

    activity_unit = models.CharField(
        max_length=50
    )

    co2e_kg = models.FloatField()

    validation_status = models.CharField(
        max_length=50,
        default='valid'
    )

    approval_status = models.CharField(
        max_length=50,
        default='pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.source_type


class AuditLog(models.Model):

    emission_record = models.ForeignKey(
        EmissionRecord,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=100
    )

    changed_by = models.CharField(
        max_length=100
    )

    change_summary = models.TextField()

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.action