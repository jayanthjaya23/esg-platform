from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import EmissionRecord, AuditLog

import csv
import io


@api_view(['GET'])
def home(request):

    return Response({
        "message": "ESG Backend Running"
    })


@api_view(['GET'])
def get_emissions(request):

    try:

        records = EmissionRecord.objects.all().order_by('-id')

        data = []

        for r in records:

            data.append({

                "id": r.id,
                "source_type": r.source_type,
                "scope": r.scope,
                "category": r.category,
                "activity_value": r.activity_value,
                "activity_unit": r.activity_unit,
                "co2e_kg": r.co2e_kg,
                "validation_status": r.validation_status,
                "approval_status": r.approval_status,
            })

        return Response(data)

    except Exception as e:

        return Response({

            "error": str(e)

        }, status=500)


@api_view(['POST'])
def upload_file(request):

    try:

        source_type = request.data.get(
            'source_type'
        )

        uploaded_file = request.FILES.get(
            'file'
        )

        if not uploaded_file:

            return Response(
                {"error": "No file uploaded"},
                status=400
            )

        decoded_file = uploaded_file.read().decode(
            'utf-8'
        )

        csv_data = csv.DictReader(
            io.StringIO(decoded_file)
        )

        created = 0

        for row in csv_data:

            if source_type == 'sap':

                scope = 'scope_3'
                category = 'procurement'

                activity_value = 500
                activity_unit = 'kg'

                co2e_kg = 900

                validation = 'warning'

            elif source_type == 'utility':

                scope = 'scope_2'
                category = 'electricity'

                activity_value = 200
                activity_unit = 'kwh'

                co2e_kg = 400

                validation = 'valid'

            else:

                scope = 'scope_3'
                category = 'business_travel'

                activity_value = 1000
                activity_unit = 'km'

                co2e_kg = 700

                validation = 'valid'

            record = EmissionRecord.objects.create(

                source_type=source_type,

                scope=scope,

                category=category,

                activity_value=float(activity_value),

                activity_unit=activity_unit,

                co2e_kg=float(co2e_kg),

                validation_status=validation,

                approval_status='pending'
            )

            AuditLog.objects.create(

                emission_record=record,

                action='created',

                changed_by='system',

                change_summary='CSV uploaded'
            )

            created += 1

        return Response({

            "message": "Upload successful",

            "records_created": created

        })

    except Exception as e:

        print(e)

        return Response({

            "error": str(e)

        }, status=500)


@api_view(['POST'])
def approve_record(request, record_id):

    try:

        record = EmissionRecord.objects.get(
            id=record_id
        )

        record.approval_status = 'approved'

        record.save()

        AuditLog.objects.create(

            emission_record=record,
            action='approved',
            changed_by='analyst',
            change_summary='Record approved'
        )

        return Response({
            "message": "Approved"
        })

    except Exception as e:

        return Response({

            "error": str(e)

        }, status=500)


@api_view(['POST'])
def reject_record(request, record_id):

    try:

        record = EmissionRecord.objects.get(
            id=record_id
        )

        record.approval_status = 'rejected'

        record.save()

        AuditLog.objects.create(

            emission_record=record,
            action='rejected',
            changed_by='analyst',
            change_summary='Record rejected'
        )

        return Response({
            "message": "Rejected"
        })

    except Exception as e:

        return Response({

            "error": str(e)

        }, status=500)


@api_view(['GET'])
def audit_logs(request):

    try:

        logs = AuditLog.objects.all().order_by('-id')

        data = []

        for log in logs:

            data.append({

                "id": log.id,
                "record_id": log.emission_record.id,
                "action": log.action,
                "changed_by": log.changed_by,
                "summary": log.change_summary,
                "timestamp": log.timestamp,
            })

        return Response(data)

    except Exception as e:

        return Response({

            "error": str(e)

        }, status=500)