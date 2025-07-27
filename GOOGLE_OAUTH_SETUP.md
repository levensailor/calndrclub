# Google OAuth Setup for Calndr

This document explains how to properly configure Google OAuth for both the iOS app and backend API.

## 🔐 OAuth Client Types

Google OAuth requires **different client types** for different parts of your application:

### 1. **iOS App Client** (Already Created ✅)
- **Type**: iOS Application
- **Client ID**: `427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com`
- **Client Secret**: ❌ **None** (iOS apps don't use secrets for security)
- **Used by**: Your iOS mobile application
- **Purpose**: User authentication in the mobile app

### 2. **Backend API Client** (❗ **Need to Create**)
- **Type**: Web Application
- **Client ID**: `[NEW_WEB_CLIENT_ID]` (You need to create this)
- **Client Secret**: `[NEW_WEB_CLIENT_SECRET]` (You'll get this when created)
- **Used by**: Your FastAPI backend server
- **Purpose**: Server-side OAuth token verification and user info retrieval

## 📋 Setup Instructions

### Step 1: Create Web Application OAuth Client

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Navigate to**: APIs & Services → Credentials
3. **Click**: "+ CREATE CREDENTIALS" → "OAuth 2.0 Client ID"
4. **Select**: "Web application"
5. **Configure**:
   - **Name**: "Calndr Backend API"
   - **Authorized redirect URIs**:
     - `https://calndr.club/api/v1/auth/google/callback` (Production)
     - `https://staging.calndr.club/api/v1/auth/google/callback` (Staging)
     - `http://localhost:8000/api/v1/auth/google/callback` (Development - optional)

### Step 2: Update Backend Configuration

After creating the web client, update your configuration:

#### A. Update Terraform Variables
```bash
# Edit terraform/production.tfvars
google_client_id = "YOUR_NEW_WEB_CLIENT_ID"

# Edit terraform/staging.tfvars  
google_client_id = "YOUR_NEW_WEB_CLIENT_ID"
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

### Step 3: Update iOS App (if needed)

Your iOS app should continue using the **original iOS Client ID**:
- **iOS Client ID**: `427740229486-irmioidbvts681onsl3crtfghlmmsjhq.apps.googleusercontent.com`
- **Backend Client ID**: `[YOUR_NEW_WEB_CLIENT_ID]`

## 🔄 OAuth Flow Explanation

### Current Issue
```
iOS App (iOS Client ID) → Backend API (❌ Missing Web Client)
                           ↳ Trying to verify with wrong client type
```

### Correct Flow
```
iOS App (iOS Client ID) → Backend API (✅ Web Client + Secret)
                           ↳ Properly verifies ID tokens
```

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