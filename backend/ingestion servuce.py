"""
Main ingestion service orchestrating the entire data pipeline.

Flow:
1. Save raw uploaded file
2. Parse CSV and create RawRecord entries
3. Normalize to EmissionRecord using source-specific normalizers
4. Validate using rule-based validators
5. Mark as ready for analyst review

This service handles both happy path and error cases,
maintaining complete auditability.
"""

import csv
import io
from decimal import Decimal
import logging

from django.utils import timezone
from django.db import transaction

from backend.api.validators import validate_record
from sap_normalizer import SAPNormalizer
from utility_normalizer import UtilityNormalizer
from travel_normalizer import TravelNormalizer

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates the complete data ingestion pipeline."""
    
    NORMALIZERS = {
        'sap': SAPNormalizer,
        'utility': UtilityNormalizer,
        'travel': TravelNormalizer,
    }
    
    @classmethod
    @transaction.atomic
    def ingest_file(cls, data_source, file_content):
        """
        Ingest an uploaded CSV file.
        
        Creates:
        - RawRecord entries (immutable)
        - EmissionRecord entries (normalized)
        - Validation results
        
        Args:
            data_source: DataSource instance
            file_content: bytes or string content
            
        Returns:
            dict with ingestion summary
        """
        try:
            # Parse CSV
            rows = cls._parse_csv(file_content)
            raw_records = []
            emission_records = []
            errors = []
            
            for row_number, row_data in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
                try:
                    # Create RawRecord
                    raw_record = cls._create_raw_record(data_source, row_number, row_data)
                    raw_records.append(raw_record)
                    
                    # Normalize to EmissionRecord
                    normalized_data = cls._normalize_record(raw_record, data_source)
                    
                    if normalized_data:
                        emission_record = cls._create_emission_record(normalized_data)
                        emission_records.append(emission_record)
                        raw_record.ingestion_status = 'parsed'
                        raw_record.save()
                    else:
                        raw_record.ingestion_status = 'error'
                        raw_record.error_message = 'Could not normalize to emission data'
                        raw_record.save()
                        errors.append((row_number, 'Normalization failed'))
                
                except Exception as e:
                    logger.error(f"Error processing row {row_number}: {e}")
                    errors.append((row_number, str(e)))
            
            # Update data source
            data_source.raw_record_count = len(raw_records)
            data_source.emission_record_count = len(emission_records)
            data_source.ingestion_status = 'completed'
            data_source.processed_at = timezone.now()
            
            if errors:
                data_source.error_message = f"{len(errors)} rows had errors"
            
            data_source.save()
            
            return {
                'success': True,
                'raw_records_created': len(raw_records),
                'emission_records_created': len(emission_records),
                'errors': errors,
            }
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            data_source.ingestion_status = 'failed'
            data_source.error_message = str(e)
            data_source.save()
            
            return {
                'success': False,
                'error': str(e),
            }
    
    @classmethod
    def _parse_csv(cls, file_content):
        """
        Parse CSV file content.
        
        Args:
            file_content: bytes or string
            
        Returns:
            list of dicts
        """
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8-sig')
        
        # Use StringIO for in-memory file object
        file_obj = io.StringIO(file_content)
        
        # Try to detect format
        sample = file_content[:1024]
        has_header = csv.Sniffer().has_header(sample)
        
        reader = csv.DictReader(file_obj) if has_header else csv.DictReader(file_obj)
        
        rows = []
        for row in reader:
            rows.append(row)
        
        return rows
    
    @classmethod
    def _create_raw_record(cls, data_source, row_number, row_data):
        """Create RawRecord entry."""
        from ingestion.models import RawRecord
        
        raw_record = RawRecord(
            data_source=data_source,
            row_number=row_number,
            raw_json=row_data,
            ingestion_status='raw',
        )
        raw_record.save()
        return raw_record
    
    @classmethod
    def _normalize_record(cls, raw_record, data_source):
        """Normalize using appropriate normalizer."""
        normalizer = cls.NORMALIZERS.get(data_source.source_type)
        
        if not normalizer:
            return None
        
        return normalizer.normalize(raw_record, data_source.organization, data_source)
    
    @classmethod
    def _create_emission_record(cls, normalized_data):
        """Create and validate EmissionRecord."""
        from emissions.models import EmissionRecord
        
        emission_record = EmissionRecord(**normalized_data)
        
        # Run validation
        validation_result = validate_record(emission_record)
        
        emission_record.validation_status = validation_result.status()
        emission_record.validation_issues = validation_result.all_messages()
        
        emission_record.save()
        return emission_record


class ApprovalService:
    """Handles analyst approval workflow."""
    
    @classmethod
    @transaction.atomic
    def approve_record(cls, emission_record, user):
        """
        Approve a single record and lock it.
        
        Args:
            emission_record: EmissionRecord instance
            user: User who is approving
        """
        from audit.models import AuditLog
        
        if not emission_record.can_approve():
            raise ValueError("Record cannot be approved in current state")
        
        emission_record.approve(user)
        
        # Log approval
        AuditLog.objects.create(
            emission_record=emission_record,
            action='approved',
            changed_by=user,
            reason='Analyst approved record'
        )
    
    @classmethod
    @transaction.atomic
    def reject_record(cls, emission_record, reason=''):
        """
        Reject a record.
        
        Args:
            emission_record: EmissionRecord instance
            reason: Reason for rejection
        """
        from audit.models import AuditLog
        
        emission_record.reject()
        
        # Log rejection
        AuditLog.objects.create(
            emission_record=emission_record,
            action='rejected',
            reason=reason
        )
    
    @classmethod
    @transaction.atomic
    def edit_record(cls, emission_record, changes, user):
        """
        Edit a record (only if not locked).
        
        Args:
            emission_record: EmissionRecord instance
            changes: dict of field_name -> new_value
            user: User making the edit
        """
        from audit.models import AuditLog
        
        if emission_record.is_locked:
            raise ValueError("Cannot edit locked record")
        
        for field_name, new_value in changes.items():
            if not hasattr(emission_record, field_name):
                continue
            
            old_value = getattr(emission_record, field_name)
            
            if old_value != new_value:
                setattr(emission_record, field_name, new_value)
                
                # Log the change
                AuditLog.objects.create(
                    emission_record=emission_record,
                    action='edited',
                    field_name=field_name,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    changed_by=user,
                )
        
        emission_record.save()