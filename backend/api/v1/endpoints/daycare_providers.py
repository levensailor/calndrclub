from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from datetime import datetime
import os
import httpx

from backend.core.database import database
from backend.core.security import get_current_user
from backend.core.logging import logger
from backend.db.models import daycare_providers, daycare_calendar_syncs
from backend.schemas.daycare import DaycareProviderCreate, DaycareProviderResponse, DaycareSearchRequest, DaycareSearchResult
from backend.services.daycare_events_service import discover_calendar_url, parse_events_from_url, store_daycare_events
from backend.services.sync_management_service import assign_daycare_sync_to_family

router = APIRouter()

@router.get("", response_model=List[DaycareProviderResponse])
async def get_daycare_providers(current_user = Depends(get_current_user)):
    """
    Get all daycare providers for the current user's family.
    """
    try:
        query = daycare_providers.select().where(daycare_providers.c.family_id == current_user['family_id'])
        providers = await database.fetch_all(query)
        
        return [
            DaycareProviderResponse(
                id=provider['id'],
                name=provider['name'],
                address=provider['address'],
                phone_number=provider['phone_number'],
                email=provider['email'],
                hours=provider['hours'],
                notes=provider['notes'],
                google_place_id=provider['google_place_id'],
                rating=float(provider['rating']) if provider['rating'] else None,
                website=provider['website'],
                created_by_user_id=str(provider['created_by_user_id']),
                created_at=str(provider['created_at']),
                updated_at=str(provider['updated_at'])
            )
            for provider in providers
        ]
    except Exception as e:
        logger.error(f"Error fetching daycare providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch daycare providers")

@router.post("", response_model=DaycareProviderResponse)
async def create_daycare_provider(provider_data: DaycareProviderCreate, current_user = Depends(get_current_user)):
    """
    Create a new daycare provider for the current user's family.
    """
    try:
        insert_query = daycare_providers.insert().values(
            family_id=current_user['family_id'],
            name=provider_data.name,
            address=provider_data.address,
            phone_number=provider_data.phone_number,
            email=provider_data.email,
            hours=provider_data.hours,
            notes=provider_data.notes,
            google_place_id=provider_data.google_place_id,
            rating=provider_data.rating,
            website=provider_data.website,
            created_by_user_id=current_user['id'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        provider_id = await database.execute(insert_query)
        
        # Fetch the created provider
        provider_record = await database.fetch_one(daycare_providers.select().where(daycare_providers.c.id == provider_id))
        
        return DaycareProviderResponse(
            id=provider_record['id'],
            name=provider_record['name'],
            address=provider_record['address'],
            phone_number=provider_record['phone_number'],
            email=provider_record['email'],
            hours=provider_record['hours'],
            notes=provider_record['notes'],
            google_place_id=provider_record['google_place_id'],
            rating=float(provider_record['rating']) if provider_record['rating'] else None,
            website=provider_record['website'],
            created_by_user_id=str(provider_record['created_by_user_id']),
            created_at=str(provider_record['created_at']),
            updated_at=str(provider_record['updated_at'])
        )
    except Exception as e:
        logger.error(f"Error creating daycare provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to create daycare provider")

@router.put("/{provider_id}", response_model=DaycareProviderResponse)
async def update_daycare_provider(provider_id: int, provider_data: DaycareProviderCreate, current_user = Depends(get_current_user)):
    """
    Update a daycare provider that belongs to the current user's family.
    """
    try:
        # Check if provider exists and belongs to user's family
        check_query = daycare_providers.select().where(
            (daycare_providers.c.id == provider_id) &
            (daycare_providers.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Daycare provider not found")
        
        # Update the provider
        update_query = daycare_providers.update().where(daycare_providers.c.id == provider_id).values(
            name=provider_data.name,
            address=provider_data.address,
            phone_number=provider_data.phone_number,
            email=provider_data.email,
            hours=provider_data.hours,
            notes=provider_data.notes,
            google_place_id=provider_data.google_place_id,
            rating=provider_data.rating,
            website=provider_data.website,
            updated_at=datetime.now()
        )
        await database.execute(update_query)
        
        # Fetch the updated provider
        provider_record = await database.fetch_one(daycare_providers.select().where(daycare_providers.c.id == provider_id))
        
        return DaycareProviderResponse(
            id=provider_record['id'],
            name=provider_record['name'],
            address=provider_record['address'],
            phone_number=provider_record['phone_number'],
            email=provider_record['email'],
            hours=provider_record['hours'],
            notes=provider_record['notes'],
            google_place_id=provider_record['google_place_id'],
            rating=float(provider_record['rating']) if provider_record['rating'] else None,
            website=provider_record['website'],
            created_by_user_id=str(provider_record['created_by_user_id']),
            created_at=str(provider_record['created_at']),
            updated_at=str(provider_record['updated_at'])
        )
    except Exception as e:
        logger.error(f"Error updating daycare provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to update daycare provider")

@router.delete("/{provider_id}")
async def delete_daycare_provider(provider_id: int, current_user = Depends(get_current_user)):
    """
    Delete a daycare provider that belongs to the current user's family.
    """
    try:
        # Check if provider exists and belongs to user's family
        check_query = daycare_providers.select().where(
            (daycare_providers.c.id == provider_id) &
            (daycare_providers.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Daycare provider not found")
        
        # Delete the provider
        delete_query = daycare_providers.delete().where(daycare_providers.c.id == provider_id)
        await database.execute(delete_query)
        
        return {"status": "success", "message": "Daycare provider deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting daycare provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete daycare provider")

@router.get("/{provider_id}/discover-calendar")
async def discover_daycare_calendar_url(provider_id: int, current_user = Depends(get_current_user)):
    """
    Discover the calendar/events URL for a specific daycare provider.
    """
    try:
        # Get the daycare provider
        query = daycare_providers.select().where(
            (daycare_providers.c.id == provider_id) &
            (daycare_providers.c.family_id == current_user['family_id'])
        )
        provider = await database.fetch_one(query)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Daycare provider not found")
        
        if not provider['website']:
            raise HTTPException(status_code=400, detail="Daycare provider has no website URL")
        
        # Discover calendar URL
        calendar_url = await discover_calendar_url(provider['website'])
        
        return {
            "provider_id": provider_id,
            "provider_name": provider['name'],
            "base_website": provider['website'],
            "discovered_calendar_url": calendar_url,
            "success": calendar_url is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering calendar URL for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover calendar URL")

@router.post("/{provider_id}/parse-events")
async def parse_daycare_events(
    provider_id: int, 
    request_data: Dict[str, str],
    current_user = Depends(get_current_user)
):
    """
    Parse events from a daycare provider's calendar URL.
    Expects {"calendar_url": "https://..."} in the request body.
    """
    try:
        calendar_url = request_data.get("calendar_url")
        if not calendar_url:
            raise HTTPException(status_code=400, detail="calendar_url is required")
        
        # Get the daycare provider for context
        query = daycare_providers.select().where(
            (daycare_providers.c.id == provider_id) &
            (daycare_providers.c.family_id == current_user['family_id'])
        )
        provider = await database.fetch_one(query)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Daycare provider not found")
        
        # Parse events from the calendar URL
        events = await parse_events_from_url(calendar_url)
        
        # Store events using the new daycare events service
        if events:
            await store_daycare_events(provider_id, events, provider['name'])
        
        # Record or update the calendar sync configuration
        if events:  # Only track successful syncs
            try:
                # Check if sync config already exists
                existing_sync = await database.fetch_one(
                    daycare_calendar_syncs.select().where(
                        (daycare_calendar_syncs.c.daycare_provider_id == provider_id) &
                        (daycare_calendar_syncs.c.calendar_url == calendar_url)
                    )
                )
                
                from datetime import datetime, timezone
                sync_data = {
                    "last_sync_at": datetime.now(timezone.utc),
                    "last_sync_success": True,
                    "last_sync_error": None,
                    "events_count": len(events),
                    "sync_enabled": True
                }
                
                if existing_sync:
                    # Update existing sync config
                    await database.execute(
                        daycare_calendar_syncs.update()
                        .where(daycare_calendar_syncs.c.id == existing_sync['id'])
                        .values(**sync_data)
                    )
                    # Assign sync to family if it's enabled
                    if sync_data.get("sync_enabled", True):
                        await assign_daycare_sync_to_family(provider_id, existing_sync['id'])
                else:
                    # Create new sync config
                    sync_data.update({
                        "daycare_provider_id": provider_id,
                        "calendar_url": calendar_url
                    })
                    sync_id = await database.execute(
                        daycare_calendar_syncs.insert().values(**sync_data)
                    )
                    # Assign the new sync to the family
                    await assign_daycare_sync_to_family(provider_id, sync_id)
                
                logger.info(f"Recorded calendar sync for provider {provider_id}: {len(events)} events")
                
            except Exception as e:
                logger.error(f"Failed to record calendar sync config: {e}")
                # Don't fail the whole request if sync tracking fails
        
        return {
            "provider_id": provider_id,
            "provider_name": provider['name'],
            "calendar_url": calendar_url,
            "events_count": len(events),
            "events": events,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing events for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse events: {str(e)}")

@router.post("/search", response_model=List[DaycareSearchResult])
async def search_daycare_providers(search_data: DaycareSearchRequest, current_user = Depends(get_current_user)):
    """
    Search for daycare providers using Google Places API.
    """
    try:
        # Get Google Places API key from environment
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google Places API key not configured")
        
        # Search for daycare providers using Google Places API
        if search_data.location_type == "zipcode" and search_data.zipcode:
            # Use new Places API (New) Text Search for ZIP code searches
            places_url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": google_api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.rating,places.websiteUri,places.businessStatus,places.regularOpeningHours"
            }
            body = {
                "textQuery": f"daycare centers near {search_data.zipcode}",
                "maxResultCount": 20  # Request more results
            }
            use_distance_calculation = False  # No reference point for distance
            use_new_api = True
        elif search_data.location_type == "current" and search_data.latitude and search_data.longitude:
            # Use legacy Nearby Search API for current location searches
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{search_data.latitude},{search_data.longitude}",
                "radius": search_data.radius,
                "type": "school",
                "keyword": "daycare OR childcare OR preschool OR nursery",
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
            
            places_data = places_response.json()
            
            # Handle different response formats between new and legacy APIs
            if use_new_api:
                # New Places API (New) format
                if "places" not in places_data:
                    logger.error(f"New Places API error: {places_data}")
                    return []
                places_list = places_data.get("places", [])
            else:
                # Legacy API format
                if places_data.get("status") != "OK":
                    logger.error(f"Google Places API error: {places_data.get('status')}")
                    return []
                places_list = places_data.get("results", [])
            
            results = []
            for place in places_list:
                if use_new_api:
                    # New API format - data is already included in the response
                    place_id = place.get("id", "")
                    name = place.get("displayName", {}).get("text", "")
                    address = place.get("formattedAddress", "")
                    phone_number = place.get("nationalPhoneNumber")
                    rating = place.get("rating")
                    website = place.get("websiteUri")
                    
                    # Format opening hours from new API
                    hours = None
                    if place.get("regularOpeningHours") and place["regularOpeningHours"].get("weekdayDescriptions"):
                        hours = "; ".join(place["regularOpeningHours"]["weekdayDescriptions"])
                    
                    # No distance calculation for ZIP code searches
                    distance = None
                    
                    results.append(DaycareSearchResult(
                        place_id=place_id,
                        name=name,
                        address=address,
                        phone_number=phone_number,
                        rating=rating,
                        website=website,
                        hours=hours,
                        distance=distance
                    ))
                else:
                    # Legacy API format - need to fetch additional details
                    place_id = place.get("place_id")
                    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        "place_id": place_id,
                        "fields": "name,formatted_address,formatted_phone_number,rating,website,opening_hours",
                        "key": google_api_key
                    }
                    
                    details_response = await client.get(details_url, params=details_params)
                    details_data = details_response.json()
                    
                    if details_data.get("status") == "OK":
                        result = details_data.get("result", {})
                        
                        # Calculate distance (approximate) only for current location searches
                        distance = None
                        if use_distance_calculation:
                            place_location = place.get("geometry", {}).get("location", {})
                            if place_location:
                                # Simple distance calculation (not precise, but good enough for sorting)
                                lat_diff = abs(latitude - place_location.get("lat", 0))
                                lng_diff = abs(longitude - place_location.get("lng", 0))
                                distance = (lat_diff + lng_diff) * 111000  # Rough conversion to meters
                        
                        # Format opening hours
                        hours = None
                        if result.get("opening_hours"):
                            hours = "; ".join(result["opening_hours"].get("weekday_text", []))
                        
                        results.append(DaycareSearchResult(
                            place_id=place_id,
                            name=result.get("name", ""),
                            address=result.get("formatted_address", ""),
                            phone_number=result.get("formatted_phone_number"),
                            rating=result.get("rating"),
                            website=result.get("website"),
                            hours=hours,
                            distance=distance
                        ))
            
            # Sort by distance if available (current location searches) or by name (ZIP code searches)
            if use_distance_calculation:
                results.sort(key=lambda x: x.distance if x.distance else float('inf'))
            else:
                results.sort(key=lambda x: x.name.lower())
            
            return results
            
    except Exception as e:
        logger.error(f"Error searching daycare providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to search daycare providers")

@router.get("/{provider_id}/calendar-sync")
async def get_daycare_calendar_sync(provider_id: int, current_user = Depends(get_current_user)):
    """
    Get the calendar sync configuration for a daycare provider.
    """
    try:
        # Check if provider exists and belongs to user's family
        provider_query = daycare_providers.select().where(
            (daycare_providers.c.id == provider_id) &
            (daycare_providers.c.family_id == current_user['family_id'])
        )
        provider = await database.fetch_one(provider_query)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Daycare provider not found")
        
        # Get calendar sync config
        sync_query = daycare_calendar_syncs.select().where(
            daycare_calendar_syncs.c.daycare_provider_id == provider_id
        ).order_by(daycare_calendar_syncs.c.created_at.desc())
        
        sync_config = await database.fetch_one(sync_query)
        
        if not sync_config:
            return {
                "provider_id": provider_id,
                "provider_name": provider['name'],
                "calendar_url": None,
                "sync_enabled": False,
                "last_sync_at": None,
                "last_sync_success": None,
                "events_count": 0
            }
        
        return {
            "provider_id": provider_id,
            "provider_name": provider['name'],
            "calendar_url": sync_config['calendar_url'],
            "sync_enabled": sync_config['sync_enabled'],
            "last_sync_at": sync_config['last_sync_at'].isoformat() if sync_config['last_sync_at'] else None,
            "last_sync_success": sync_config['last_sync_success'],
            "events_count": sync_config['events_count']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting calendar sync for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get calendar sync info")
