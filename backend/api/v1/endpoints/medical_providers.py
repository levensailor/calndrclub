from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from datetime import datetime
import os
import httpx
import math

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import medical_providers, users
from schemas.medical_provider import (
    MedicalProviderCreate,
    MedicalProviderUpdate,
    MedicalProviderResponse,
    MedicalSearchRequest,
    MedicalSearchResult,
    MedicalSearchResponse
)

router = APIRouter()


@router.get("/", response_model=List[MedicalProviderResponse])
async def get_medical_providers(current_user = Depends(get_current_user)):
    """
    Get all medical providers for the current user's family.
    """
    try:
        query = medical_providers.select().where(medical_providers.c.family_id == current_user['family_id'])
        providers = await database.fetch_all(query)
        
        return [
            MedicalProviderResponse(
                id=provider['id'],
                name=provider['name'],
                specialty=provider['specialty'],
                address=provider['address'],
                phone=provider['phone'],
                email=provider['email'],
                website=provider['website'],
                latitude=float(provider['latitude']) if provider['latitude'] else None,
                longitude=float(provider['longitude']) if provider['longitude'] else None,
                zip_code=provider['zip_code'],
                notes=provider['notes'],
                google_place_id=provider['google_place_id'],
                rating=float(provider['rating']) if provider['rating'] else None,
                family_id=str(provider['family_id']),
                created_by_user_id=str(provider['created_by_user_id']),
                created_at=str(provider['created_at']),
                updated_at=str(provider['updated_at'])
            )
            for provider in providers
        ]
    except Exception as e:
        logger.error(f"Error fetching medical providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch medical providers")

@router.post("/", response_model=MedicalProviderResponse)
async def create_medical_provider(provider_data: MedicalProviderCreate, current_user = Depends(get_current_user)):
    """
    Create a new medical provider for the current user's family.
    """
    try:
        logger.info(f"Creating medical provider: {provider_data.name} for family {current_user['family_id']}")
        # Prepare the insert data
        insert_data = {
            "family_id": current_user['family_id'],
            "created_by_user_id": current_user['id'],
            "name": provider_data.name,
            "specialty": provider_data.specialty,
            "address": provider_data.address,
            "phone": provider_data.phone,
            "email": provider_data.email,
            "website": provider_data.website,
            "latitude": provider_data.latitude,
            "longitude": provider_data.longitude,
            "zip_code": provider_data.zip_code,
            "notes": provider_data.notes,
            "google_place_id": provider_data.google_place_id,
            "rating": provider_data.rating,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Insert the provider
        query = medical_providers.insert().values(**insert_data)
        provider_id = await database.execute(query)
        
        # Fetch the created provider
        created_provider = await database.fetch_one(
            medical_providers.select().where(medical_providers.c.id == provider_id)
        )
        
        return MedicalProviderResponse(
            id=created_provider['id'],
            name=created_provider['name'],
            specialty=created_provider['specialty'],
            address=created_provider['address'],
            phone=created_provider['phone'],
            email=created_provider['email'],
            website=created_provider['website'],
            latitude=float(created_provider['latitude']) if created_provider['latitude'] else None,
            longitude=float(created_provider['longitude']) if created_provider['longitude'] else None,
            zip_code=created_provider['zip_code'],
            notes=created_provider['notes'],
            google_place_id=created_provider['google_place_id'],
            rating=float(created_provider['rating']) if created_provider['rating'] else None,
            family_id=str(created_provider['family_id']),
            created_by_user_id=str(created_provider['created_by_user_id']),
            created_at=str(created_provider['created_at']),
            updated_at=str(created_provider['updated_at'])
        )
    
    except Exception as e:
        logger.error(f"Error creating medical provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to create medical provider")

@router.get("/{provider_id}", response_model=MedicalProviderResponse)
async def get_medical_provider(provider_id: int, current_user = Depends(get_current_user)):
    """
    Get a specific medical provider by ID (must belong to user's family).
    """
    try:
        query = medical_providers.select().where(
            (medical_providers.c.id == provider_id) &
            (medical_providers.c.family_id == current_user['family_id'])
        )
        provider = await database.fetch_one(query)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Medical provider not found")
        
        return MedicalProviderResponse(
            id=provider['id'],
            name=provider['name'],
            specialty=provider['specialty'],
            address=provider['address'],
            phone=provider['phone'],
            email=provider['email'],
            website=provider['website'],
            latitude=float(provider['latitude']) if provider['latitude'] else None,
            longitude=float(provider['longitude']) if provider['longitude'] else None,
            zip_code=provider['zip_code'],
            notes=provider['notes'],
            google_place_id=provider['google_place_id'],
            rating=float(provider['rating']) if provider['rating'] else None,
            family_id=str(provider['family_id']),
            created_by_user_id=str(provider['created_by_user_id']),
            created_at=str(provider['created_at']),
            updated_at=str(provider['updated_at'])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching medical provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch medical provider")

@router.put("/{provider_id}", response_model=MedicalProviderResponse)
async def update_medical_provider(
    provider_id: int, 
    provider_data: MedicalProviderUpdate, 
    current_user = Depends(get_current_user)
):
    """
    Update an existing medical provider (must belong to user's family).
    """
    try:
        # Check if the provider exists and belongs to the user's family
        existing_provider = await database.fetch_one(
            medical_providers.select().where(
                (medical_providers.c.id == provider_id) &
                (medical_providers.c.family_id == current_user['family_id'])
            )
        )
        
        if not existing_provider:
            raise HTTPException(status_code=404, detail="Medical provider not found")
        
        # Prepare update data (only include non-None values)
        update_data = {"updated_at": datetime.now()}
        
        for field, value in provider_data.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        # Update the provider
        query = medical_providers.update().where(
            medical_providers.c.id == provider_id
        ).values(**update_data)
        
        await database.execute(query)
        
        # Fetch the updated provider
        updated_provider = await database.fetch_one(
            medical_providers.select().where(medical_providers.c.id == provider_id)
        )
        
        return MedicalProviderResponse(
            id=updated_provider['id'],
            name=updated_provider['name'],
            specialty=updated_provider['specialty'],
            address=updated_provider['address'],
            phone=updated_provider['phone'],
            email=updated_provider['email'],
            website=updated_provider['website'],
            latitude=float(updated_provider['latitude']) if updated_provider['latitude'] else None,
            longitude=float(updated_provider['longitude']) if updated_provider['longitude'] else None,
            zip_code=updated_provider['zip_code'],
            notes=updated_provider['notes'],
            google_place_id=updated_provider['google_place_id'],
            rating=float(updated_provider['rating']) if updated_provider['rating'] else None,
            family_id=str(updated_provider['family_id']),
            created_by_user_id=str(updated_provider['created_by_user_id']),
            created_at=str(updated_provider['created_at']),
            updated_at=str(updated_provider['updated_at'])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating medical provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update medical provider")

@router.delete("/{provider_id}")
async def delete_medical_provider(provider_id: int, current_user = Depends(get_current_user)):
    """
    Delete a medical provider (must belong to user's family).
    """
    try:
        # Check if the provider exists and belongs to the user's family
        existing_provider = await database.fetch_one(
            medical_providers.select().where(
                (medical_providers.c.id == provider_id) &
                (medical_providers.c.family_id == current_user['family_id'])
            )
        )
        
        if not existing_provider:
            raise HTTPException(status_code=404, detail="Medical provider not found")
        
        # Delete the provider
        query = medical_providers.delete().where(medical_providers.c.id == provider_id)
        await database.execute(query)
        
        return {"message": "Medical provider deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting medical provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete medical provider")

@router.post("/search", response_model=MedicalSearchResponse)
async def search_medical_providers(
    search_data: MedicalSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search for medical providers using Google Places API
    """
    try:
        # Get Google Places API key from environment
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google Places API key not configured")
        
        logger.info(f"Medical provider search: location_type={search_data.location_type}, "
                   f"lat={search_data.latitude}, lng={search_data.longitude}, "
                   f"radius={search_data.radius}m, specialty={search_data.specialty}")
        
        # Build search query for medical providers
        search_terms = []
        if search_data.specialty:
            search_terms.append(search_data.specialty)
        else:
            search_terms.extend(["doctor", "physician", "medical", "clinic", "hospital"])
        
        # Search for medical providers using Google Places API
        if search_data.location_type == "zipcode" and search_data.zipcode:
            # Use new Places API (New) Text Search for ZIP code searches
            places_url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": google_api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.rating,places.websiteUri,places.businessStatus"
            }
            
            query_text = f"{' '.join(search_terms)} near {search_data.zipcode}"
            body = {
                "textQuery": query_text,
                "maxResultCount": 20
            }
            use_distance_calculation = False
            use_new_api = True
            
        elif search_data.location_type == "current" and search_data.latitude and search_data.longitude:
            # Use legacy Nearby Search API for current location searches
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            # Build keyword for medical search
            keyword = " OR ".join(search_terms)
            
            params = {
                "location": f"{search_data.latitude},{search_data.longitude}",
                "radius": search_data.radius,
                "type": "hospital",  # Primary type
                "keyword": keyword,
                "key": google_api_key
            }
            use_distance_calculation = True
            use_new_api = False
            latitude = search_data.latitude
            longitude = search_data.longitude
            
        else:
            raise HTTPException(status_code=400, detail="Invalid location data")
        
        async with httpx.AsyncClient() as client:
            if use_new_api:
                # Use POST for new Places API
                places_response = await client.post(places_url, headers=headers, json=body)
            else:
                # Use GET for legacy API
                places_response = await client.get(places_url, params=params)
        
        if places_response.status_code != 200:
            logger.error(f"Google Places API error: {places_response.status_code} - {places_response.text}")
            raise HTTPException(status_code=500, detail="Error searching medical providers")
        
        places_data = places_response.json()
        search_results = []
        
        if use_new_api:
            # Process new API response format
            places = places_data.get("places", [])
            logger.info(f"New Places API returned {len(places)} results")
            
            for place in places:
                # Calculate distance if using zipcode search (approximate)
                distance = None
                
                result = MedicalSearchResult(
                    id=place.get("id", ""),
                    name=place.get("displayName", {}).get("text", ""),
                    specialty=search_data.specialty,  # Use the searched specialty
                    address=place.get("formattedAddress", ""),
                    phone_number=place.get("nationalPhoneNumber"),
                    website=place.get("websiteUri"),
                    rating=place.get("rating"),
                    place_id=place.get("id", ""),
                    distance=distance
                )
                search_results.append(result)
                
        else:
            # Process legacy API response format
            places = places_data.get("results", [])
            logger.info(f"Legacy Places API returned {len(places)} results")
            
            for place in places:
                # Calculate distance using coordinates
                distance = None
                if use_distance_calculation and "geometry" in place and "location" in place["geometry"]:
                    place_lat = place["geometry"]["location"]["lat"]
                    place_lng = place["geometry"]["location"]["lng"]
                    distance = calculate_distance(latitude, longitude, place_lat, place_lng)
                
                # Format phone number
                phone = place.get("formatted_phone_number") or place.get("international_phone_number")
                
                result = MedicalSearchResult(
                    id=place.get("place_id", ""),
                    name=place.get("name", ""),
                    specialty=search_data.specialty,  # Use the searched specialty
                    address=place.get("vicinity", ""),
                    phone_number=phone,
                    website=place.get("website"),
                    rating=place.get("rating"),
                    place_id=place.get("place_id", ""),
                    distance=distance
                )
                search_results.append(result)
        
        # Sort by distance if available
        if use_distance_calculation:
            search_results.sort(key=lambda x: x.distance if x.distance is not None else float('inf'))
        
        total = len(search_results)
        logger.info(f"Medical provider search returned {total} results")
        
        return MedicalSearchResponse(
            results=search_results,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching medical providers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula
    """
    # Earth's radius in meters
    R = 6371000
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c