"""
SAP procurement/fuel data normalizer.

Handles messy SAP exports with:
- German column headers
- Multiple unit formats
- Inconsistent date formats
- Plant code mappings

SAP exports are typically CSV flat files from materials management (MM) module.
"""

from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SAPNormalizer:
    """
    Converts messy SAP procurement data to normalized EmissionRecord format.
    
    SAP exports are notoriously inconsistent. This normalizer handles:
    - Column name variation (German/English)
    - Unit conversion (l, L, ltr, liters)
    - Date parsing (DD.MM.YYYY vs YYYY-MM-DD)
    - Plant code standardization
    """
    
    # Column name mappings for different SAP export versions
    COLUMN_MAPPINGS = {
        'quantity': [
            'Menge', 'menge', 'quantity', 'Quantity',
            'QTY', 'qty', 'amount', 'Amount'
        ],
        'unit': [
            'Einheit', 'einheit', 'unit', 'Unit',
            'UOM', 'uom', 'Unit of Measure'
        ],
        'date': [
            'Datum', 'datum', 'date', 'Date',
            'Posting Date', 'posting_date', 'Buchungsdatum'
        ],
        'plant': [
            'Werk', 'werk', 'plant', 'Plant',
            'Plant Code', 'plant_code', 'Location'
        ],
        'material': [
            'Material', 'material', 'Material Number',
            'material_number', 'Materialnummer'
        ],
        'material_desc': [
            'Description', 'description', 'Material Description',
            'Beschreibung', 'beschreibung'
        ],
        'value': [
            'Wert', 'wert', 'value', 'Value',
            'Amount', 'Betrag', 'betrag'
        ],
    }
    
    # Material description to fuel type mappings
    FUEL_MAPPINGS = {
        'diesel': 'diesel_fuel',
        'petrol': 'petrol_fuel',
        'gasoline': 'petrol_fuel',
        'naturgas': 'natural_gas',
        'natural gas': 'natural_gas',
        'erdgas': 'natural_gas',
        'lng': 'liquefied_natural_gas',
        'lpg': 'lpg_fuel',
        'kohle': 'coal',
        'coal': 'coal',
        'heizöl': 'heating_oil',
        'heating oil': 'heating_oil',
    }
    
    # Unit conversions to standardized units
    UNIT_CONVERSIONS = {
        'liters': ('liters', Decimal('1')),
        'l': ('liters', Decimal('1')),
        'liter': ('liters', Decimal('1')),
        'ltr': ('liters', Decimal('1')),
        'cubic_meters': ('cubic_meters', Decimal('1')),
        'm3': ('cubic_meters', Decimal('1')),
        'cbm': ('cubic_meters', Decimal('1')),
        'kg': ('kg', Decimal('1')),
        'kilograms': ('kg', Decimal('1')),
        'kwh': ('kwh', Decimal('1')),
        'mj': ('mj', Decimal('1')),
        'gj': ('gj', Decimal('1000')),  # Convert GJ to MJ
    }
    
    # Plant code to location mapping
    PLANT_CODES = {
        '1000': 'Berlin',
        '2000': 'Munich',
        '3000': 'Frankfurt',
        '4000': 'Hamburg',
        '5000': 'Cologne',
    }
    
    @classmethod
    def normalize(cls, raw_record, organization, data_source):
        """
        Convert a raw SAP record to normalized EmissionRecord data.
        
        Args:
            raw_record: RawRecord instance with raw_json data
            organization: Organization instance
            data_source: DataSource instance
            
        Returns:
            dict with normalized fields, or None if normalization fails
        """
        try:
            row_data = raw_record.raw_json
            
            # Extract fields with flexible column name matching
            quantity = cls._extract_field(row_data, 'quantity')
            unit = cls._extract_field(row_data, 'unit')
            date_str = cls._extract_field(row_data, 'date')
            material_desc = cls._extract_field(row_data, 'material_desc', '')
            
            if not all([quantity, unit, date_str]):
                return None  # Can't normalize without key fields
            
            # Parse and validate quantity
            try:
                activity_value = Decimal(str(quantity).replace(',', '.'))
            except:
                return None
            
            if activity_value <= 0:
                return None
            
            # Normalize unit and apply conversion
            normalized_unit, unit_multiplier = cls._normalize_unit(unit)
            if not normalized_unit:
                return None
            
            activity_value = activity_value * unit_multiplier
            
            # Parse date
            activity_date = cls._parse_date(date_str)
            if not activity_date:
                return None
            
            # Infer category from material description
            category = cls._infer_category(material_desc)
            if not category:
                category = 'other_fuel'
            
            # Determine scope (SAP fuel data is Scope 1)
            scope = 'scope_1'
            
            # Determine emission factor
            emission_factor = cls._get_emission_factor(category, normalized_unit)
            
            # Calculate CO2e
            co2e_kg = activity_value * emission_factor
            
            return {
                'organization': organization,
                'raw_record': raw_record,
                'source_type': 'sap',
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
            logger.error(f"SAP normalization failed: {e}")
            return None
    
    @classmethod
    def _extract_field(cls, row_data, field_type, default=None):
        """Extract a field value using flexible column name matching."""
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
        """
        Convert unit string to normalized unit and multiplier.
        
        Returns:
            (normalized_unit, multiplier) or (None, 1) if unknown
        """
        if not unit_str:
            return None, Decimal('1')
        
        unit_lower = str(unit_str).lower().strip()
        
        for key, (normalized, multiplier) in cls.UNIT_CONVERSIONS.items():
            if unit_lower == key.lower():
                return normalized, multiplier
        
        return None, Decimal('1')
    
    @classmethod
    def _parse_date(cls, date_str):
        """
        Parse various date formats from SAP exports.
        
        Handles: DD.MM.YYYY, YYYY-MM-DD, DD/MM/YYYY
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        formats = [
            '%d.%m.%Y',      # German format
            '%Y-%m-%d',      # ISO format
            '%d/%m/%Y',      # UK format
            '%m/%d/%Y',      # US format
            '%d.%m.%y',      # German 2-digit year
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    @classmethod
    def _infer_category(cls, material_desc):
        """Infer fuel category from material description."""
        if not material_desc:
            return None
        
        desc_lower = str(material_desc).lower()
        
        for keyword, category in cls.FUEL_MAPPINGS.items():
            if keyword in desc_lower:
                return category
        
        return None
    
    @classmethod
    def _get_emission_factor(cls, category, unit):
        """Get emission factor for category and unit."""
        from django.conf import settings
        
        factors = settings.EMISSIONS_CALCULATION_FACTORS
        
        # Map categories to factor keys
        category_factors = {
            'diesel_fuel': 'diesel_co2_per_liter',
            'petrol_fuel': 'diesel_co2_per_liter',  # Similar to diesel
            'natural_gas': 'natural_gas_co2_per_m3',
            'liquefied_natural_gas': 'natural_gas_co2_per_m3',
            'lpg_fuel': 'diesel_co2_per_liter',
            'heating_oil': 'diesel_co2_per_liter',
            'other_fuel': 'diesel_co2_per_liter',
        }
        
        factor_key = category_factors.get(category)
        if factor_key:
            return Decimal(str(factors.get(factor_key, 2.5)))
        
        return Decimal('2.5')  # Default