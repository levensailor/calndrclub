# MapKit School Search Integration Instructions

## 📱 Overview

The iOS app has been updated to use **MapKit's MKLocalSearch** instead of Google Places API for school searches. This provides native iOS search functionality and removes the dependency on Google Places API.

## 🔧 Files Modified

### ✅ New Files Created:
- `ios/calndr/calndr/SchoolSearchManager.swift` - MapKit-based school search implementation

### ✅ Files Modified:
- `ios/calndr/calndr/SchoolView.swift` - Updated to use MapKit search
- `ios/calndr/calndr/CalendarViewModel.swift` - Removed Google Places API dependency

## 🚀 Integration Steps

### Step 1: Add MapKit Framework
1. Open **calndr.xcodeproj** in Xcode
2. Select your target (calndr)
3. Go to **"General"** tab
4. Scroll to **"Frameworks, Libraries, and Embedded Content"**
5. Click the **"+"** button
6. Search for and add **"MapKit.framework"**
7. Ensure it's set to **"Do Not Embed"**

### Step 2: Add Location Permissions (Already Done)
The following is already configured in `Info.plist`:
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>A coparent on calndr is requesting your location.</string>
```

### Step 3: Add File to Xcode Project
1. Right-click on the **calndr** folder in Xcode
2. Select **"Add Files to 'calndr'"**
3. Navigate to and select **`SchoolSearchManager.swift`**
4. Ensure **"Add to target: calndr"** is checked
5. Click **"Add"**

### Step 4: Import MapKit in Relevant Files (Already Done)
The following imports are already added to `SchoolSearchManager.swift`:
```swift
import Foundation
import MapKit
import CoreLocation
```

### Step 5: Build and Test
1. Clean build folder: **Product → Clean Build Folder**
2. Build the project: **⌘ + B**
3. Run on device or simulator: **⌘ + R**

## 🎯 Features Included

### MapKit School Search Features:
- **🔍 Location-based search**: Find schools near current location
- **📍 ZIP code search**: Search schools by ZIP code with geocoding
- **🏫 Smart filtering**: Filters results to education-related places only
- **📏 Distance calculation**: Shows distance from search center
- **📱 Native integration**: Uses iOS native search with no API keys required

### Search Types:
- **Current Location**: Uses GPS to find nearby schools (5km radius)
- **ZIP Code**: Geocodes ZIP code and searches within 10km radius

### Data Provided:
- School name
- Full address
- Phone number (when available)
- Distance from search point
- Coordinates for mapping

## 🔄 API Changes

### Before (Google Places API):
```swift
// Used viewModel.searchSchoolProviders() with API calls
viewModel.searchSchoolProviders(searchRequest) { result in
    // Handle API response
}
```

### After (MapKit):
```swift
// Uses SchoolSearchManager with native MapKit
let results = await searchManager.searchForSchools(
    type: searchType,
    zipCode: zipCode,
    userLocation: userLocation
)
```

## ⚠️ Important Notes

### MapKit Limitations:
- **No ratings**: MapKit doesn't provide business ratings
- **No reviews**: No user review data available
- **No hours**: Business hours not typically available
- **No websites**: Website URLs not provided directly

### Benefits:
- **No API keys required**: Uses Apple's native services
- **Better iOS integration**: Follows Apple's design patterns
- **Privacy focused**: No third-party data sharing
- **Free**: No usage limits or costs
- **Offline capable**: Works with cached map data

## 🛠️ Troubleshooting

### Common Issues:

1. **"MapKit not found" error**:
   - Ensure MapKit framework is added to project
   - Check deployment target (iOS 14.0+)

2. **No search results**:
   - Check location permissions
   - Verify internet connection for fresh searches
   - Try broader search terms

3. **Location not working**:
   - Check `Info.plist` for location usage description
   - Verify location permissions in Settings app
   - Test on physical device (simulator location may be limited)

## 📋 Testing Checklist

- [ ] MapKit framework added to project
- [ ] SchoolSearchManager.swift added to target
- [ ] Project builds without errors
- [ ] Location-based search works
- [ ] ZIP code search works
- [ ] Results show school names and addresses
- [ ] Distance calculation works
- [ ] Phone numbers are clickable (when available)
- [ ] Error handling works for invalid ZIP codes
- [ ] Location permission prompts work correctly

## 🎉 Benefits of MapKit Integration

1. **🔒 Privacy**: No third-party API calls
2. **💰 Cost**: Free with no usage limits
3. **🚀 Performance**: Native iOS integration
4. **📱 UX**: Consistent with iOS design patterns
5. **🌍 Global**: Works worldwide without API key restrictions
6. **🔄 Reliability**: Uses Apple's infrastructure

The MapKit implementation provides a more native iOS experience while maintaining all the core functionality needed for school searches! 🎊 