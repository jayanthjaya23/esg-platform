"""
ESG Analytics Platform — API URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    # Health
    path("", views.health_check, name="health_check"),

    # Emission Records
    path("emissions/", views.emissions_list, name="emissions_list"),
    path("emissions/<int:pk>/", views.emission_detail, name="emission_detail"),

    # Workflow
    path("approve/<int:pk>/", views.approve_record, name="approve_record"),
    path("reject/<int:pk>/", views.reject_record, name="reject_record"),
    path("bulk-action/", views.bulk_action, name="bulk_action"),

    # Upload
    path("upload/", views.upload_csv, name="upload_csv"),

    # Audit
    path("audit-logs/", views.audit_logs, name="audit_logs"),

    # Sources
    path("sources/", views.emission_sources, name="emission_sources"),

    # Analytics
    path("analytics/", views.analytics_summary, name="analytics_summary"),
]