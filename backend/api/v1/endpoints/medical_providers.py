"""
Medical Providers API Endpoints
Handles CRUD operations for medical providers
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime

from core.database import database
from core.security import get_current_user
from db.models import medical_providers, users
from schemas.medical_provider import (
    MedicalProviderCreate,
    MedicalProviderUpdate,
    MedicalProviderResponse,
    MedicalProviderSearchParams,
    MedicalProviderListResponse,
    MedicalSearchRequest
)
from utils.location_service import location_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=MedicalProviderListResponse)
async def get_medical_providers(
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort by: name, created_at"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all medical providers for the authenticated family
    """
    try:
        # Build base query
        query = medical_providers.select().where(
            medical_providers.c.family_id == current_user["family_id"]
        )
        
        # Apply specialty filter
        if specialty:
            query = query.where(
                medical_providers.c.specialty.ilike(f"%{specialty}%")
            )
        
        # Get total count
        count_query = medical_providers.select().where(
            medical_providers.c.family_id == current_user["family_id"]
        )
        if specialty:
            count_query = count_query.where(
                medical_providers.c.specialty.ilike(f"%{specialty}%")
            )
        total = await database.fetch_val(
            f"SELECT COUNT(*) FROM medical_providers WHERE family_id = '{current_user['family_id']}'" + 
            (f" AND specialty ILIKE '%{specialty}%'" if specialty else "")
        )
        total = total or 0
        
        # Apply sorting
        if sort_by == "name":
            order_column = medical_providers.c.name
        elif sort_by == "created_at":
            order_column = medical_providers.c.created_at
        else:
            order_column = medical_providers.c.name
        
        if sort_order.lower() == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        providers = await database.fetch_all(query)
        
        # Convert to response format
        provider_list = []
        for provider in providers:
            provider_dict = dict(provider)
            provider_list.append(MedicalProviderResponse(**provider_dict))
        
        total_pages = (total + limit - 1) // limit
        
        return MedicalProviderListResponse(
            providers=provider_list,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error fetching medical providers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=MedicalProviderResponse)
async def create_medical_provider(
    provider_data: MedicalProviderCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new medical provider
    """
    try:
        # Validate family ownership
        if provider_data.family_id != current_user["family_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Prepare data
        provider_dict = provider_data.dict()
        
        # Geocode address if coordinates not provided
        if provider_dict.get("address") and not (provider_dict.get("latitude") and provider_dict.get("longitude")):
            coords = location_service.geocode_address(provider_dict["address"])
            if coords:
                provider_dict["latitude"], provider_dict["longitude"] = coords
        
        # Extract ZIP code if not provided
        if provider_dict.get("address") and not provider_dict.get("zip_code"):
            zip_code = location_service.extract_zip_code(provider_dict["address"])
            if zip_code:
                provider_dict["zip_code"] = zip_code
        
        # Format phone number
        if provider_dict.get("phone"):
            provider_dict["phone"] = location_service.format_phone_number(provider_dict["phone"])
        
        # Set timestamps
        provider_dict["created_at"] = datetime.now()
        provider_dict["updated_at"] = datetime.now()
        
        # Insert into database
        query = medical_providers.insert().values(**provider_dict)
        provider_id = await database.execute(query)
        
        # Get the created provider
        created_provider = await database.fetch_one(
            medical_providers.select().where(medical_providers.c.id == provider_id)
        )
        
        return MedicalProviderResponse(**dict(created_provider))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating medical provider: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{provider_id}", response_model=MedicalProviderResponse)
async def get_medical_provider(
    provider_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific medical provider
    """
    try:
        provider = await database.fetch_one(
            medical_providers.select().where(
                and_(
                    medical_providers.c.id == provider_id,
                    medical_providers.c.family_id == current_user["family_id"]
                )
            )
        )
        
        if not provider:
            raise HTTPException(status_code=404, detail="Medical provider not found")
        
        return MedicalProviderResponse(**dict(provider))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching medical provider: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{provider_id}", response_model=MedicalProviderResponse)
async def update_medical_provider(
    provider_id: int,
    provider_data: MedicalProviderUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a medical provider
    """
    try:
        # Check if provider exists and belongs to family
        existing_provider = await database.fetch_one(
            medical_providers.select().where(
                and_(
                    medical_providers.c.id == provider_id,
                    medical_providers.c.family_id == current_user["family_id"]
                )
            )
        )
        
        if not existing_provider:
            raise HTTPException(status_code=404, detail="Medical provider not found")
        
        # Prepare update data
        update_data = provider_data.dict(exclude_unset=True)
        
        # Geocode address if provided and coordinates not provided
        if update_data.get("address") and not (update_data.get("latitude") and update_data.get("longitude")):
            coords = location_service.geocode_address(update_data["address"])
            if coords:
                update_data["latitude"], update_data["longitude"] = coords
        
        # Extract ZIP code if address provided and ZIP not provided
        if update_data.get("address") and not update_data.get("zip_code"):
            zip_code = location_service.extract_zip_code(update_data["address"])
            if zip_code:
                update_data["zip_code"] = zip_code
        
        # Format phone number if provided
        if update_data.get("phone"):
            update_data["phone"] = location_service.format_phone_number(update_data["phone"])
        
        # Set updated timestamp
        update_data["updated_at"] = datetime.now()
        
        # Update database
        await database.execute(
            medical_providers.update().where(
                medical_providers.c.id == provider_id
            ).values(**update_data)
        )
        
        # Get updated provider
        updated_provider = await database.fetch_one(
            medical_providers.select().where(medical_providers.c.id == provider_id)
        )
        
        return MedicalProviderResponse(**dict(updated_provider))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating medical provider: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{provider_id}")
async def delete_medical_provider(
    provider_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a medical provider
    """
    try:
        # Check if provider exists and belongs to family
        existing_provider = await database.fetch_one(
            medical_providers.select().where(
                and_(
                    medical_providers.c.id == provider_id,
                    medical_providers.c.family_id == current_user["family_id"]
                )
            )
        )
        
        if not existing_provider:
            raise HTTPException(status_code=404, detail="Medical provider not found")
        
        # Delete from database
        await database.execute(
            medical_providers.delete().where(
                medical_providers.c.id == provider_id
            )
        )
        
        return {"success": True, "message": "Medical provider deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting medical provider: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/search", response_model=MedicalProviderListResponse)
async def search_medical_providers(
    q: Optional[str] = Query(None, description="Search query"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    radius: float = Query(25.0, gt=0, le=100, description="Search radius in miles"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort by: name, distance, created_at"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search medical providers by location or name
    """
    try:
        # Build base query
        query = medical_providers.select().where(
            medical_providers.c.family_id == current_user["family_id"]
        )
        
        # Apply text search
        if q:
            search_filter = or_(
                medical_providers.c.name.ilike(f"%{q}%"),
                medical_providers.c.specialty.ilike(f"%{q}%"),
                medical_providers.c.address.ilike(f"%{q}%")
            )
            query = query.where(search_filter)
        
        # Apply specialty filter
        if specialty:
            query = query.where(
                medical_providers.c.specialty.ilike(f"%{specialty}%")
            )
        
        # Get all matching providers
        providers = await database.fetch_all(query)
        
        # Convert to list of dictionaries
        provider_list = []
        for provider in providers:
            provider_dict = dict(provider)
            provider_list.append(provider_dict)
        
        # Apply location-based filtering and distance calculation
        if lat is not None and lng is not None:
            provider_list = location_service.search_providers_by_location(
                provider_list, lat, lng, radius
            )
        
        # Apply sorting
        if sort_by == "distance" and lat is not None and lng is not None:
            provider_list.sort(key=lambda x: x.get('distance', float('inf')))
            if sort_order.lower() == "desc":
                provider_list.reverse()
        elif sort_by == "name":
            provider_list.sort(key=lambda x: x.get('name', ''))
            if sort_order.lower() == "desc":
                provider_list.reverse()
        elif sort_by == "created_at":
            provider_list.sort(key=lambda x: x.get('created_at', datetime.min))
            if sort_order.lower() == "desc":
                provider_list.reverse()
        
        # Apply pagination
        total = len(provider_list)
        offset = (page - 1) * limit
        paginated_providers = provider_list[offset:offset + limit]
        
        # Convert to response format
        response_providers = []
        for provider in paginated_providers:
            response_providers.append(MedicalProviderResponse(**provider))
        
        total_pages = (total + limit - 1) // limit
        
        return MedicalProviderListResponse(
            providers=response_providers,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching medical providers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/search", response_model=MedicalProviderListResponse)
async def search_medical_providers_post(
    search_data: MedicalSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search medical providers by location with POST request
    """
    try:
        # Convert radius from meters to miles for consistency with GET endpoint
        radius_miles = search_data.radius / 1609.34 if search_data.radius else 25.0
        
        # Build base query
        query = medical_providers.select().where(
            medical_providers.c.family_id == current_user["family_id"]
        )
        
        # Apply text search if provided
        if search_data.query:
            search_filter = or_(
                medical_providers.c.name.ilike(f"%{search_data.query}%"),
                medical_providers.c.specialty.ilike(f"%{search_data.query}%"),
                medical_providers.c.address.ilike(f"%{search_data.query}%")
            )
            query = query.where(search_filter)
        
        # Apply specialty filter if provided
        if search_data.specialty:
            query = query.where(
                medical_providers.c.specialty.ilike(f"%{search_data.specialty}%")
            )
        
        # Get all matching providers
        providers = await database.fetch_all(query)
        
        # Convert to list of dictionaries
        provider_list = []
        for provider in providers:
            provider_dict = dict(provider)
            provider_list.append(provider_dict)
        
        # Apply location-based filtering and distance calculation
        if search_data.latitude is not None and search_data.longitude is not None:
            provider_list = location_service.search_providers_by_location(
                provider_list, search_data.latitude, search_data.longitude, radius_miles
            )
            # Sort by distance by default when location is provided
            provider_list.sort(key=lambda x: x.get('distance', float('inf')))
        
        # For now, return all results without pagination (can be enhanced later)
        # Convert to response format
        response_providers = []
        for provider in provider_list:
            response_providers.append(MedicalProviderResponse(**provider))
        
        total = len(response_providers)
        
        return MedicalProviderListResponse(
            providers=response_providers,
            total=total,
            page=1,
            limit=total,
            total_pages=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching medical providers (POST): {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 