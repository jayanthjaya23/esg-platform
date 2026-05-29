from django.urls import path

from .views import *

urlpatterns = [

    path('', home),

    path(
        'emissions/',
        get_emissions
    ),

    path(
        'upload/',
        upload_file
    ),

    path(
        'approve/<int:record_id>/',
        approve_record
    ),

    path(
        'reject/<int:record_id>/',
        reject_record
    ),

    path(
        'audit-logs/',
        audit_logs
    ),
]