# Calndr API Diagram Documentation

This directory contains API documentation for the Calndr backend that can be imported into Lucidchart.

## Files Created

1. **api_endpoints.csv** - A CSV file containing all API endpoints that can be imported directly into Lucidchart
2. **api_diagram.puml** - A PlantUML diagram showing the API architecture

## How to Import into Lucidchart

### Method 1: CSV Import (Recommended)
1. Open Lucidchart
2. Go to File → Import Data
3. Select "Import Your Data"
4. Upload `api_endpoints.csv`
5. Map the columns:
   - Module → Shape Name
   - Path → Additional Text
   - Method + Endpoint → Description
   - Category → Group/Container
6. Choose a layout (hierarchy or grid)
7. Click "Import"

### Method 2: PlantUML Import
1. Open Lucidchart
2. Go to File → Import
3. Select "PlantUML"
4. Copy the contents of `api_diagram.puml`
5. Paste into the import dialog
6. Click "Import"

## API Overview

### Base URL: `/api`

### API Categories:

#### 1. Authentication & Users
- **Authentication** (`/api/auth`) - 9 endpoints
- **Users** (`/api/users`) - 9 endpoints
- **Profile** (`/api/user/profile`) - 1 endpoint
- **Phone Verification** (`/api/phone-verification`) - 3 endpoints

#### 2. Calendar & Scheduling
- **Events** (`/api/events`) - 5 endpoints
- **Custody** (`/api/custody`) - 5 endpoints
- **Schedule Templates** (`/api/schedule-templates`) - 6 endpoints
- **School Events** (`/api/school-events`) - 1 endpoint

#### 3. Family Management
- **Family** (`/api/family`) - 5 endpoints
- **Children** (`/api/children`) - 4 endpoints
- **Daycare Providers** (`/api/daycare-providers`) - 7 endpoints
- **Emergency Contacts** (`/api/emergency-contacts`) - 4 endpoints
- **Babysitters** (`/api/babysitters`) - 4 endpoints

#### 4. Communication
- **Journal** (`/api/journal`) - 5 endpoints
- **Notifications** (`/api/notifications`) - 4 endpoints
- **Themes** (`/api/themes`) - 5 endpoints
- **Reminders** (`/api/reminders`) - 1 endpoint
- **Group Chat** (`/api/group-chat`) - 1 endpoint

#### 5. External Integration
- **Weather** (`/api/weather`) - 2 endpoints

### External Services
- Twilio (SMS)
- SendGrid (Email)
- Weather API
- Apple Authentication
- Google OAuth
- Facebook Authentication

### Database
- PostgreSQL with SQLAlchemy ORM

## Creating Custom Diagrams

You can use the CSV data to create custom diagrams by:
1. Filtering by Category or Module
2. Creating separate diagrams for each category
3. Adding custom styling based on the HTTP methods
4. Creating sequence diagrams for specific workflows

## Color Scheme Used
- **Authentication & Users**: #FFE6CC (Light Orange)
- **Calendar & Scheduling**: #DAE8FC (Light Blue)
- **Family Management**: #F8CECC (Light Red)
- **Communication**: #E1D5E7 (Light Purple)
- **External Integration**: #D4E1F5 (Light Blue-Gray)
