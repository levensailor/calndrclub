# Deploy Your Calendar Backend to Railway

## Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

## Step 2: Login to Railway
```bash
railway login
```

## Step 3: Initialize Railway Project
```bash
railway init
```

## Step 4: Deploy
```bash
railway up
```

## Step 5: Set Environment Variables
In the Railway dashboard, add:
- `GMAIL_APP_PASSWORD` - Your Gmail app password for email functionality

## Step 6: Get Your App URL
Railway will give you a URL like: `https://your-app-name.railway.app`

## Step 7: Update Your iOS App
Update your frontend to use the Railway URL instead of localhost.

Your backend will be available at: `https://your-app-name.railway.app/api/` 