# Calndr Backend

A modular FastAPI backend for the Calndr family calendar application.

## Project Structure

```
backend/
├── api/
│   └── v1/
│       ├── api.py          # Main API router
│       └── endpoints/      # All endpoint modules
├── core/
│   ├── config.py          # Application configuration
│   ├── database.py        # Database connection
│   ├── logging.py         # Logging configuration
│   ├── middleware.py      # Custom middleware
│   └── security.py        # Security utilities
├── db/
│   └── models.py          # SQLAlchemy table definitions
├── schemas/               # Pydantic models
├── services/              # Business logic services
└── main.py               # FastAPI application entry point
```

## Features


✅ **Fully Implemented Endpoints:**
- Authentication (`/auth`)
- User Management (`/users`)
- Family Management (`/family`)
- Event Management (`/events`)
- Custody Management (`/custody`)
- Notification Management (`/notifications`)
- User Profile (`/profile`)
- Reminder Management (`/reminders`)
- Babysitter Management (`/babysitters`)
- Emergency Contacts (`/emergency-contacts`)
- Group Chat (`/group-chat`)
- Children Management (`/children`)
- Daycare Provider Management (`/daycare-providers`)
- Weather API (`/weather`)
- School Events (`/school-events`)
- Theme Management (`/themes`)

## Setup

1. **Install Dependencies**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Environment Variables**
Create a `.env` file in the backend directory:
```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=your_db_name
SECRET_KEY=your_secret_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your_s3_bucket
SNS_PLATFORM_APPLICATION_ARN=your_sns_arn
GOOGLE_PLACES_API_KEY=your_google_api_key
```

3. **Run the Application**
```bash
# Development
uvicorn main:app --reload --port 8000

# Production
gunicorn main:app -k uvicorn.workers.UvicornWorker
```

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Adding New Endpoints

1. Create a new module in `api/v1/endpoints/`
2. Define your router and endpoints
3. Add the router to `api/v1/api.py`
4. Create corresponding schemas in `schemas/`
5. Add any new models to `db/models.py`

### Database Migrations

Run migration scripts from the project root:
```bash
python migrate_db.py
```

## Testing

```bash
pytest tests/
```

## Deployment

The application is configured for deployment on AWS EC2. Use the deployment script:
```bash
../deploy.sh
```

This will:
1. Copy files to the EC2 instance
2. Install dependencies
3. Set up systemd service
4. Configure Nginx
5. Enable SSL with Certbot
