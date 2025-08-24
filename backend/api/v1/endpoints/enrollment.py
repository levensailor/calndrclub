from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import random
import string
from datetime import datetime, timedelta
import uuid

from core.database import database
from core.security import get_current_user
from db.models import users, families
from schemas.enrollment import EnrollmentCodeCreate, EnrollmentCodeResponse, EnrollmentCodeValidate

router = APIRouter()

def generate_enrollment_code() -> str:
    """Generate a 6-character alphanumeric enrollment code"""
    characters = string.ascii_uppercase + string.digits
    # Exclude confusing characters like 0, O, I, 1
    characters = characters.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    return ''.join(random.choices(characters, k=6))

@router.post("/create-code", response_model=EnrollmentCodeResponse)
async def create_enrollment_code(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new enrollment code for family linking.
    This is used by the first parent to generate a code for their co-parent.
    """
    try:
        # Check if user already has a family
        if current_user.get("family_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already belongs to a family"
            )
        
        async with database.transaction():
            # Create a new family for this user
            family_id = uuid.uuid4()
            family_name = f"{current_user.get('last_name', 'Family')} Family"
            
            family_insert = families.insert().values(
                id=family_id,
                name=family_name,
                created_by_user_id=current_user["id"]
            )
            await database.execute(family_insert)
            
            # Update user's family_id
            user_update = users.update().where(users.c.id == current_user["id"]).values(
                family_id=family_id
            )
            await database.execute(user_update)
            
            # Generate unique enrollment code
            max_attempts = 10
            for attempt in range(max_attempts):
                code = generate_enrollment_code()
                
                # Check if code already exists
                existing_code = await database.fetch_one(
                    "SELECT id FROM enrollment_codes WHERE code = :code AND expires_at > NOW()",
                    {"code": code}
                )
                
                if not existing_code:
                    break
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate unique enrollment code"
                )
            
            # Create enrollment code record
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            await database.execute(
                """
                INSERT INTO enrollment_codes (code, family_id, created_by_user_id, expires_at, created_at, updated_at)
                VALUES (:code, :family_id, :created_by_user_id, :expires_at, NOW(), NOW())
                """,
                {
                    "code": code,
                    "family_id": family_id,
                    "created_by_user_id": current_user["id"],
                    "expires_at": expires_at
                }
            )
            
            return {
                "success": True,
                "message": "Enrollment code created successfully",
                "enrollment_code": code,
                "family_id": str(family_id)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create enrollment code: {str(e)}"
        )

@router.post("/validate-code", response_model=EnrollmentCodeResponse)
async def validate_enrollment_code(
    request: EnrollmentCodeValidate,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate an enrollment code and prepare for family linking.
    This is used by the second parent to join an existing family.
    """
    try:
        # Check if user already has a family
        if current_user.get("family_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already belongs to a family"
            )
        
        # Find the enrollment code
        code_record = await database.fetch_one(
            """
            SELECT ec.id, ec.family_id, ec.created_by_user_id, ec.is_used, ec.expires_at,
                   f.id as family_exists
            FROM enrollment_codes ec
            LEFT JOIN families f ON ec.family_id = f.id
            WHERE ec.code = :code
            """,
            {"code": request.code.upper()}
        )
        
        if not code_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid enrollment code"
            )
        
        # Check if code is expired
        if code_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enrollment code has expired"
            )
        
        # Check if code is already used
        if code_record.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enrollment code has already been used"
            )
        
        # Check if family still exists
        if not code_record.family_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Associated family no longer exists"
            )
        
        # Check if user is trying to use their own code
        if code_record.created_by_user_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot use your own enrollment code"
            )
        
        return {
            "success": True,
            "message": "Enrollment code is valid",
            "enrollment_code": request.code.upper(),
            "family_id": str(code_record.family_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate enrollment code: {str(e)}"
        )

@router.post("/use-code")
async def use_enrollment_code(
    request: EnrollmentCodeValidate,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Use an enrollment code to join a family.
    This should be called during the registration process.
    """
    try:
        # Validate the code first
        validation_result = await validate_enrollment_code(request, current_user)
        
        if not validation_result["success"]:
            return validation_result
        
        family_id = validation_result["family_id"]
        
        async with database.transaction():
            # Update user's family_id
            user_update = users.update().where(users.c.id == current_user["id"]).values(
                family_id=family_id
            )
            await database.execute(user_update)
            
            # Mark the enrollment code as used
            await database.execute(
                """
                UPDATE enrollment_codes 
                SET is_used = TRUE, used_by_user_id = :user_id, updated_at = NOW()
                WHERE code = :code
                """,
                {"user_id": current_user["id"], "code": request.code.upper()}
            )
            
            return {
                "success": True,
                "message": "Successfully joined family",
                "family_id": family_id
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to use enrollment code: {str(e)}"
        )
