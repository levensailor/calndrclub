# Daycare Events Caching Issue - Fix Guide

## Problem Analysis

You've removed all daycare syncs from the backend but daycare events still appear in your iOS calendar. Here's what's happening:

### Root Cause
1. **Daycare events are NOT stored in the backend database** - they're only parsed and returned
2. **iOS app is caching the events locally** - likely in UserDefaults or in-memory cache  
3. **School events ARE stored in database** - different system entirely
4. **Signing out/in doesn't clear the cache** - cache survives authentication changes

### Evidence from Code Review
- `parse_daycare_events` endpoint only returns events, doesn't store them
- School events use `get_school_events()` to store in database
- iOS `CalendarViewModel.resetData()` doesn't clear daycare events cache
- No daycare events table in database schema

## Fix Options

### Option 1: Quick Fix - Clear iOS App Cache (IMMEDIATE)

Force the iOS app to clear its local cache:

```swift
// In CalendarViewModel.swift resetData() method, add:
func resetData() {
    print("Resetting all local data.")
    isDataLoaded = false
    events = []
    custodyRecords = []
    schoolEvents = []
    weatherData = [:]
    
    // ADD THIS LINE to clear daycare events cache:
    UserDefaults.standard.removeObject(forKey: "cachedDaycareEvents")
    UserDefaults.standard.removeObject(forKey: "daycareEventsCache") 
    UserDefaults.standard.removeObject(forKey: "lastDaycareSyncDate")
    
    // Reset family data
    coparents = []
    children = []
    otherFamilyMembers = []
    daycareProviders = []
    // ... rest of existing code
}
```

Then force logout/login or delete and reinstall the app.

### Option 2: Check for iOS Cache Keys (INVESTIGATE)

Search for where daycare events might be cached:

```bash
# Search iOS codebase for cache keys
grep -r "daycare.*cache\|cache.*daycare" ios/calndr/calndr/
grep -r "UserDefaults.*daycare\|daycare.*UserDefaults" ios/calndr/calndr/
grep -r "DaycareEvent" ios/calndr/calndr/
```

### Option 3: Backend Database Check (VERIFY)

Confirm no daycare events in database:

```sql
-- Check for any daycare-related events
SELECT * FROM events WHERE content ILIKE '%daycare%' OR event_type = 'daycare';

-- Check daycare calendar syncs
SELECT * FROM daycare_calendar_syncs WHERE sync_enabled = true;

-- Check for events with specific position that might be daycare
SELECT * FROM events WHERE position = 5 OR position > 4;
```

### Option 4: Add Daycare Events Clear API (PERMANENT FIX)

Create an endpoint to clear daycare events:

```python
# In backend/api/v1/endpoints/daycare_providers.py
@router.delete("/events/clear")
async def clear_all_daycare_events(current_user = Depends(get_current_user)):
    """Clear all daycare events for the current family."""
    try:
        # Delete any events that might be daycare-related
        delete_query = events.delete().where(
            (events.c.family_id == current_user['family_id']) &
            (events.c.event_type == 'daycare')
        )
        result = await database.execute(delete_query)
        
        return {"message": f"Cleared daycare events", "deleted_count": result}
    except Exception as e:
        logger.error(f"Error clearing daycare events: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear daycare events")
```

### Option 5: Fix iOS Event Display Logic (ARCHITECTURAL)

Modify iOS to only show events from database, not cached parsing results:

```swift
// In DayContentView.swift or CalendarGridView.swift
// Remove any logic that displays cached daycare events
// Only display events from viewModel.eventsForDate() which comes from backend
```

## Recommended Solution

**Try Option 1 first** (clear iOS cache) as it's the quickest fix. If that doesn't work:

1. **Delete and reinstall the iOS app** - this will clear all local storage
2. **Check backend database** using Option 3 to confirm no daycare events stored
3. **Implement Option 4** to add a clear endpoint for future use

## Prevention

To prevent this in the future:

1. **Store daycare events in database** like school events do
2. **Clear caches on provider deletion** 
3. **Add cache invalidation** when sync configs are disabled
4. **Use consistent event storage** across all event types

## Testing the Fix

After applying the fix:

1. Check that no daycare events appear in calendar
2. Add a new daycare and sync - events should appear
3. Remove the daycare - events should disappear immediately
4. Sign out/in - events should stay cleared

## Emergency Reset Command

If all else fails, you can reset the entire iOS app state:

```swift
// Add this to a debug menu or run in Xcode console
UserDefaults.standard.removePersistentDomain(forName: Bundle.main.bundleIdentifier!)
```

This will clear ALL app preferences and force a complete re-sync. 