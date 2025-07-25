# API Analysis Report: iOS Swift App & Python Backend Data Flow Issues

## Executive Summary

After analyzing the data flow between your Swift iOS app and Python FastAPI backend, I've identified **7 critical failure points** that could cause API calls to fail. These issues range from missing endpoints to data type mismatches and inconsistent field naming conventions.

## 🚨 Critical Issues Identified

### 1. **MISSING API ENDPOINT: School Events**
**Severity: HIGH** 
**Status: Will cause 404 errors**

**Problem:**
- iOS app calls: `GET /api/school-events`  
- Backend: **Endpoint does not exist**

**Simulated Failure:**
```swift
// iOS app makes this call:
APIService.shared.fetchSchoolEvents { result in
    // This will fail with 404 Not Found
}
```

**Backend Response:**
```
HTTP 404 Not Found
{"detail": "Not Found"}
```

**Remedies:**

**Option A: Implement School Events API (Recommended)**
```python
@app.get("/api/school-events")
async def get_school_events(current_user: User = Depends(get_current_user)):
    # Use the existing test.py scraping logic
    events = scrape_school_events()  # From test.py
    return [{"date": date, "title": event} for date, event in events.items()]
```

**Option B: Return Empty Array (Quick Fix)**
```python
@app.get("/api/school-events")
async def get_school_events(current_user: User = Depends(get_current_user)):
    return []  # Empty array to prevent crashes
```

### 2. **DATA TYPE MISMATCH: UUID vs String**
**Severity: HIGH**
**Status: Silent failures and data corruption**

**Problem:**
- Backend database uses `UUID(as_uuid=True)` for user IDs
- iOS app expects and sends `String` for custodian IDs
- API returns UUIDs as strings but iOS string comparisons may fail

**Database Schema:**
```sql
users.id = UUID(as_uuid=True)  -- Python uuid.UUID object
custody.custodian_id = UUID(as_uuid=True)  -- Python uuid.UUID object
```

**iOS Expectation:**
```swift
struct Custodian: Codable {
    let id: String  // Expects string, not UUID
    let first_name: String
}
```

**Simulated Failure:**
```python
# Backend returns:
{
    "custodian_one": {
        "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID as string
        "first_name": "Jeff"
    }
}

# iOS comparison fails due to UUID formatting inconsistencies:
if custodyRecord.content.lowercased() == self.custodianOneName.lowercased() {
    return (self.custodianOne?.id ?? "", self.custodianOneName)  // May not match!
}
```

**Remedies:**

**Option A: Standardize UUID String Format (Recommended)**
```python
# In backend, ensure consistent UUID string format:
return {
    "custodian_one": {
        "id": str(family_members[0]['id']).lower(),  # Force lowercase
        "first_name": family_members[0]['first_name']
    }
}
```

**Option B: Use UUID Type in iOS (Major Change)**
```swift
import Foundation

struct Custodian: Codable {
    let id: UUID  // Change to UUID type
    let first_name: String
}
```

### 3. **INCONSISTENT RESPONSE FORMATS: Custody API**
**Severity: MEDIUM**
**Status: Potential decoding failures**

**Problem:**
- Backend Pydantic model expects different fields than what it returns
- Field name inconsistencies between request/response models

**Backend Model Mismatch:**
```python
# Request model
class CustodyRecord(BaseModel):
    date: date  # Python date object
    custodian_id: uuid.UUID

# Response model  
class CustodyResponse(BaseModel):
    id: int
    date: str  # String, not date!
    custodian_id: str
    custodian_name: str

# But actual API returns:
{
    'id': record['id'],
    'event_date': str(record['date']),  # Different field name!
    'content': custodian_name,          # Different field name!
    'position': 4
}
```

**iOS Expects:**
```swift
struct CustodyResponse: Codable {
    let id: Int
    let event_date: String  // Matches API response
    let content: String     // Matches API response  
    let position: Int       // Matches API response
}
```

**Remedies:**

**Option A: Fix Backend Model (Recommended)**
```python
class CustodyResponse(BaseModel):
    id: int
    event_date: str  # Match actual response
    content: str     # Match actual response
    position: int    # Match actual response
```

**Option B: Fix API Response to Match Model**
```python
return {
    'id': final_record['id'],
    'date': str(final_record['date']),
    'custodian_id': str(final_record['custodian_id']),
    'custodian_name': custodian_name
}
```

### 4. **PASSWORD UPDATE ENDPOINT MISMATCH**
**Severity: MEDIUM**
**Status: iOS not using actual API**

**Problem:**
- Backend has working password update endpoint: `PUT /api/users/me/password`
- iOS has local-only password update that doesn't call the API

**iOS Implementation:**
```swift
func updatePassword() {
    // This doesn't actually call the API!
    self.passwordUpdateMessage = "Password updated successfully!"
    self.isPasswordUpdateSuccessful = true
}
```

**Backend Implementation:**
```python
@app.put("/api/users/me/password")
async def update_user_password(password_update: PasswordUpdate, current_user: User = Depends(get_current_user)):
    # Actually updates password in database
```

**Remedy:**
```swift
func updatePassword() {
    guard !newPassword.isEmpty, newPassword == confirmPassword else {
        passwordUpdateMessage = "New passwords do not match."
        return
    }
    
    let passwordUpdate = PasswordUpdate(
        current_password: currentPassword,
        new_password: newPassword
    )
    
    APIService.shared.updatePassword(passwordUpdate: passwordUpdate) { [weak self] result in
        DispatchQueue.main.async {
            switch result {
            case .success:
                self?.passwordUpdateMessage = "Password updated successfully!"
                self?.isPasswordUpdateSuccessful = true
                self?.clearPasswordFields()
            case .failure(let error):
                self?.passwordUpdateMessage = "Failed to update password: \(error.localizedDescription)"
                self?.isPasswordUpdateSuccessful = false
            }
        }
    }
}
```

### 5. **DATE TIMEZONE INCONSISTENCIES**
**Severity: MEDIUM**  
**Status: Potential date mismatches**

**Problem:**
- iOS uses UTC timezone for date formatting
- Backend uses system timezone for date operations
- May cause off-by-one-day errors

**iOS Date Formatting:**
```swift
func isoDateString(from date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd"
    formatter.timeZone = TimeZone(secondsFromGMT: 0) // UTC
    return formatter.string(from: date)
}
```

**Backend Date Handling:**
```python
# Uses system timezone, not UTC
start_date = date(year, month, 1)  # System timezone
```

**Remedy:**
```python
from datetime import date, datetime, timezone

# Force UTC for consistency
def get_custody_records(year: int, month: int, current_user: User = Depends(get_current_user)):
    # Use UTC timezone consistently
    start_date = datetime(year, month, 1, tzinfo=timezone.utc).date()
```

### 6. **DEVICE TOKEN UPDATE URL CONSTRUCTION**
**Severity: LOW**
**Status: Incorrect URL building**

**Problem:**
- iOS constructs device token URL incorrectly

**iOS Code:**
```swift
func updateDeviceToken(token: String, completion: @escaping (Result<Void, Error>) -> Void) {
    guard let url = URL(string: "\(baseURL)/api/users/me/device-token") else {
        // This creates: https://calndr.club/api/api/users/me/device-token (double /api)
```

**Remedy:**
```swift
func updateDeviceToken(token: String, completion: @escaping (Result<Void, Error>) -> Void) {
    let url = baseURL.appendingPathComponent("/users/me/device-token")  // Remove /api prefix
    // Creates correct URL: https://calndr.club/api/users/me/device-token
```

### 7. **EVENT SAVE ENDPOINT MISMATCH**
**Severity: MEDIUM**
**Status: Backend rejects non-custody events**

**Problem:**
- Backend `/api/events` endpoint only handles legacy events  
- Returns placeholder response instead of saving to database

**Backend Response:**
```python
return {
    'id': 0,  # Placeholder ID - not saved!
    'event_date': legacy_event.event_date,
    'content': legacy_event.content,
    'position': legacy_event.position
}
```

**Remedy:**
```python
@app.post("/api/events")
async def save_event(request: dict, current_user: User = Depends(get_current_user)):
    if 'event_date' in request and 'position' in request and 'content' in request:
        if request['position'] == 4:
            raise HTTPException(status_code=400, detail="Use /api/custody endpoint")
        
        # Actually save the event to database
        event_date = datetime.strptime(request['event_date'], '%Y-%m-%d').date()
        
        # Create events table entry (need to add this table support)
        insert_query = events.insert().values(
            family_id=current_user.family_id,
            date=event_date,
            content=request['content'],
            position=request['position'],
            event_type='regular'
        )
        event_id = await database.execute(insert_query)
        
        return {
            'id': event_id,
            'event_date': request['event_date'],
            'content': request['content'],
            'position': request['position']
        }
```

## 🔧 Database Schema Issues

### Missing Fields in Events Table
The `events` table is missing fields that the API expects:

**Current Schema:**
```python
events = sqlalchemy.Table(
    "events",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id")),
    sqlalchemy.Column("date", sqlalchemy.Date),
    sqlalchemy.Column("custodian_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=True),
    sqlalchemy.Column("event_type", sqlalchemy.String, default='custody'),
    # MISSING: content, position fields
)
```

**Needed Schema:**
```python
events = sqlalchemy.Table(
    "events",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("family_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("families.id")),
    sqlalchemy.Column("date", sqlalchemy.Date),
    sqlalchemy.Column("content", sqlalchemy.String, nullable=True),  # ADD THIS
    sqlalchemy.Column("position", sqlalchemy.Integer, nullable=True),  # ADD THIS
    sqlalchemy.Column("custodian_id", UUID(as_uuid=True), sqlalchemy.ForeignKey("users.id"), nullable=True),
    sqlalchemy.Column("event_type", sqlalchemy.String, default='regular'),
)
```

## 🧪 Testing Simulation

Here's how to test these issues:

### Test School Events Failure:
```bash
curl -H "Authorization: Bearer <token>" https://calndr.club/api/school-events
# Returns: {"detail":"Not Found"}
```

### Test Custody Data Type Issues:
```python
# Simulate backend UUID handling
import uuid
custodian_id = uuid.uuid4()
print(f"Backend UUID: {custodian_id}")
print(f"String representation: {str(custodian_id)}")
print(f"Lowercase: {str(custodian_id).lower()}")

# iOS string comparison may fail due to case sensitivity
```

## 📋 Recommended Implementation Order

1. **Immediate Fixes (1-2 hours):**
   - Add school events endpoint (return empty array)
   - Fix device token URL construction
   - Standardize UUID string formatting

2. **Medium Priority (4-8 hours):**
   - Implement proper school events scraping
   - Fix password update in iOS to use actual API
   - Add content/position fields to events table

3. **Long-term Improvements (1-2 days):**
   - Standardize all date handling to UTC
   - Implement comprehensive event saving
   - Add proper error handling for all type mismatches

## 🔍 Monitoring & Logging

Add these logging points to catch failures:

**Backend:**
```python
import logging
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_api_calls(request: Request, call_next):
    logger.info(f"API Call: {request.method} {request.url}")
    response = await call_next(request)
    if response.status_code >= 400:
        logger.error(f"API Error: {response.status_code} for {request.url}")
    return response
```

**iOS:**
```swift
// Add to APIService error handling
if let jsonString = String(data: data, encoding: .utf8) {
    print("⚠️ API Error Response: \(jsonString)")
    print("🔍 Request URL: \(request.url?.absoluteString ?? "unknown")")
    print("📊 Status Code: \(httpResponse.statusCode)")
}
```

This analysis provides a roadmap to fix the critical data flow issues between your iOS app and Python backend. The most urgent fixes are the missing school events endpoint and the UUID string formatting inconsistencies.