# Google OAuth Setup for Calndr

This document explains how to properly configure Google OAuth for the iOS app and backend API.

## 🔐 OAuth Client Configuration

For your iOS app + Python backend setup, you **only need ONE client ID**:

### **iOS App Client** (Already Created ✅)
- **Type**: iOS Application
- **Client ID**: `427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com`
- **Client Secret**: ❌ **None** (iOS apps don't use secrets for security)
- **Used by**: 
  - ✅ Your iOS mobile application (for getting ID tokens)
  - ✅ Your FastAPI backend server (for verifying those same ID tokens)
- **Purpose**: Complete OAuth flow from iOS app authentication to backend token verification

## 🔄 How It Works

1. **iOS app** uses the iOS Client ID to authenticate with Google and get an ID token
2. **iOS app** sends that ID token to your backend API
3. **Backend** verifies the token using the **same iOS Client ID** that created it

**❌ You do NOT need a separate "Web Application" client ID for the backend!**

## 📋 Setup Instructions

### Step 1: Use Your Existing iOS Client ID

Since you already have the iOS Client ID working, **you're done!** Just make sure your backend is configured with the same iOS Client ID.

### Step 2: Backend Configuration

Your backend should use the **same iOS Client ID** for token verification:

#### A. Update Terraform Variables
```bash
# Edit terraform/production.tfvars
google_client_id = "427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com"

# Edit terraform/staging.tfvars  
google_client_id = "427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com"
```

#### B. Update SSM Parameters Script
```bash
# Edit scripts/setup-ssm-parameters.sh
GOOGLE_CLIENT_SECRET="YOUR_NEW_WEB_CLIENT_SECRET"
```

#### C. Deploy Configuration
```bash
# Set up SSM parameters
./scripts/setup-ssm-parameters.sh setup-all

# Deploy terraform changes
cd terraform
terraform apply -var-file="production.tfvars"
```

### Step 3: Verify iOS App Configuration

Your iOS app should continue using the **same iOS Client ID**:
- **iOS Client ID**: `427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com`
- **Backend Client ID**: **Same as iOS** (`427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com`)

## 🔄 OAuth Flow Explanation

### How It Actually Works
```
iOS App (iOS Client ID) → Gets ID Token from Google
                           ↓
iOS App → Sends ID Token → Backend API (Same iOS Client ID)
                           ↳ Verifies token using same client ID
```

### ✅ This is the CORRECT and SECURE approach!

## 🛠️ Authentication Endpoints

### Backend Endpoints
- `GET /api/v1/auth/google/login` - Returns Google auth URL
- `POST /api/v1/auth/google/callback` - Handles web OAuth callback
- `POST /api/v1/auth/google/ios-login` - Handles iOS ID token verification

### Flow Types

#### 1. Web Flow (Future Use)
```
1. Client calls /auth/google/login
2. User authorizes on Google
3. Google redirects to /auth/google/callback
4. Backend exchanges code for tokens
5. Backend returns access_token
```

#### 2. iOS Flow (Current Use)
```
1. iOS app handles Google Sign-In
2. iOS app gets ID token from Google
3. iOS app sends ID token to /auth/google/ios-login
4. Backend verifies ID token with Google
5. Backend returns access_token
```

## 🔧 Troubleshooting

### Check OAuth Configuration
```bash
# Debug Google OAuth setup
./scripts/debug-google-auth.sh all production

# Check SSM parameters
./scripts/setup-ssm-parameters.sh list production

# View backend logs
./scripts/quick-logs.sh errors-prod
```

### Common Issues

#### 1. "Invalid Google token" Error
- **Cause**: Backend using wrong client ID/secret
- **Fix**: Ensure backend uses **Web Application** client, not iOS client

#### 2. "access_token" Not Found Error  
- **Cause**: Backend not returning properly formatted response
- **Fix**: Ensure backend endpoints return `{"access_token": "...", "token_type": "bearer"}`

#### 3. "Client Secret Missing" Error
- **Cause**: Web Application OAuth client not created
- **Fix**: Create Web Application client and update SSM parameters

## 📊 Configuration Summary

| Component | Client Type | Client ID | Client Secret |
|-----------|-------------|-----------|---------------|
| iOS App | iOS Application | `427740229486-...` | ❌ None |
| Backend API | Web Application | `[NEW_WEB_ID]` | ✅ Required |

## 🚀 Quick Setup Commands

After creating the Web Application OAuth client:

```bash
# 1. Update SSM script with new credentials
nano scripts/setup-ssm-parameters.sh

# 2. Update terraform variables  
nano terraform/production.tfvars
nano terraform/staging.tfvars

# 3. Deploy everything
./scripts/setup-ssm-parameters.sh setup-all
cd terraform && terraform apply -var-file="production.tfvars"

# 4. Test the setup
./scripts/debug-google-auth.sh all production
```

---

**🎯 Key Takeaway**: You need **TWO** separate OAuth clients - one for iOS (no secret) and one for your backend API (with secret). The current iOS client is correct, but you need to create an additional Web Application client for the backend. 