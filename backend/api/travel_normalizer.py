"""
Corporate travel data normalizer.

Handles exports from:
- Concur
- Navan
- Other travel management platforms

Common issues:
- Missing flight distances
- Incomplete airport codes
- Various travel categories
- Currency conversions
"""

from decimal import Decimal
from datetime import datetime
import logging
import math

logger = logging.getLogger(__name__)


class TravelNormalizer:
    """
    Converts corporate travel data to normalized EmissionRecord format.
    
    Handles:
    - Flight distance inference from airport pairs
    - Multiple travel categories
    - Date parsing
    - Incomplete expense data
    """
    
    COLUMN_MAPPINGS = {
        'travel_type': [
            'travel_type', 'Travel Type', 'type', 'Type',
            'Reiseart', 'reiseart', 'Category', 'category'
        ],
        'origin': [
            'origin', 'Origin', 'from', 'From',
            'from_airport', 'departure_airport', 'Abflughafen'
        ],
        'destination': [
            'destination', 'Destination', 'to', 'To',
            'to_airport', 'arrival_airport', 'Ankunftshafen'
        ],
        'distance': [
            'distance', 'Distance', 'km', 'kilometers',
            'Distanz', 'distanz', 'distance_km'
        ],
        'date': [
            'date', 'Date', 'travel_date', 'Travel Date',
            'Reisedatum', 'reisedatum'
        ],
        'traveler': [
            'traveler', 'Traveler', 'employee', 'Employee',
            'person', 'Reisender'
        ],
        'cost': [
            'cost', 'Cost', 'amount', 'Amount',
            'Kosten', 'kosten', 'price'
        ],
    }
    
    # Common airport codes to great-circle distances (km)
    # Simplified sample - production would use haversine formula
    AIRPORT_DISTANCES = {
        'BER-MUC': 620,    # Berlin - Munich
        'BER-FRA': 540,    # Berlin - Frankfurt
        'BER-CDG': 880,    # Berlin - Paris
        'BER-LHR': 930,    # Berlin - London
        'MUC-FRA': 350,    # Munich - Frankfurt
        'FRA-CDG': 550,    # Frankfurt - Paris
        'FRA-LHR': 550,    # Frankfurt - London
        'CDG-LHR': 330,    # Paris - London
    }
    
    # Travel categories to scopes/subcategories
    TRAVEL_CATEGORIES = {
        'flight': 'flight_travel',
        'flights': 'flight_travel',
        'air': 'flight_travel',
        'flying': 'flight_travel',
        'hotel': 'hotel_accommodation',
        'hotels': 'hotel_accommodation',
        'accommodation': 'hotel_accommodation',
        'car': 'ground_transport',
        'ground': 'ground_transport',
        'taxi': 'ground_transport',
        'train': 'rail_transport',
        'rail': 'rail_transport',
        'bus': 'bus_transport',
    }
    
    @classmethod
    def normalize(cls, raw_record, organization, data_source):
        """
        Convert raw travel data to normalized EmissionRecord.
        
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
            travel_type = cls._extract_field(row_data, 'travel_type', 'unknown')
            origin = cls._extract_field(row_data, 'origin', '')
            destination = cls._extract_field(row_data, 'destination', '')
            distance = cls._extract_field(row_data, 'distance')
            date_str = cls._extract_field(row_data, 'date')
            
            if not date_str:
                return None
            
            # Parse travel date
            activity_date = cls._parse_date(date_str)
            if not activity_date:
                return None
            
            # Infer category
            category = cls._infer_category(travel_type)
            if not category:
                return None
            
            # Handle different travel categories
            if category == 'flight_travel':
                return cls._normalize_flight(
                    raw_record, organization, activity_date, origin, destination, distance
                )
            elif category == 'hotel_accommodation':
                return cls._normalize_hotel(
                    raw_record, organization, activity_date
                )
            elif category in ['ground_transport', 'rail_transport', 'bus_transport']:
                return cls._normalize_ground_transport(
                    raw_record, organization, activity_date, distance, category
                )
            else:
                return None
                
        except Exception as e:
            logger.error(f"Travel normalization failed: {e}")
            return None
    
    @classmethod
    def _normalize_flight(cls, raw_record, organization, activity_date, origin, destination, distance):
        """Normalize flight data."""
        if not origin or not destination:
            return None
        
        # Try to get distance
        distance_km = cls._infer_distance(origin, destination, distance)
        if not distance_km or distance_km <= 0:
            return None
        
        activity_value = Decimal(str(distance_km))
        
        # Get emission factor
        emission_factor = Decimal(
            str(organization.emission_calculation_factors.get(
                'flight_co2_per_km', 0.255
            ))
        )
        
        co2e_kg = activity_value * emission_factor
        
        return {
            'organization': organization,
            'raw_record': raw_record,
            'source_type': 'travel',
            'scope': 'scope_3',
            'category': 'flight_travel',
            'activity_date': activity_date,
            'activity_value': activity_value,
            'activity_unit': 'km',
            'normalized_unit': 'km',
            'co2e_kg': co2e_kg,
            'emission_factor_used': emission_factor,
        }
    
    @classmethod
    def _normalize_hotel(cls, raw_record, organization, activity_date):
        """Normalize hotel/accommodation data (nights)."""
        # For hotel data, we'd expect a 'nights' field
        # Simplification: count as 1 night per record
        nights = 1
        activity_value = Decimal(str(nights))
        
        emission_factor = Decimal('25.0')  # kg CO2e per night
        co2e_kg = activity_value * emission_factor
        
        return {
            'organization': organization,
            'raw_record': raw_record,
            'source_type': 'travel',
            'scope': 'scope_3',
            'category': 'hotel_accommodation',
            'activity_date': activity_date,
            'activity_value': activity_value,
            'activity_unit': 'nights',
            'normalized_unit': 'nights',
            'co2e_kg': co2e_kg,
            'emission_factor_used': emission_factor,
        }
    
    @classmethod
    def _normalize_ground_transport(cls, raw_record, organization, activity_date, distance, category):
        """Normalize ground transport (car, taxi, train, bus)."""
        distance_km = cls._parse_numeric(distance)
        if not distance_km or distance_km <= 0:
            return None
        
        activity_value = Decimal(str(distance_km))
        
        # Emission factors by transport type
        factors = {
            'ground_transport': Decimal('0.12'),  # kg CO2e per km (car)
            'rail_transport': Decimal('0.04'),    # kg CO2e per km (train)
            'bus_transport': Decimal('0.08'),     # kg CO2e per km (bus)
        }
        
        emission_factor = factors.get(category, Decimal('0.12'))
        co2e_kg = activity_value * emission_factor
        
        return {
            'organization': organization,
            'raw_record': raw_record,
            'source_type': 'travel',
            'scope': 'scope_3',
            'category': category,
            'activity_date': activity_date,
            'activity_value': activity_value,
            'activity_unit': 'km',
            'normalized_unit': 'km',
            'co2e_kg': co2e_kg,
            'emission_factor_used': emission_factor,
        }
    
    @classmethod
    def _infer_category(cls, travel_type):
        """Infer normalized category from travel type string."""
        if not travel_type:
            return None
        
        travel_lower = str(travel_type).lower()
        
        for keyword, category in cls.TRAVEL_CATEGORIES.items():
            if keyword in travel_lower:
                return category
        
        return None
    
    @classmethod
    def _infer_distance(cls, origin, destination, distance_str):
        """
        Infer distance between airports.
        
        If distance is provided, use it.
        Otherwise, estimate from airport pair.
        """
        # If distance is provided, use it
        if distance_str:
            distance = cls._parse_numeric(distance_str)
            if distance and distance > 0:
                return distance
        
        # Try to infer from airport codes
        if origin and destination:
            origin = str(origin).upper().strip()
            destination = str(destination).upper().strip()
            
            # Normalize to 3-letter codes if needed
            origin = origin[:3] if len(origin) >= 3 else None
            destination = destination[:3] if len(destination) >= 3 else None
            
            if origin and destination:
                # Check both directions
                key_forward = f"{origin}-{destination}"
                key_reverse = f"{destination}-{origin}"
                
                if key_forward in cls.AIRPORT_DISTANCES:
                    return cls.AIRPORT_DISTANCES[key_forward]
                elif key_reverse in cls.AIRPORT_DISTANCES:
                    return cls.AIRPORT_DISTANCES[key_reverse]
                else:
                    # Estimate using great-circle distance (simplified)
                    return cls._estimate_distance(origin, destination)
        
        return None
    
    @classmethod
    def _estimate_distance(cls, airport1, airport2):
        """Rough estimation of distance between airports."""
        # This is a placeholder - production would use real coordinate data
        # For now, return None to indicate unknown distance
        logger.warning(f"Could not estimate distance between {airport1} and {airport2}")
        return None
    
    @classmethod
    def _parse_numeric(cls, value):
        """Parse numeric value from string."""
        if value is None:
            return None
        
        try:
            return Decimal(str(value).replace(',', '.'))
        except:
            return None
    
    @classmethod
    def _parse_date(cls, date_str):
        """Parse date string."""
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
    def _extract_field(cls, row_data, field_type, default=None):
        """Extract field with flexible column name matching."""
        if not isinstance(row_data, dict):
            return default
        
        possible_names = cls.COLUMN_MAPPINGS.get(field_type, [])
        
        for key in row_data.keys():
            if any(key.lower() == name.lower() for name in possible_names):
                value = row_data[key]
                if value is not None and str(value).strip():
                    return str(value).strip()
        
        return default