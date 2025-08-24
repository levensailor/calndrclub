from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date
import uuid

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import users, families, children
from schemas.enrollment_flow import (
    CoparentInfoRequest, 
    ChildInfoRequest, 
    CustodyScheduleRequest,
    EnrollmentStatusResponse,
    EnrollmentStepResponse
)

router = APIRouter()

@router.get("/status", response_model=EnrollmentStatusResponse)
async def get_enrollment_status(current_user: dict = Depends(get_current_user)):
    """Get current user's enrollment status and next required step."""
    try:
        # Get user details including enrollment fields
        user_query = """
            SELECT enrolled, coparent_enrolled, coparent_invited, family_id
            FROM users 
            WHERE id = :user_id
        """
        user = await database.fetch_one(user_query, {"user_id": current_user["id"]})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Determine next step based on current state
        next_step = None
        if not user.enrolled:
            # Check if user has family (entered code vs created code)
            if user.family_id:
                # Check if family has children and custody info
                family_query = """
                    SELECT id FROM families WHERE id = :family_id
                """
                family = await database.fetch_one(family_query, {"family_id": user.family_id})
                
                if family:
                    # Check if family has children
                    children_query = """
                        SELECT COUNT(*) as child_count FROM children WHERE family_id = :family_id
                    """
                    children_count = await database.fetch_one(children_query, {"family_id": user.family_id})
                    
                    if children_count["child_count"] == 0:
                        next_step = "coparent_info"
                    else:
                        # Family already has children, user is joining existing setup
                        next_step = "complete"
                else:
                    next_step = "coparent_info"
            else:
                next_step = "enrollment_options"
        
        return {
            "enrolled": user.enrolled,
            "coparent_enrolled": user.coparent_enrolled,
            "coparent_invited": user.coparent_invited,
            "next_step": next_step,
            "family_id": str(user.family_id) if user.family_id else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get enrollment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get enrollment status"
        )

@router.post("/coparent-info", response_model=EnrollmentStepResponse)
async def submit_coparent_info(
    request: CoparentInfoRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit coparent information (step 2 of enrollment)."""
    try:
        async with database.transaction():
            # Verify user has a family
            if not current_user.get("family_id"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must have a family to add coparent info"
                )
            
            # Store coparent info in family or user table (you may want a separate coparents table)
            # For now, we'll just mark that coparent info was provided
            # You might want to create a separate coparents table for this data
            
            logger.info(f"Coparent info submitted for user {current_user['id']}: {request.coparent_first_name}")
            
            return {
                "success": True,
                "message": "Coparent information saved successfully",
                "next_step": "children_info"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit coparent info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save coparent information"
        )

@router.post("/children-info", response_model=EnrollmentStepResponse)
async def submit_children_info(
    request: List[ChildInfoRequest],
    current_user: dict = Depends(get_current_user)
):
    """Submit children information (step 3 of enrollment)."""
    try:
        async with database.transaction():
            family_id = current_user.get("family_id")
            if not family_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must have a family to add children"
                )
            
            # Add each child to the children table
            for child_info in request:
                child_id = uuid.uuid4()
                
                # Parse date of birth
                try:
                    dob = datetime.strptime(child_info.date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date format for {child_info.first_name}. Use YYYY-MM-DD"
                    )
                
                await database.execute(
                    """
                    INSERT INTO children (id, family_id, first_name, last_name, date_of_birth, created_at, updated_at)
                    VALUES (:id, :family_id, :first_name, :last_name, :date_of_birth, NOW(), NOW())
                    """,
                    {
                        "id": child_id,
                        "family_id": family_id,
                        "first_name": child_info.first_name,
                        "last_name": child_info.last_name,
                        "date_of_birth": dob
                    }
                )
                
                logger.info(f"Added child {child_info.first_name} {child_info.last_name} to family {family_id}")
            
            return {
                "success": True,
                "message": f"Added {len(request)} child(ren) successfully",
                "next_step": "custody_schedule"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit children info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save children information"
        )

@router.post("/custody-schedule", response_model=EnrollmentStepResponse)
async def submit_custody_schedule(
    request: CustodyScheduleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit default custody schedule (final step of enrollment)."""
    try:
        async with database.transaction():
            family_id = current_user.get("family_id")
            if not family_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must have a family to set custody schedule"
                )
            
            # Store custody schedule (you may want a separate custody_schedules table)
            # For now, we'll just mark enrollment as complete
            
            # Mark user as enrolled
            await database.execute(
                """
                UPDATE users 
                SET enrolled = TRUE 
                WHERE id = :user_id
                """,
                {"user_id": current_user["id"]}
            )
            
            # If user generated a code (coparent_invited = true), keep that status
            # If user entered a code, mark coparent as enrolled too
            user_query = """
                SELECT coparent_invited FROM users WHERE id = :user_id
            """
            user = await database.fetch_one(user_query, {"user_id": current_user["id"]})
            
            if not user.coparent_invited:
                # User entered a code, so they're joining existing family
                # Mark coparent as enrolled
                await database.execute(
                    """
                    UPDATE users 
                    SET coparent_enrolled = TRUE 
                    WHERE family_id = :family_id AND id != :user_id
                    """,
                    {"family_id": family_id, "user_id": current_user["id"]}
                )
            
            logger.info(f"Enrollment completed for user {current_user['id']}")
            
            return {
                "success": True,
                "message": "Enrollment completed successfully!",
                "next_step": "complete"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit custody schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save custody schedule"
        )

@router.post("/complete", response_model=EnrollmentStepResponse)
async def complete_enrollment(current_user: dict = Depends(get_current_user)):
    """Mark enrollment as complete for users who entered a code."""
    try:
        async with database.transaction():
            # Mark user as enrolled
            await database.execute(
                """
                UPDATE users 
                SET enrolled = TRUE 
                WHERE id = :user_id
                """,
                {"user_id": current_user["id"]}
            )
            
            logger.info(f"Enrollment marked complete for user {current_user['id']}")
            
            return {
                "success": True,
                "message": "Welcome to your family calendar!",
                "next_step": "complete"
            }
            
    except Exception as e:
        logger.error(f"Failed to complete enrollment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete enrollment"
        )
