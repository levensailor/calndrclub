from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
from datetime import datetime, timezone

from core.database import database
from core.security import get_current_user
from db.models import themes, user_preferences
from schemas import theme as theme_schema

router = APIRouter()

@router.post("/", response_model=theme_schema.Theme)
async def create_theme(theme: theme_schema.ThemeCreate, current_user = Depends(get_current_user)):
    theme_id = uuid.uuid4()
    insert_query = themes.insert().values(
        id=theme_id,
        name=theme.name,
        mainBackgroundColor=theme.mainBackgroundColor,
        secondaryBackgroundColor=theme.secondaryBackgroundColor,
        textColor=theme.textColor,
        headerTextColor=theme.headerTextColor,
        iconColor=theme.iconColor,
        iconActiveColor=theme.iconActiveColor,
        accentColor=theme.accentColor,
        parentOneColor=theme.parentOneColor,
        parentTwoColor=theme.parentTwoColor,
        is_public=theme.is_public,
        created_by_user_id=current_user['id'],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    await database.execute(insert_query)
    
    # Fetch the created theme
    select_query = themes.select().where(themes.c.id == theme_id)
    db_theme = await database.fetch_one(select_query)
    
    return theme_schema.Theme(
        id=db_theme['id'],
        name=db_theme['name'],
        mainBackgroundColor=db_theme['mainBackgroundColor'],
        secondaryBackgroundColor=db_theme['secondaryBackgroundColor'],
        textColor=db_theme['textColor'],
        headerTextColor=db_theme['headerTextColor'],
        iconColor=db_theme['iconColor'],
        iconActiveColor=db_theme['iconActiveColor'],
        accentColor=db_theme['accentColor'],
        parentOneColor=db_theme['parentOneColor'],
        parentTwoColor=db_theme['parentTwoColor'],
        is_public=db_theme['is_public'],
        created_by_user_id=db_theme['created_by_user_id'],
        created_at=db_theme['created_at'],
        updated_at=db_theme['updated_at']
    )

@router.get("/", response_model=List[theme_schema.Theme])
async def get_themes(current_user = Depends(get_current_user)):
    query = themes.select().where(
        (themes.c.is_public == True) | 
        (themes.c.created_by_user_id == current_user['id'])
    )
    
    db_themes = await database.fetch_all(query)
    
    return [
        theme_schema.Theme(
            id=theme['id'],
            name=theme['name'],
            mainBackgroundColor=theme['mainBackgroundColor'],
            secondaryBackgroundColor=theme['secondaryBackgroundColor'],
            textColor=theme['textColor'],
            headerTextColor=theme['headerTextColor'],
            iconColor=theme['iconColor'],
            iconActiveColor=theme['iconActiveColor'],
            accentColor=theme['accentColor'],
            parentOneColor=theme['parentOneColor'],
            parentTwoColor=theme['parentTwoColor'],
            is_public=theme['is_public'],
            created_by_user_id=theme['created_by_user_id'],
            created_at=theme['created_at'],
            updated_at=theme['updated_at']
        )
        for theme in db_themes
    ]

@router.put("/{theme_id}", response_model=theme_schema.Theme)
async def update_theme(theme_id: uuid.UUID, theme: theme_schema.ThemeUpdate, current_user = Depends(get_current_user)):
    # Check if theme exists and user has permission
    select_query = themes.select().where(themes.c.id == theme_id)
    db_theme = await database.fetch_one(select_query)
    
    if db_theme is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    if db_theme['created_by_user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to update this theme")
    
    # Build update data
    update_data = theme.dict(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc)
    
    # Update the theme
    update_query = themes.update().where(themes.c.id == theme_id).values(**update_data)
    await database.execute(update_query)
    
    # Fetch the updated theme
    updated_theme = await database.fetch_one(select_query)
    
    return theme_schema.Theme(
        id=updated_theme['id'],
        name=updated_theme['name'],
        mainBackgroundColor=updated_theme['mainBackgroundColor'],
        secondaryBackgroundColor=updated_theme['secondaryBackgroundColor'],
        textColor=updated_theme['textColor'],
        headerTextColor=updated_theme['headerTextColor'],
        iconColor=updated_theme['iconColor'],
        iconActiveColor=updated_theme['iconActiveColor'],
        accentColor=updated_theme['accentColor'],
        parentOneColor=updated_theme['parentOneColor'],
        parentTwoColor=updated_theme['parentTwoColor'],
        is_public=updated_theme['is_public'],
        created_by_user_id=updated_theme['created_by_user_id'],
        created_at=updated_theme['created_at'],
        updated_at=updated_theme['updated_at']
    )

@router.delete("/{theme_id}", status_code=204)
async def delete_theme(theme_id: uuid.UUID, current_user = Depends(get_current_user)):
    # Check if theme exists and user has permission
    select_query = themes.select().where(themes.c.id == theme_id)
    db_theme = await database.fetch_one(select_query)
    
    if db_theme is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    if db_theme['created_by_user_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this theme")
    
    # Delete the theme
    delete_query = themes.delete().where(themes.c.id == theme_id)
    await database.execute(delete_query)

@router.put("/set-preference/{theme_id}", status_code=204)
async def set_theme_preference(theme_id: uuid.UUID, current_user = Depends(get_current_user)):
    # First, validate that the theme exists and is accessible to the user
    theme_query = themes.select().where(
        (themes.c.id == theme_id) & 
        ((themes.c.is_public == True) | (themes.c.created_by_user_id == current_user['id']))
    )
    theme_exists = await database.fetch_one(theme_query)
    
    if theme_exists is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Theme with ID {theme_id} not found or not accessible"
        )
    
    # Check if user preferences record exists
    prefs_query = user_preferences.select().where(user_preferences.c.user_id == current_user['id'])
    user_prefs = await database.fetch_one(prefs_query)
    
    if user_prefs is None:
        # Create new user preferences record
        insert_query = user_preferences.insert().values(
            user_id=current_user['id'],
            selected_theme_id=theme_id
        )
        await database.execute(insert_query)
    else:
        # Update existing user preferences
        update_query = user_preferences.update().where(
            user_preferences.c.user_id == current_user['id']
        ).values(selected_theme_id=theme_id)
        await database.execute(update_query) 