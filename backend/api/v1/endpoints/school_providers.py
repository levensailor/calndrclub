from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from datetime import datetime
import os
import json
import httpx

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import school_providers, school_calendar_syncs
from schemas.school import SchoolProviderCreate, SchoolProviderResponse, SchoolSearchRequest, SchoolSearchResult
from services.school_events_service import discover_calendar_url, parse_events_from_url, store_school_events
from services.sync_management_service import assign_school_sync_to_family

router = APIRouter()

@router.get("", response_model=List[SchoolProviderResponse])
async def get_school_providers(current_user = Depends(get_current_user)):
    """
    Get all school providers for the current user's family.
    """
    try:
        query = school_providers.select().where(school_providers.c.family_id == current_user['family_id'])
        providers = await database.fetch_all(query)
        
        return [
            SchoolProviderResponse(
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
        logger.error(f"Error fetching school providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch school providers")

@router.post("", response_model=SchoolProviderResponse)
async def create_school_provider(provider_data: SchoolProviderCreate, current_user = Depends(get_current_user)):
    """
    Create a new school provider for the current user's family.
    """
    try:
        insert_query = school_providers.insert().values(
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
        provider_record = await database.fetch_one(school_providers.select().where(school_providers.c.id == provider_id))
        
        return SchoolProviderResponse(
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
        logger.error(f"Error creating school provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to create school provider")

@router.put("/{provider_id}", response_model=SchoolProviderResponse)
async def update_school_provider(provider_id: int, provider_data: SchoolProviderCreate, current_user = Depends(get_current_user)):
    """
    Update a school provider that belongs to the current user's family.
    """
    try:
        # Check if provider exists and belongs to user's family
        check_query = school_providers.select().where(
            (school_providers.c.id == provider_id) &
            (school_providers.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        
        if not existing:
            raise HTTPException(status_code=404, detail="School provider not found")
        
        # Update the provider
        update_query = school_providers.update().where(school_providers.c.id == provider_id).values(
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
        provider_record = await database.fetch_one(school_providers.select().where(school_providers.c.id == provider_id))
        
        return SchoolProviderResponse(
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
        logger.error(f"Error updating school provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to update school provider")

@router.delete("/{provider_id}")
async def delete_school_provider(provider_id: int, current_user = Depends(get_current_user)):
    """
    Delete a school provider that belongs to the current user's family.
    """
    try:
        # Check if provider exists and belongs to user's family
        check_query = school_providers.select().where(
            (school_providers.c.id == provider_id) &
            (school_providers.c.family_id == current_user['family_id'])
        )
        existing = await database.fetch_one(check_query)
        
        if not existing:
            raise HTTPException(status_code=404, detail="School provider not found")
        
        # Delete the provider
        delete_query = school_providers.delete().where(school_providers.c.id == provider_id)
        await database.execute(delete_query)
        
        return {"status": "success", "message": "School provider deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting school provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete school provider")

@router.get("/{provider_id}/discover-calendar")
async def discover_school_calendar(provider_id: int, current_user = Depends(get_current_user)):
    """
    Discover calendar URL for a school provider.
    """
    logger.info(f"🔍 School calendar discovery request for provider {provider_id} by user {current_user['id']}")
    try:
        # Check if provider exists and belongs to user's family
        check_query = school_providers.select().where(
            (school_providers.c.id == provider_id) &
            (school_providers.c.family_id == current_user['family_id'])
        )
        provider = await database.fetch_one(check_query)
        
        if not provider:
            raise HTTPException(status_code=404, detail="School provider not found")
        
        # Check if provider has a website
        if not provider['website']:
            return {
                "provider_id": provider_id,
                "provider_name": provider['name'],
                "base_website": "",
                "discovered_calendar_url": None,
                "success": False
            }
        
        # Try to discover calendar URL
        logger.info(f"🌐 Attempting calendar discovery for {provider['name']} at {provider['website']}")
        calendar_url = await discover_calendar_url(provider['name'], provider['website'])
        
        response_data = {
            "provider_id": provider_id,
            "provider_name": provider['name'],
            "base_website": provider['website'] or "",
            "discovered_calendar_url": calendar_url,
            "success": calendar_url is not None
        }
        
        logger.info(f"📊 School calendar discovery response: {response_data}")
        return response_data
    except Exception as e:
        logger.error(f"Error discovering school calendar: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover calendar")

@router.post("/{provider_id}/parse-events")
async def parse_school_events(
    provider_id: int, 
    request_data: Dict[str, str],
    current_user = Depends(get_current_user)
):
    """
    Parse events from a school calendar URL and store them.
    """
    try:
        # Check if provider exists and belongs to user's family
        check_query = school_providers.select().where(
            (school_providers.c.id == provider_id) &
            (school_providers.c.family_id == current_user['family_id'])
        )
        provider = await database.fetch_one(check_query)
        
        if not provider:
            raise HTTPException(status_code=404, detail="School provider not found")
        
        calendar_url = request_data.get('calendar_url')
        if not calendar_url:
            raise HTTPException(status_code=400, detail="Calendar URL is required")
        
        # Parse events from the calendar URL
        events = await parse_events_from_url(calendar_url)
        
        # Store events using the new school events service
        if events:
            await store_school_events(provider_id, events, provider['name'])
        
        # Record or update the calendar sync configuration
        if events:  # Only track successful syncs
            try:
                # Check if sync config already exists
                existing_sync = await database.fetch_one(
                    school_calendar_syncs.select().where(
                        (school_calendar_syncs.c.school_provider_id == provider_id) &
                        (school_calendar_syncs.c.calendar_url == calendar_url)
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
                        school_calendar_syncs.update()
                        .where(school_calendar_syncs.c.id == existing_sync['id'])
                        .values(**sync_data)
                    )
                    # Assign sync to family if it's enabled
                    if sync_data.get("sync_enabled", True):
                        await assign_school_sync_to_family(provider_id, existing_sync['id'])
                else:
                    # Create new sync config
                    sync_data.update({
                        "school_provider_id": provider_id,
                        "calendar_url": calendar_url
                    })
                    sync_id = await database.execute(
                        school_calendar_syncs.insert().values(**sync_data)
                    )
                    # Assign the new sync to the family
                    await assign_school_sync_to_family(provider_id, sync_id)
                
                logger.info(f"Recorded calendar sync for school provider {provider_id}: {len(events)} events")
                
            except Exception as e:
                logger.error(f"Failed to record calendar sync config: {e}")
                # Don't fail the whole request if sync tracking fails
        
        return {
            "events_count": len(events) if events else 0,
            "message": f"Successfully parsed {len(events) if events else 0} events"
        }
    except Exception as e:
        logger.error(f"Error parsing school events: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse events")

@router.post("/search", response_model=List[SchoolSearchResult])
async def search_school_providers(search_data: SchoolSearchRequest, current_user = Depends(get_current_user)):
    """
    Search for school providers using Google Places API.
    """
    try:
        # Get Google Places API key from environment
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google Places API key not configured")
        
        # Search for school providers using Google Places API
        if search_data.location_type == "zipcode" and search_data.zipcode:
            # Use new Places API (New) Text Search for ZIP code searches
            places_url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": google_api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.rating,places.websiteUri,places.businessStatus,places.regularOpeningHours"
            }
            body = {
                "textQuery": f"schools near {search_data.zipcode}"
            }
            use_distance_calculation = False  # No reference point for distance
            use_new_api = True
        else:
            # Use legacy Places API for coordinate-based searches
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{search_data.latitude},{search_data.longitude}",
                "radius": search_data.radius,
                "type": "school",
                "key": google_api_key
            }
            use_distance_calculation = True
            use_new_api = False
        
        async with httpx.AsyncClient() as client:
            logger.info(f"🔍 School Search Request - Type: {search_data.location_type}")
            if use_new_api:
                logger.info(f"📡 Using NEW Google Places API - URL: {places_url}")
                logger.info(f"📋 Request Headers: {headers}")
                logger.info(f"📋 Request Body: {body}")
                response = await client.post(places_url, headers=headers, json=body)
            else:
                logger.info(f"📡 Using LEGACY Google Places API - URL: {places_url}")
                logger.info(f"📋 Request Params: {params}")
                response = await client.get(places_url, params=params)
            
            logger.info(f"📊 API Response Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Google Places API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Failed to search for schools")
            
            data = response.json()
            logger.info(f"📄 Raw API Response Data: {json.dumps(data, indent=2)}")
            
            if use_new_api:
                places_list = data.get("places", [])
                logger.info(f"🏫 Found {len(places_list)} schools using NEW API")
            else:
                places_list = data.get("results", [])
                logger.info(f"🏫 Found {len(places_list)} schools using LEGACY API")
        
        results = []
        
        for i, place in enumerate(places_list):
            logger.info(f"🏫 Processing School #{i+1}")
            logger.info(f"📋 Raw Place Data: {json.dumps(place, indent=2)}")
            
            if use_new_api:
                # New API format - data is already included in the response
                place_id = place.get("id", "")
                name = place.get("displayName", {}).get("text", "")
                address = place.get("formattedAddress", "")
                phone_number = place.get("nationalPhoneNumber")
                rating = place.get("rating")
                website = place.get("websiteUri")
                
                logger.info(f"🆔 Extracted place_id: '{place_id}'")
                logger.info(f"🏷️ Extracted name: '{name}'")
                logger.info(f"📍 Extracted address: '{address}'")
                logger.info(f"📞 Extracted phone_number: '{phone_number}'")
                logger.info(f"⭐ Extracted rating: '{rating}'")
                logger.info(f"🌐 Extracted website: '{website}'")
                
                # Format opening hours from new API
                hours = None
                opening_hours_data = place.get("regularOpeningHours")
                if opening_hours_data:
                    logger.info(f"🕒 Raw opening hours data: {json.dumps(opening_hours_data, indent=2)}")
                    if opening_hours_data.get("weekdayDescriptions"):
                        hours = "; ".join(opening_hours_data["weekdayDescriptions"])
                        logger.info(f"🕒 Formatted hours: '{hours}'")
                else:
                    logger.info("🕒 No opening hours data found")
                
                # No distance calculation for ZIP code searches
                distance = None
                
                logger.info(f"✅ Final SchoolSearchResult: place_id='{place_id}', name='{name}', address='{address}', phone='{phone_number}', rating='{rating}', website='{website}', hours='{hours}', distance='{distance}'")
                
                results.append(SchoolSearchResult(
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
                # Legacy API format - need details request for some fields
                place_id = place.get("place_id", "")
                name = place.get("name", "")
                address = place.get("vicinity", "")
                rating = place.get("rating")
                
                logger.info(f"🆔 Legacy API - Extracted place_id: '{place_id}'")
                logger.info(f"🏷️ Legacy API - Extracted name: '{name}'")
                logger.info(f"📍 Legacy API - Extracted address: '{address}'")
                logger.info(f"⭐ Legacy API - Extracted rating: '{rating}'")
                
                # Calculate distance if location provided
                distance = None
                if use_distance_calculation and search_data.latitude and search_data.longitude:
                    place_lat = place.get("geometry", {}).get("location", {}).get("lat")
                    place_lng = place.get("geometry", {}).get("location", {}).get("lng")
                    if place_lat and place_lng:
                        # Simple distance calculation (not perfectly accurate but good enough)
                        import math
                        lat_diff = math.radians(place_lat - search_data.latitude)
                        lng_diff = math.radians(place_lng - search_data.longitude)
                        a = math.sin(lat_diff/2)**2 + math.cos(math.radians(search_data.latitude)) * math.cos(math.radians(place_lat)) * math.sin(lng_diff/2)**2
                        c = 2 * math.asin(math.sqrt(a))
                        distance = 6371000 * c  # Earth radius in meters
                        logger.info(f"📏 Legacy API - Calculated distance: {distance} meters")
                
                # Get additional details
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    "place_id": place_id,
                    "fields": "formatted_phone_number,website,opening_hours",
                    "key": google_api_key
                }
                
                logger.info(f"📡 Legacy API - Fetching details for place_id: {place_id}")
                logger.info(f"📋 Legacy API - Details request params: {details_params}")
                
                try:
                    details_response = await client.get(details_url, params=details_params)
                    logger.info(f"📊 Legacy API - Details response status: {details_response.status_code}")
                    
                    if details_response.status_code == 200:
                        details_data = details_response.json()
                        logger.info(f"📄 Legacy API - Raw details data: {json.dumps(details_data, indent=2)}")
                        
                        result = details_data.get("result", {})
                        phone_number = result.get("formatted_phone_number")
                        website = result.get("website")
                        opening_hours = result.get("opening_hours", {}).get("weekday_text")
                        hours = "; ".join(opening_hours) if opening_hours else None
                        
                        logger.info(f"📞 Legacy API - Extracted phone from details: '{phone_number}'")
                        logger.info(f"🌐 Legacy API - Extracted website from details: '{website}'")
                        logger.info(f"🕒 Legacy API - Extracted hours from details: '{hours}'")
                    else:
                        logger.warning(f"❌ Legacy API - Details request failed: {details_response.text}")
                        phone_number = None
                        website = None
                        hours = None
                except Exception as e:
                    logger.error(f"❌ Legacy API - Exception during details request: {e}")
                    phone_number = None
                    website = None
                    hours = None
                
                logger.info(f"✅ Legacy API - Final SchoolSearchResult: place_id='{place_id}', name='{name}', address='{address}', phone='{phone_number}', rating='{rating}', website='{website}', hours='{hours}', distance='{distance}'")
                
                results.append(SchoolSearchResult(
                    place_id=place_id,
                    name=name,
                    address=address,
                    phone_number=phone_number,
                    rating=rating,
                    website=website,
                    hours=hours,
                    distance=distance
                ))
        
        logger.info(f"🎯 School Search Complete - Returning {len(results)} results")
        for i, result in enumerate(results):
            logger.info(f"📋 Result #{i+1}: {result.dict()}")
        
        return results
    except Exception as e:
        logger.error(f"Error searching school providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to search for schools") 