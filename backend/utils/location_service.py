"""
Location Service Utility
Handles geocoding, reverse geocoding, and distance calculations
"""

import math
import re
import logging
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class LocationService:
    def __init__(self, google_maps_api_key: Optional[str] = None):
        self.google_maps_api_key = google_maps_api_key
        self.geocoding_base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in miles
        """
        try:
            # Convert to radians
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # Haversine formula
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth's radius in miles
            radius = 3959
            
            distance = radius * c
            return round(distance, 2)
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return 0.0
    
    def geocode_address(self, address: str) -> Optional[Tuple[Decimal, Decimal]]:
        """
        Convert address to coordinates using Google Maps Geocoding API
        Returns (latitude, longitude) or None
        """
        if not self.google_maps_api_key:
            logger.warning("Google Maps API key not configured, skipping geocoding")
            return None
        
        try:
            params = {
                'address': address,
                'key': self.google_maps_api_key
            }
            
            response = requests.get(self.geocoding_base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                lat = Decimal(str(location['lat']))
                lng = Decimal(str(location['lng']))
                return (lat, lng)
            else:
                logger.warning(f"Geocoding failed for address '{address}': {data.get('status')}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error calling Google Maps API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in geocoding: {e}")
            return None
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Convert coordinates to address using Google Maps Reverse Geocoding API
        Returns formatted address or None
        """
        if not self.google_maps_api_key:
            logger.warning("Google Maps API key not configured, skipping reverse geocoding")
            return None
        
        try:
            params = {
                'latlng': f"{lat},{lng}",
                'key': self.google_maps_api_key
            }
            
            response = requests.get(self.geocoding_base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                return data['results'][0]['formatted_address']
            else:
                logger.warning(f"Reverse geocoding failed for coordinates ({lat}, {lng}): {data.get('status')}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error calling Google Maps API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in reverse geocoding: {e}")
            return None
    
    def extract_zip_code(self, address: str) -> Optional[str]:
        """
        Extract ZIP code from address string
        """
        if not address:
            return None
        
        # Common ZIP code patterns
        zip_patterns = [
            r'\b\d{5}\b',  # 5-digit ZIP
            r'\b\d{5}-\d{4}\b',  # ZIP+4
        ]
        
        for pattern in zip_patterns:
            match = re.search(pattern, address)
            if match:
                return match.group()
        
        return None
    
    def validate_coordinates(self, lat: float, lng: float) -> bool:
        """
        Validate coordinate values
        """
        return -90 <= lat <= 90 and -180 <= lng <= 180
    
    def validate_address(self, address: str) -> bool:
        """
        Basic address validation
        """
        if not address or len(address.strip()) < 5:
            return False
        
        # Check for basic address components
        address_lower = address.lower()
        has_number = bool(re.search(r'\d', address))
        has_street = any(word in address_lower for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'drive', 'dr', 'lane', 'ln', 'way', 'court', 'ct'])
        
        return has_number and has_street
    
    def format_phone_number(self, phone: str) -> str:
        """
        Format phone number to standard format
        """
        if not phone:
            return phone
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone
    
    def search_providers_by_location(self, 
                                   providers: list, 
                                   search_lat: float, 
                                   search_lng: float, 
                                   radius_miles: float = 25.0) -> list:
        """
        Filter providers by distance from search location
        """
        if not self.validate_coordinates(search_lat, search_lng):
            raise HTTPException(status_code=400, detail="Invalid search coordinates")
        
        filtered_providers = []
        
        for provider in providers:
            if provider.get('latitude') and provider.get('longitude'):
                try:
                    distance = self.calculate_distance(
                        search_lat, search_lng,
                        float(provider['latitude']), float(provider['longitude'])
                    )
                    
                    if distance <= radius_miles:
                        provider_copy = provider.copy()
                        provider_copy['distance'] = distance
                        filtered_providers.append(provider_copy)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error calculating distance for provider {provider.get('id')}: {e}")
                    continue
        
        # Sort by distance
        filtered_providers.sort(key=lambda x: x.get('distance', float('inf')))
        
        return filtered_providers

# Global instance
location_service = LocationService() 