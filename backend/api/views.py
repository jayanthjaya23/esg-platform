"""
ESG Analytics Platform — API Views
Handles: emissions CRUD, CSV upload & normalisation, approval/rejection workflow,
         audit logs, analytics aggregation, emission sources.
"""

import csv
import io
import uuid
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import EmissionRecord, AuditLog, EmissionSource

logger = logging.getLogger("api")

# ─── Emission Factors (kgCO2e per unit) ─────────────────────────────────────
EMISSION_FACTORS = {
    # Electricity — grid average kg CO2e / kWh
    "electricity_kwh": 0.233,
    "electricity_mwh": 233.0,
    # Natural gas — kg CO2e / m³
    "natural_gas_m3": 1.9,
    "natural_gas_kwh": 0.203,
    # Fleet / fuel — kg CO2e / litre
    "diesel_litre": 2.68,
    "petrol_litre": 2.31,
    "lpg_litre": 1.51,
    # Travel — kg CO2e / km
    "flight_km_economy": 0.255,
    "flight_km_business": 0.430,
    "rail_km": 0.041,
    "taxi_km": 0.149,
    "hotel_night": 31.0,
    # Waste — kg CO2e / tonne
    "waste_landfill_tonne": 467.0,
    "waste_recycled_tonne": 21.0,
    # Water — kg CO2e / m³
    "water_m3": 0.344,
}

SCOPE_MAP = {
    "electricity": "scope2",
    "natural_gas": "scope1",
    "diesel": "scope1",
    "petrol": "scope1",
    "lpg": "scope1",
    "fleet": "scope1",
    "flight": "scope3",
    "rail": "scope3",
    "hotel": "scope3",
    "taxi": "scope3",
    "waste": "scope3",
    "water": "scope3",
    "refrigerant": "scope1",
}


# ─── Normalisation Helpers ───────────────────────────────────────────────────

def _safe_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _safe_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _detect_scope(category: str, description: str) -> str:
    combined = f"{category} {description}".lower()
    for key, scope in SCOPE_MAP.items():
        if key in combined:
            return scope
    return "scope3"


def _build_warnings(record_data: dict) -> list:
    warnings = []
    qty = record_data.get("quantity", 0)
    if qty == 0:
        warnings.append("Quantity is zero — please verify the source data.")
    if qty < 0:
        warnings.append("Negative quantity detected — may indicate a data error.")
    if not record_data.get("period_start"):
        warnings.append("No reporting period start date found.")
    if record_data.get("co2e_tonnes", 0) > 10000:
        warnings.append("Unusually high emission value (>10,000 tCO₂e) — please verify.")
    if not record_data.get("emission_factor"):
        warnings.append("Emission factor not resolved — CO₂e calculation may be inaccurate.")
    return warnings


def normalise_sap_row(row: dict) -> dict:
    """Normalise a SAP expense/purchase-order export row."""
    category = str(row.get("Cost Element Text", row.get("GL Account", ""))).strip()
    quantity = _safe_float(row.get("Quantity", row.get("Amount", 0)))
    unit = str(row.get("Unit", row.get("UOM", "unit"))).strip().lower()
    description = str(row.get("Description", row.get("Short Text", ""))).strip()
    department = str(row.get("Cost Center", row.get("Profit Center", ""))).strip()
    location = str(row.get("Plant", row.get("Location", ""))).strip()
    period_raw = row.get("Posting Date", row.get("Document Date", ""))

    # Resolve emission factor
    factor_key = None
    cat_lower = category.lower()
    if "electric" in cat_lower:
        factor_key = "electricity_kwh" if "kwh" in unit else "electricity_mwh"
    elif "gas" in cat_lower:
        factor_key = "natural_gas_m3" if "m3" in unit or "m³" in unit else "natural_gas_kwh"
    elif "diesel" in cat_lower:
        factor_key = "diesel_litre"
    elif "petrol" in cat_lower or "gasoline" in cat_lower:
        factor_key = "petrol_litre"

    ef = EMISSION_FACTORS.get(factor_key, 0.0)
    co2e = quantity * ef / 1000  # convert kg → tonnes

    return {
        "data_source_type": "sap",
        "description": description or category,
        "quantity": quantity,
        "unit": unit,
        "emission_factor": ef,
        "co2e_tonnes": round(co2e, 6),
        "scope": _detect_scope(category, description),
        "category": category,
        "department": department,
        "location": location,
        "period_start": _safe_date(period_raw),
        "period_end": _safe_date(period_raw),
        "validation_warnings": [],
    }


def normalise_utility_row(row: dict) -> dict:
    """Normalise a utility bill CSV row."""
    utility_type = str(row.get("Utility Type", row.get("Type", "electricity"))).strip().lower()
    quantity = _safe_float(row.get("Consumption", row.get("Usage", row.get("Quantity", 0))))
    unit = str(row.get("Unit", "kWh")).strip().lower()
    period_start = _safe_date(row.get("Period Start", row.get("Bill From", "")))
    period_end = _safe_date(row.get("Period End", row.get("Bill To", "")))
    location = str(row.get("Site", row.get("Location", row.get("Meter ID", "")))).strip()
    description = str(row.get("Description", f"{utility_type.title()} consumption")).strip()

    # Resolve factor
    if "electric" in utility_type:
        factor_key = "electricity_kwh" if unit in ("kwh", "kw-h") else "electricity_mwh"
        scope = "scope2"
    elif "gas" in utility_type:
        factor_key = "natural_gas_m3" if "m3" in unit else "natural_gas_kwh"
        scope = "scope1"
    elif "water" in utility_type:
        factor_key = "water_m3"
        scope = "scope3"
    else:
        factor_key = None
        scope = "scope3"

    ef = EMISSION_FACTORS.get(factor_key, 0.0)
    co2e = quantity * ef / 1000

    return {
        "data_source_type": "utility",
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "emission_factor": ef,
        "co2e_tonnes": round(co2e, 6),
        "scope": scope,
        "category": utility_type.title(),
        "department": str(row.get("Department", row.get("Cost Center", ""))).strip(),
        "location": location,
        "period_start": period_start,
        "period_end": period_end,
        "validation_warnings": [],
    }


def normalise_travel_row(row: dict) -> dict:
    """Normalise an expense / travel booking CSV row."""
    travel_type = str(row.get("Travel Type", row.get("Mode", row.get("Category", "flight")))).strip().lower()
    distance = _safe_float(row.get("Distance KM", row.get("Distance", row.get("Miles", 0))))
    if "miles" in str(row.get("Distance KM", "")).lower() or "miles" in str(row.get("Distance", "")).lower():
        distance *= 1.60934  # convert miles → km
    nights = _safe_float(row.get("Nights", 0))
    cabin_class = str(row.get("Cabin Class", row.get("Class", "economy"))).strip().lower()
    description = str(row.get("Description", row.get("Route", f"{travel_type.title()} travel"))).strip()
    period_raw = row.get("Travel Date", row.get("Date", ""))

    if "flight" in travel_type or "air" in travel_type:
        factor_key = "flight_km_business" if "business" in cabin_class else "flight_km_economy"
        ef = EMISSION_FACTORS.get(factor_key, 0.255)
        qty = distance
        unit = "km"
        scope = "scope3"
        category = "Business Travel — Air"
    elif "rail" in travel_type or "train" in travel_type:
        ef = EMISSION_FACTORS["rail_km"]
        qty = distance
        unit = "km"
        scope = "scope3"
        category = "Business Travel — Rail"
    elif "hotel" in travel_type or "accommodation" in travel_type:
        ef = EMISSION_FACTORS["hotel_night"]
        qty = nights if nights else 1
        unit = "nights"
        scope = "scope3"
        category = "Business Travel — Accommodation"
    elif "taxi" in travel_type or "car" in travel_type or "road" in travel_type:
        ef = EMISSION_FACTORS["taxi_km"]
        qty = distance
        unit = "km"
        scope = "scope3"
        category = "Business Travel — Road"
    else:
        ef = 0.0
        qty = distance
        unit = "km"
        scope = "scope3"
        category = "Business Travel — Other"

    co2e = qty * ef / 1000

    return {
        "data_source_type": "travel",
        "description": description,
        "quantity": round(qty, 2),
        "unit": unit,
        "emission_factor": ef,
        "co2e_tonnes": round(co2e, 6),
        "scope": scope,
        "category": category,
        "department": str(row.get("Cost Center", row.get("Department", ""))).strip(),
        "location": str(row.get("Origin", row.get("From", ""))).strip(),
        "period_start": _safe_date(period_raw),
        "period_end": _safe_date(period_raw),
        "validation_warnings": [],
    }


NORMALISER_MAP = {
    "sap": normalise_sap_row,
    "utility": normalise_utility_row,
    "travel": normalise_travel_row,
}


# ─── Views ───────────────────────────────────────────────────────────────────

@api_view(["GET"])
def health_check(request):
    return Response({"message": "Backend API working", "status": "ok"})


@api_view(["GET", "POST"])
def emissions_list(request):
    """List all emission records or create one manually."""
    if request.method == "GET":
        scope = request.query_params.get("scope")
        status_filter = request.query_params.get("status")
        source_type = request.query_params.get("source_type")
        search = request.query_params.get("search", "")

        qs = EmissionRecord.objects.all()
        if scope:
            qs = qs.filter(scope=scope)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if source_type:
            qs = qs.filter(data_source_type=source_type)
        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(category__icontains=search) |
                Q(department__icontains=search) |
                Q(location__icontains=search)
            )

        records = list(qs.values(
            "id", "data_source_type", "description", "quantity", "unit",
            "emission_factor", "co2e_tonnes", "scope", "category",
            "department", "location", "status", "validation_warnings",
            "rejection_reason", "upload_batch", "period_start", "period_end",
            "created_at", "updated_at",
        ))
        return Response({"count": len(records), "results": records})

    # POST — manual create
    data = request.data
    record = EmissionRecord.objects.create(
        data_source_type=data.get("data_source_type", "manual"),
        description=data.get("description", ""),
        quantity=_safe_float(data.get("quantity", 0)),
        unit=data.get("unit", ""),
        emission_factor=_safe_float(data.get("emission_factor", 0)),
        co2e_tonnes=_safe_float(data.get("co2e_tonnes", 0)),
        scope=data.get("scope", "scope3"),
        category=data.get("category", ""),
        department=data.get("department", ""),
        location=data.get("location", ""),
        period_start=_safe_date(data.get("period_start")),
        period_end=_safe_date(data.get("period_end")),
        status="pending",
    )
    AuditLog.objects.create(
        record=record,
        action="create",
        actor=data.get("actor", "api"),
        detail="Manual record creation via API.",
        new_status="pending",
    )
    return Response({"id": record.id, "status": "created"}, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
def emission_detail(request, pk):
    """Retrieve, update, or delete a single emission record."""
    try:
        record = EmissionRecord.objects.get(pk=pk)
    except EmissionRecord.DoesNotExist:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        data = {
            "id": record.id,
            "data_source_type": record.data_source_type,
            "description": record.description,
            "quantity": record.quantity,
            "unit": record.unit,
            "emission_factor": record.emission_factor,
            "co2e_tonnes": record.co2e_tonnes,
            "scope": record.scope,
            "category": record.category,
            "department": record.department,
            "location": record.location,
            "status": record.status,
            "validation_warnings": record.validation_warnings,
            "rejection_reason": record.rejection_reason,
            "upload_batch": record.upload_batch,
            "period_start": record.period_start,
            "period_end": record.period_end,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
        return Response(data)

    if request.method == "PUT":
        prev = record.status
        for field in ["description", "quantity", "unit", "emission_factor",
                      "co2e_tonnes", "scope", "category", "department", "location"]:
            if field in request.data:
                setattr(record, field, request.data[field])
        record.save()
        AuditLog.objects.create(
            record=record, action="edit", actor=request.data.get("actor", "api"),
            detail="Record updated via API.",
            previous_status=prev, new_status=record.status,
        )
        return Response({"id": record.id, "status": "updated"})

    if request.method == "DELETE":
        AuditLog.objects.create(
            record=record, action="delete", actor="api",
            detail=f"Record {record.id} deleted.",
        )
        record.delete()
        return Response({"status": "deleted"}, status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_csv(request):
    """
    Upload a CSV file for batch ingestion.
    Param: source_type = sap | utility | travel
    """
    file_obj = request.FILES.get("file")
    source_type = request.data.get("source_type", "sap").lower()
    actor = request.data.get("actor", "uploader")

    if not file_obj:
        return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
    if not file_obj.name.lower().endswith(".csv"):
        return Response({"error": "Only CSV files are accepted."}, status=status.HTTP_400_BAD_REQUEST)
    if source_type not in NORMALISER_MAP:
        return Response(
            {"error": f"source_type must be one of: {', '.join(NORMALISER_MAP.keys())}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    normalise = NORMALISER_MAP[source_type]
    batch_id = str(uuid.uuid4())[:8].upper()
    created_ids = []
    skipped = 0
    warning_count = 0

    try:
        content = file_obj.read().decode("utf-8-sig")  # handle BOM
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception as exc:
        logger.error("CSV parse error: %s", exc)
        return Response({"error": f"CSV parse error: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

    if not rows:
        return Response({"error": "CSV file is empty."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        for row in rows:
            try:
                normalised = normalise(row)
                normalised["validation_warnings"] = _build_warnings(normalised)
                if normalised["validation_warnings"]:
                    warning_count += 1
                record = EmissionRecord.objects.create(
                    upload_batch=batch_id,
                    status="pending",
                    **normalised,
                )
                created_ids.append(record.id)
            except Exception as exc:
                logger.warning("Row skipped — %s | row=%s", exc, row)
                skipped += 1

        # Audit the batch upload
        AuditLog.objects.create(
            action="upload",
            actor=actor,
            batch_id=batch_id,
            detail=(
                f"Batch {batch_id}: {len(created_ids)} records ingested "
                f"({skipped} skipped, {warning_count} with warnings) "
                f"from {file_obj.name} [{source_type}]."
            ),
        )

    return Response(
        {
            "batch_id": batch_id,
            "source_type": source_type,
            "total_rows": len(rows),
            "created": len(created_ids),
            "skipped": skipped,
            "warnings": warning_count,
            "record_ids": created_ids,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def approve_record(request, pk):
    """Approve a pending emission record."""
    try:
        record = EmissionRecord.objects.get(pk=pk)
    except EmissionRecord.DoesNotExist:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if record.status == "approved":
        return Response({"message": "Already approved."})

    prev = record.status
    record.status = "approved"
    record.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        record=record,
        action="approve",
        actor=request.data.get("actor", "reviewer"),
        detail=request.data.get("note", "Record approved."),
        previous_status=prev,
        new_status="approved",
    )
    return Response({"id": pk, "status": "approved"})


@api_view(["POST"])
def reject_record(request, pk):
    """Reject a pending emission record with a mandatory reason."""
    try:
        record = EmissionRecord.objects.get(pk=pk)
    except EmissionRecord.DoesNotExist:
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get("reason", "").strip()
    if not reason:
        return Response(
            {"error": "A rejection reason is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prev = record.status
    record.status = "rejected"
    record.rejection_reason = reason
    record.save(update_fields=["status", "rejection_reason", "updated_at"])

    AuditLog.objects.create(
        record=record,
        action="reject",
        actor=request.data.get("actor", "reviewer"),
        detail=reason,
        previous_status=prev,
        new_status="rejected",
    )
    return Response({"id": pk, "status": "rejected", "reason": reason})


@api_view(["POST"])
def bulk_action(request):
    """
    Bulk approve or reject records.
    Body: { "action": "approve"|"reject", "ids": [1,2,3], "reason": "...", "actor": "..." }
    """
    action = request.data.get("action")
    ids = request.data.get("ids", [])
    reason = request.data.get("reason", "Bulk action.")
    actor = request.data.get("actor", "reviewer")

    if action not in ("approve", "reject"):
        return Response({"error": "action must be 'approve' or 'reject'."}, status=400)
    if not ids:
        return Response({"error": "No ids provided."}, status=400)
    if action == "reject" and not reason.strip():
        return Response({"error": "Reason required for bulk reject."}, status=400)

    records = EmissionRecord.objects.filter(id__in=ids)
    updated = 0
    audit_logs = []

    with transaction.atomic():
        for record in records:
            prev = record.status
            record.status = "approved" if action == "approve" else "rejected"
            if action == "reject":
                record.rejection_reason = reason
            record.save(update_fields=["status", "rejection_reason", "updated_at"])
            audit_logs.append(AuditLog(
                record=record,
                action="bulk_approve" if action == "approve" else "bulk_reject",
                actor=actor,
                detail=reason,
                previous_status=prev,
                new_status=record.status,
            ))
            updated += 1
        AuditLog.objects.bulk_create(audit_logs)

    return Response({"updated": updated, "action": action})


@api_view(["GET"])
def audit_logs(request):
    """Return audit log entries with optional filters."""
    record_id = request.query_params.get("record_id")
    action = request.query_params.get("action")
    actor = request.query_params.get("actor")
    limit = int(request.query_params.get("limit", 100))

    qs = AuditLog.objects.all()
    if record_id:
        qs = qs.filter(record_id=record_id)
    if action:
        qs = qs.filter(action=action)
    if actor:
        qs = qs.filter(actor__icontains=actor)

    logs = list(qs[:limit].values(
        "id", "record_id", "action", "actor", "detail",
        "previous_status", "new_status", "batch_id", "timestamp",
    ))
    return Response({"count": len(logs), "results": logs})


@api_view(["GET"])
def emission_sources(request):
    """List all emission sources."""
    sources = list(EmissionSource.objects.filter(is_active=True).values(
        "id", "name", "source_type", "location", "department",
    ))
    return Response({"count": len(sources), "results": sources})


@api_view(["GET"])
def analytics_summary(request):
    """
    Aggregated analytics for the dashboard.
    Returns: totals by scope, by source type, by month, status breakdown, top categories.
    """
    approved_qs = EmissionRecord.objects.filter(status="approved")

    # Totals by scope
    scope_totals = {}
    for row in approved_qs.values("scope").annotate(total=Sum("co2e_tonnes")):
        scope_totals[row["scope"]] = round(row["total"] or 0, 4)

    # Totals by source type
    source_totals = {}
    for row in approved_qs.values("data_source_type").annotate(total=Sum("co2e_tonnes")):
        source_totals[row["data_source_type"]] = round(row["total"] or 0, 4)

    # Monthly trend (last 12 months)
    monthly = []
    for row in (
        approved_qs
        .extra(select={"month": "strftime('%%Y-%%m', period_start)"})
        .values("month")
        .annotate(total=Sum("co2e_tonnes"))
        .order_by("month")[:12]
    ):
        if row["month"]:
            monthly.append({"month": row["month"], "co2e_tonnes": round(row["total"] or 0, 4)})

    # Status breakdown (all records)
    status_counts = {}
    for row in EmissionRecord.objects.values("status").annotate(count=Count("id")):
        status_counts[row["status"]] = row["count"]

    # Top 10 categories by emissions
    top_categories = list(
        approved_qs
        .values("category")
        .annotate(total=Sum("co2e_tonnes"), count=Count("id"))
        .order_by("-total")[:10]
    )
    for item in top_categories:
        item["total"] = round(item["total"] or 0, 4)

    # Top departments
    top_departments = list(
        approved_qs
        .exclude(department="")
        .values("department")
        .annotate(total=Sum("co2e_tonnes"))
        .order_by("-total")[:8]
    )
    for item in top_departments:
        item["total"] = round(item["total"] or 0, 4)

    # Grand total
    grand_total = approved_qs.aggregate(total=Sum("co2e_tonnes"))["total"] or 0

    return Response({
        "grand_total_co2e": round(grand_total, 4),
        "scope_totals": scope_totals,
        "source_totals": source_totals,
        "monthly_trend": monthly,
        "status_breakdown": status_counts,
        "top_categories": top_categories,
        "top_departments": top_departments,
        "total_records": EmissionRecord.objects.count(),
        "pending_review": status_counts.get("pending", 0),
    })