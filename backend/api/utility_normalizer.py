"""
Utility consumption data normalizer.

Handles electricity/utility exports from:
- Meter portals
- Billing systems
- Building management systems (BMS)

Common issues:
- Billing periods not calendar months
- Multiple meters
- Mixed units (kWh, MWh)
- Missing meter IDs
"""

from decimal import Decimal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class UtilityNormalizer:
    """
    Converts utility consumption data to normalized EmissionRecord format.
    
    Handles:
    - Various meter portal exports
    - Billing period normalization
    - Unit conversion
    - Meter ID tracking
    """
    
    COLUMN_MAPPINGS = {
        'consumption': [
            'consumption', 'Consumption', 'usage', 'Usage',
            'kWh', 'kwh', 'Energy', 'energy',
            'Verbrauch', 'verbrauch', 'Stromverbrauch'
        ],
        'unit': [
            'unit', 'Unit', 'UOM', 'uom',
            'Einheit', 'einheit'
        ],
        'start_date': [
            'start_date', 'Start Date', 'from_date', 'From',
            'Period Start', 'periode_start', 'Startdatum'
        ],
        'end_date': [
            'end_date', 'End Date', 'to_date', 'To',
            'Period End', 'periode_end', 'Enddatum'
        ],
        'meter_id': [
            'meter_id', 'Meter ID', 'Meter Number',
            'meter_number', 'Zählernummer', 'Meter'
        ],
        'facility': [
            'facility', 'Facility', 'location', 'Location',
            'Site', 'site', 'Standort'
        ],
    }
    
    # Unit conversions to kWh
    UNIT_CONVERSIONS = {
        'kwh': ('kwh', Decimal('1')),
        'kWh': ('kwh', Decimal('1')),
        'mwh': ('kwh', Decimal('1000')),
        'MWh': ('kwh', Decimal('1000')),
        'wh': ('kwh', Decimal('0.001')),
        'Wh': ('kwh', Decimal('0.001')),
        'mj': ('kwh', Decimal('0.277778')),  # 1 MJ = 0.277778 kWh
        'MJ': ('kwh', Decimal('0.277778')),
        'gj': ('kwh', Decimal('277.778')),
        'GJ': ('kwh', Decimal('277.778')),
    }
    
    @classmethod
    def normalize(cls, raw_record, organization, data_source):
        """
        Convert raw utility consumption data to normalized EmissionRecord.
        
        Args:
            raw_record: RawRecord instance
            organization: Organization instance
            data_source: DataSource instance
            
        Returns:
            dict with normalized fields or None if normalization fails
        """
        try:
            row_data = raw_record.raw_json
            
            # Extract fields
            consumption = cls._extract_field(row_data, 'consumption')
            unit = cls._extract_field(row_data, 'unit', 'kWh')
            start_date_str = cls._extract_field(row_data, 'start_date')
            end_date_str = cls._extract_field(row_data, 'end_date')
            meter_id = cls._extract_field(row_data, 'meter_id', '')
            
            if not all([consumption, start_date_str, end_date_str]):
                return None
            
            # Parse consumption
            try:
                activity_value = Decimal(str(consumption).replace(',', '.'))
            except:
                return None
            
            if activity_value < 0:  # Allow 0 for zero consumption
                return None
            
            # Normalize unit
            normalized_unit, unit_multiplier = cls._normalize_unit(unit)
            if not normalized_unit:
                return None
            
            activity_value = activity_value * unit_multiplier
            
            # Parse billing period
            start_date = cls._parse_date(start_date_str)
            end_date = cls._parse_date(end_date_str)
            
            if not start_date or not end_date or start_date >= end_date:
                return None
            
            # Check billing period is reasonable (not more than 45 days)
            billing_days = (end_date - start_date).days
            if billing_days > 45:
                logger.warning(f"Unusual billing period: {billing_days} days")
            
            # Use middle of billing period as activity_date
            activity_date = start_date + timedelta(days=billing_days // 2)
            
            # Category is always grid electricity for utility data
            category = 'grid_electricity'
            scope = 'scope_2'
            
            # Get emission factor for electricity
            emission_factor = cls._get_emission_factor(normalized_unit)
            
            # Calculate CO2e
            co2e_kg = activity_value * emission_factor
            
            return {
                'organization': organization,
                'raw_record': raw_record,
                'source_type': 'utility',
                'scope': scope,
                'category': category,
                'activity_date': activity_date,
                'activity_value': activity_value,
                'activity_unit': unit,
                'normalized_unit': normalized_unit,
                'co2e_kg': co2e_kg,
                'emission_factor_used': emission_factor,
            }
            
        except Exception as e:
            logger.error(f"Utility normalization failed: {e}")
            return None
    
    @classmethod
    def _extract_field(cls, row_data, field_type, default=None):
        """Extract field value with flexible column name matching."""
        if not isinstance(row_data, dict):
            return default
        
        possible_names = cls.COLUMN_MAPPINGS.get(field_type, [])
        
        for key in row_data.keys():
            if any(key.lower() == name.lower() for name in possible_names):
                value = row_data[key]
                if value is not None and str(value).strip():
                    return str(value).strip()
        
        return default
    
    @classmethod
    def _normalize_unit(cls, unit_str):
        """Convert unit to standardized kWh."""
        if not unit_str:
            return 'kwh', Decimal('1')
        
        unit_lower = str(unit_str).strip()
        
        for key, (normalized, multiplier) in cls.UNIT_CONVERSIONS.items():
            if unit_lower.lower() == key.lower():
                return normalized, multiplier
        
        # Default to kWh if unknown
        logger.warning(f"Unknown unit: {unit_str}, assuming kWh")
        return 'kwh', Decimal('1')
    
    @classmethod
    def _parse_date(cls, date_str):
        """Parse various date formats."""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        formats = [
            '%d.%m.%Y',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d.%m.%y',
            '%Y/%m/%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    @classmethod
    def _get_emission_factor(cls, normalized_unit):
        """Get electricity emission factor."""
        from django.conf import settings
        
        factors = settings.EMISSIONS_CALCULATION_FACTORS
        
        if normalized_unit == 'kwh':
            return Decimal(str(factors.get('electricity_co2_per_kwh', 0.43)))
        
        # Shouldn't happen if normalization is correct
        return Decimal('0.43')