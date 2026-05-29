"""
Validation engine for ESG data quality.

Rule-based validators that check:
- Data completeness
- Format consistency
- Business logic
- Suspicious anomalies

Validators are modular and can be extended for domain-specific rules.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import re


class ValidationResult:
    """Holds validation check results."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def add_error(self, message):
        """Add a validation error."""
        self.errors.append(message)
    
    def add_warning(self, message):
        """Add a validation warning."""
        self.warnings.append(message)
    
    def status(self):
        """Return validation status based on errors/warnings."""
        if self.errors:
            return 'error'
        elif self.warnings:
            return 'warning'
        return 'valid'
    
    def all_messages(self):
        """Return all messages for storage."""
        return self.errors + self.warnings


class SAPValidator:
    """Validates normalized SAP procurement/fuel data."""
    
    VALID_UNITS = ['liters', 'cubic_meters', 'kg', 'kwh']
    VALID_SCOPES = ['scope_1', 'scope_2']
    
    @classmethod
    def validate(cls, record):
        """
        Validate a normalized SAP emission record.
        
        Args:
            record: EmissionRecord instance
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Check quantity is positive
        if record.activity_value <= 0:
            result.add_error(f"Activity value must be positive (got {record.activity_value})")
        
        # Check quantity is reasonable
        if record.activity_value > Decimal('1000000'):
            result.add_warning(f"Very large quantity: {record.activity_value} {record.activity_unit}")
        
        # Check date is recent
        days_old = (datetime.now().date() - record.activity_date).days
        if days_old > 730:  # 2 years
            result.add_warning(f"Data is {days_old} days old")
        
        # Check date is not in future
        if record.activity_date > datetime.now().date():
            result.add_error(f"Activity date is in the future: {record.activity_date}")
        
        # Validate unit
        if record.activity_unit not in cls.VALID_UNITS:
            result.add_error(f"Unknown unit: {record.activity_unit}")
        
        # SAP data should typically be Scope 1 or 2
        if record.scope not in cls.VALID_SCOPES:
            result.add_warning(f"Unusual scope for SAP data: {record.scope}")
        
        return result


class UtilityValidator:
    """Validates utility consumption data."""
    
    @classmethod
    def validate(cls, record):
        """Validate electricity/utility consumption record."""
        result = ValidationResult()
        
        # Electricity usage must be positive
        if record.activity_value <= 0:
            result.add_error(f"Consumption must be positive (got {record.activity_value})")
        
        # Check for abnormal spikes
        if record.activity_value > Decimal('1000000'):  # 1M kWh is huge
            result.add_warning(f"Extremely high consumption: {record.activity_value} kWh")
        
        # Check date
        days_old = (datetime.now().date() - record.activity_date).days
        if days_old > 365:
            result.add_warning(f"Utility data is {days_old} days old")
        
        if record.activity_date > datetime.now().date():
            result.add_error("Activity date cannot be in future")
        
        # Utility should be Scope 2
        if record.scope != 'scope_2':
            result.add_warning(f"Unusual scope for utility data: {record.scope}")
        
        return result


class TravelValidator:
    """Validates corporate travel data."""
    
    AIRPORT_CODE_PATTERN = re.compile(r'^[A-Z]{3}$')
    
    @classmethod
    def validate(cls, record):
        """Validate travel record."""
        result = ValidationResult()
        
        # Distance must be positive
        if record.activity_value <= 0:
            result.add_error(f"Distance must be positive (got {record.activity_value})")
        
        # Flight distances are typically < 20,000 km
        if record.activity_value > Decimal('20000'):
            result.add_warning(f"Very long distance: {record.activity_value} km")
        
        # Check date
        if record.activity_date > datetime.now().date():
            result.add_error("Travel date cannot be in future")
        
        # Travel should be Scope 3
        if record.scope != 'scope_3':
            result.add_warning(f"Unusual scope for travel: {record.scope}")
        
        # Validate category format if it contains airport codes
        if 'airport_code' in record.category and not cls._validate_airport_codes(record.category):
            result.add_warning(f"Invalid airport code format in: {record.category}")
        
        return result
    
    @classmethod
    def _validate_airport_codes(cls, category):
        """Check if airport codes in category follow standard format."""
        # Simple check - just pattern matching
        codes = re.findall(r'[A-Z]{3}', category)
        return len(codes) >= 1


def validate_record(record):
    """
    Dispatch validation based on source type.
    
    Args:
        record: EmissionRecord instance
        
    Returns:
        ValidationResult
    """
    validators = {
        'sap': SAPValidator,
        'utility': UtilityValidator,
        'travel': TravelValidator,
    }
    
    validator_class = validators.get(record.source_type)
    if validator_class:
        return validator_class.validate(record)
    
    # Default: no validation
    return ValidationResult()