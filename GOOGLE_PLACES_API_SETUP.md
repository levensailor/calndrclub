# Google Places API Setup for Enhanced School Search

## 📱 Overview

The enhanced school search combines **MapKit** (for finding schools) with **Google Places API** (for detailed information like website, hours, and ratings). This provides the best of both worlds: privacy-focused native search with comprehensive business details.

## 🔑 Google Places API Setup

### Step 1: Get Google Places API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Places API** for your project:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Places API"
   - Click on "Places API" and enable it
4. Create an API key:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the generated API key

### Step 2: Secure Your API Key (Recommended)

1. **Restrict the API key** in Google Cloud Console:
   - Click on your API key in the credentials page
   - Under "Application restrictions", select "iOS apps"
   - Add your app's bundle identifier (e.g., `com.yourcompany.calndr`)
   - Under "API restrictions", select "Restrict key" and choose "Places API"

### Step 3: Add API Key to iOS Project

Add the API key to your app's `Info.plist`:

```xml
<!-- Add this to ios/calndr/calndr/Info.plist -->
<key>GOOGLE_PLACES_API_KEY</key>
<string>YOUR_API_KEY_HERE</string>
```

**⚠️ Security Note**: Never commit your actual API key to version control. Consider using environment variables or build configurations for different environments.

## 🚀 Integration Steps

### Step 1: Add Enhanced Search Manager to Xcode
1. Add `EnhancedSchoolSearchManager.swift` to your Xcode project
2. Ensure it's added to your target

### Step 2: Update Info.plist
```xml
<key>GOOGLE_PLACES_API_KEY</key>
<string>YOUR_ACTUAL_API_KEY_HERE</string>
```

### Step 3: Build and Test
The enhanced search will automatically:
1. Use MapKit to find schools (fast, privacy-focused)
2. When user selects a school, enhance it with Google data
3. Display enhanced information in the schools list

## 🎯 How It Works

### Search Flow:
1. **MapKit Search**: Finds schools using native iOS search
   - Fast and privacy-focused
   - No API usage costs
   - Provides: name, address, phone number, distance

2. **User Selection**: When user chooses a school to add

3. **Google Enhancement**: Automatically looks up additional details
   - Uses Google Places API
   - Provides: website, business hours, ratings
   - Shows loading indicator during enhancement

4. **Final Result**: School saved with complete information

### API Usage Optimization:
- **No bulk enhancement**: Only enhances schools that users actually select
- **Coordinate matching**: Ensures Google result matches MapKit result (500m radius)
- **Graceful fallback**: If Google enhancement fails, saves with MapKit data
- **Error handling**: Continues working even without API key

## 🔧 Features

### MapKit Provides:
- ✅ School name
- ✅ Full address
- ✅ Phone number (when available)
- ✅ Distance from search point
- ✅ Coordinates

### Google Places API Adds:
- ✅ Website URL
- ✅ Business hours (formatted)
- ✅ User ratings (1-5 stars)
- ✅ Price level information
- ✅ Verified Google Place ID

### Enhanced School Card Features:
- **Clickable phone numbers** (opens phone app)
- **Clickable websites** (opens Safari)
- **Formatted business hours** (multi-line display)
- **Star ratings** (visual rating display)
- **Complete address** (from MapKit)

## 💰 Cost Considerations

### Google Places API Pricing:
- **Find Place from Text**: $0.017 per request
- **Place Details**: $0.017 per request
- **Total per school enhancement**: ~$0.034

### Cost Optimization:
- Only enhances schools when user selects them (not during search)
- Typical usage: 1-5 schools enhanced per user session
- Monthly costs for small apps: $1-10 depending on usage

### Free Tier:
- Google provides $200 monthly credit
- Covers ~5,800 school enhancements per month
- More than sufficient for most apps

## 🛠️ Troubleshooting

### Common Issues:

1. **No enhancement happening**:
   - Check if `GOOGLE_PLACES_API_KEY` is in Info.plist
   - Verify API key is valid in Google Cloud Console
   - Check Xcode console for error messages

2. **"API key not available" in logs**:
   - Ensure key is added to Info.plist with correct name
   - Clean build and rebuild project

3. **Google API errors**:
   - Check if Places API is enabled in Google Cloud Console
   - Verify API key restrictions allow your app
   - Check quota limits in Google Cloud Console

4. **Schools found but no Google data**:
   - Normal for some schools (not all are in Google Places)
   - Check coordinate matching (must be within 500m)
   - Some schools may not have complete Google business profiles

### Debug Tips:

Enable detailed logging to see the enhancement process:
```swift
// Check console for these log messages:
// ✅ Enhanced school 'School Name' with Google data
// ❌ Failed to enhance school 'School Name': error details
// ⚠️ Google Places API key not available - skipping enhancement
```

## 🔒 Privacy & Security

### Privacy Benefits:
- **MapKit**: No data sent to third parties during search
- **Google**: Only used when user actively selects a school
- **Minimal data**: Only school name and coordinates sent to Google

### Security Best Practices:
- Restrict API key to your iOS app bundle ID
- Use environment-specific API keys for dev/prod
- Monitor API usage in Google Cloud Console
- Never expose API keys in client-side code repositories

## 📋 Testing Checklist

- [ ] Google Places API enabled in Cloud Console
- [ ] API key added to Info.plist
- [ ] API key restrictions configured (bundle ID + Places API)
- [ ] Project builds without errors
- [ ] MapKit search works (schools appear in search results)
- [ ] School selection triggers enhancement (loading indicator shows)
- [ ] Enhanced schools display additional information
- [ ] Error handling works gracefully without API key
- [ ] Console logs show enhancement success/failure messages

## 🎉 Benefits

### For Users:
- **Fast search** with native MapKit
- **Complete information** with Google enhancement
- **Seamless experience** with automatic enhancement
- **Rich school profiles** with websites, hours, and ratings

### For Developers:
- **Cost-effective** (only enhances selected schools)
- **Privacy-focused** (MapKit for discovery)
- **Robust** (works without Google API)
- **Future-proof** (can add more data sources easily)

The enhanced school search provides a premium experience that combines the best of native iOS capabilities with comprehensive business data! 🎊 