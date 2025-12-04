"""
Custody maintenance endpoints for diagnosing and fixing data integrity issues.
These endpoints are only available to authenticated users for their own family data.
"""

from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.database import database
from core.security import get_current_user
from core.logging import logger
from db.models import custody, users

router = APIRouter()

class CustodyIntegrityReport(BaseModel):
    """Report of custody data integrity issues."""
    total_records: int
    valid_records: int
    mismatched_records: int
    mismatched_dates: List[str]
    family_members: List[dict]
    fixes_applied: int

class CustodyMismatch(BaseModel):
    """Details of a custody record with mismatched custodian."""
    date: str
    custody_id: str
    invalid_custodian_id: str
    invalid_custodian_name: Optional[str]
    suggested_custodian_id: Optional[str]
    suggested_custodian_name: Optional[str]

@router.get("/integrity-check", response_model=CustodyIntegrityReport)
async def check_custody_integrity(current_user = Depends(get_current_user)):
    """
    Check custody records for data integrity issues.
    Returns a report of any records with custodian IDs that don't belong to the family.
    """
    family_id = current_user['family_id']
    logger.info(f"Running custody integrity check for family {family_id}")
    
    try:
        # Get all family members
        family_members_query = users.select().where(
            (users.c.family_id == family_id) &
            (users.c.status == 'active')
        ).order_by(users.c.created_at.asc())
        
        family_members_data = await database.fetch_all(family_members_query)
        valid_custodian_ids = [str(member['id']) for member in family_members_data]
        
        family_members = [
            {
                "id": str(member['id']),
                "name": f"{member['first_name']} {member['last_name']}",
                "email": member['email']
            }
            for member in family_members_data
        ]
        
        # Get all custody records for the family
        custody_query = custody.select().where(
            custody.c.family_id == family_id
        ).order_by(custody.c.date.asc())
        
        custody_records = await database.fetch_all(custody_query)
        total_records = len(custody_records)
        
        # Check for mismatches
        mismatched_records = []
        mismatched_dates = []
        
        for record in custody_records:
            custodian_id = str(record['custodian_id'])
            if custodian_id not in valid_custodian_ids:
                mismatched_records.append(record)
                mismatched_dates.append(str(record['date']))
                
        valid_records = total_records - len(mismatched_records)
        
        logger.info(f"Integrity check complete: {len(mismatched_records)} mismatches found out of {total_records} records")
        
        return CustodyIntegrityReport(
            total_records=total_records,
            valid_records=valid_records,
            mismatched_records=len(mismatched_records),
            mismatched_dates=mismatched_dates,
            family_members=family_members,
            fixes_applied=0
        )
        
    except Exception as e:
        logger.error(f"Error checking custody integrity: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking custody integrity: {str(e)}")

@router.get("/mismatches", response_model=List[CustodyMismatch])
async def get_custody_mismatches(
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """
    Get detailed information about custody records with mismatched custodian IDs.
    """
    family_id = current_user['family_id']
    
    try:
        # Get valid family member IDs
        family_members_query = users.select().where(
            (users.c.family_id == family_id) &
            (users.c.status == 'active')
        ).order_by(users.c.created_at.asc())
        
        family_members_data = await database.fetch_all(family_members_query)
        valid_custodian_ids = [str(member['id']) for member in family_members_data]
        custodian_names = {
            str(member['id']): member['first_name'] 
            for member in family_members_data
        }
        
        # Find mismatched custody records
        custody_query = """
        SELECT 
            c.id,
            c.date,
            c.custodian_id,
            u.first_name as custodian_name,
            u.family_id as custodian_family_id
        FROM custody c
        LEFT JOIN users u ON u.id = c.custodian_id
        WHERE c.family_id = :family_id
        ORDER BY c.date DESC
        LIMIT :limit
        """
        
        custody_records = await database.fetch_all(custody_query, {
            'family_id': family_id,
            'limit': limit
        })
        
        mismatches = []
        for record in custody_records:
            custodian_id = str(record['custodian_id'])
            if custodian_id not in valid_custodian_ids:
                # Determine suggested custodian based on pattern
                suggested_id = None
                suggested_name = None
                
                if len(valid_custodian_ids) == 2:
                    # Check previous day's custody
                    prev_date = record['date'] - timedelta(days=1)
                    prev_query = custody.select().where(
                        (custody.c.family_id == family_id) &
                        (custody.c.date == prev_date)
                    )
                    prev_record = await database.fetch_one(prev_query)
                    
                    if prev_record and str(prev_record['custodian_id']) in valid_custodian_ids:
                        # Suggest alternating from previous day
                        prev_id = str(prev_record['custodian_id'])
                        if prev_id == valid_custodian_ids[0]:
                            suggested_id = valid_custodian_ids[1]
                        else:
                            suggested_id = valid_custodian_ids[0]
                    else:
                        # Default to first parent
                        suggested_id = valid_custodian_ids[0]
                    
                    suggested_name = custodian_names.get(suggested_id)
                
                mismatches.append(CustodyMismatch(
                    date=str(record['date']),
                    custody_id=str(record['id']),
                    invalid_custodian_id=custodian_id,
                    invalid_custodian_name=record['custodian_name'],
                    suggested_custodian_id=suggested_id,
                    suggested_custodian_name=suggested_name
                ))
        
        logger.info(f"Found {len(mismatches)} custody mismatches for family {family_id}")
        return mismatches
        
    except Exception as e:
        logger.error(f"Error getting custody mismatches: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting custody mismatches: {str(e)}")

@router.post("/fix-mismatches")
async def fix_custody_mismatches(
    dry_run: bool = True,
    current_user = Depends(get_current_user)
):
    """
    Fix custody records with mismatched custodian IDs.
    Set dry_run=false to actually apply the fixes.
    """
    family_id = current_user['family_id']
    logger.info(f"Fixing custody mismatches for family {family_id} (dry_run={dry_run})")
    
    try:
        # Get valid family member IDs
        family_members_query = users.select().where(
            (users.c.family_id == family_id) &
            (users.c.status == 'active')
        ).order_by(users.c.created_at.asc())
        
        family_members_data = await database.fetch_all(family_members_query)
        valid_custodian_ids = [str(member['id']) for member in family_members_data]
        
        if len(valid_custodian_ids) != 2:
            return {
                "error": f"Cannot auto-fix: Family has {len(valid_custodian_ids)} active members (need exactly 2)",
                "fixes_applied": 0
            }
        
        # Find and fix mismatched records
        custody_query = custody.select().where(
            custody.c.family_id == family_id
        ).order_by(custody.c.date.asc())
        
        custody_records = await database.fetch_all(custody_query)
        fixes_applied = 0
        fixes_preview = []
        
        for record in custody_records:
            custodian_id = str(record['custodian_id'])
            if custodian_id not in valid_custodian_ids:
                # Determine correct custodian
                prev_date = record['date'] - timedelta(days=1)
                prev_query = custody.select().where(
                    (custody.c.family_id == family_id) &
                    (custody.c.date == prev_date)
                )
                prev_record = await database.fetch_one(prev_query)
                
                new_custodian_id = None
                if prev_record and str(prev_record['custodian_id']) in valid_custodian_ids:
                    # Alternate from previous day
                    prev_id = str(prev_record['custodian_id'])
                    if prev_id == valid_custodian_ids[0]:
                        new_custodian_id = valid_custodian_ids[1]
                    else:
                        new_custodian_id = valid_custodian_ids[0]
                else:
                    # Default to first parent
                    new_custodian_id = valid_custodian_ids[0]
                
                fixes_preview.append({
                    "date": str(record['date']),
                    "old_custodian_id": custodian_id,
                    "new_custodian_id": new_custodian_id
                })
                
                if not dry_run:
                    # Apply the fix
                    update_query = custody.update().where(
                        custody.c.id == record['id']
                    ).values(
                        custodian_id=new_custodian_id,
                        updated_at=datetime.utcnow()
                    )
                    await database.execute(update_query)
                    fixes_applied += 1
        
        if dry_run:
            return {
                "message": "Dry run complete - no changes made",
                "fixes_preview": fixes_preview,
                "total_fixes_needed": len(fixes_preview)
            }
        else:
            # Clear cache after fixes
            from services.redis_service import redis_service
            await redis_service.clear_family_cache(family_id)
            
            return {
                "message": f"Successfully fixed {fixes_applied} custody records",
                "fixes_applied": fixes_applied
            }
            
    except Exception as e:
        logger.error(f"Error fixing custody mismatches: {e}")
        raise HTTPException(status_code=500, detail=f"Error fixing custody mismatches: {str(e)}")
