"""
Tests for Medical Providers and Medications API
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, time, datetime
from decimal import Decimal

from main import app
from core.database import get_db
from core.config import settings


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def test_user():
    """Create a test user for authentication"""
    # This would create a test user and return auth token
    # For now, we'll use a mock token
    return {
        "access_token": "test_token",
        "token_type": "bearer"
    }

@pytest.fixture
def test_family_id():
    """Test family ID"""
    return "test-family-id"

class TestMedicalProviders:
    """Test medical providers endpoints"""
    
    def test_create_medical_provider(self, test_user, test_family_id):
        """Test creating a medical provider"""
        provider_data = {
            "family_id": test_family_id,
            "name": "Dr. John Smith",
            "specialty": "Pediatrics",
            "address": "123 Main St, Anytown, NY 12345",
            "phone": "555-123-4567",
            "email": "dr.smith@example.com",
            "website": "https://drjohnsmith.com",
            "notes": "Great pediatrician"
        }
        
        response = client.post(
            "/api/v1/medical-providers/",
            json=provider_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == provider_data["name"]
        assert data["specialty"] == provider_data["specialty"]
        assert data["family_id"] == test_family_id
    
    def test_get_medical_providers(self, test_user, test_family_id):
        """Test getting all medical providers"""
        response = client.get(
            "/api/v1/medical-providers/",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "total" in data
        assert "page" in data
    
    def test_get_medical_provider_by_id(self, test_user, test_family_id):
        """Test getting a specific medical provider"""
        # First create a provider
        provider_data = {
            "family_id": test_family_id,
            "name": "Dr. Jane Doe",
            "specialty": "Cardiology"
        }
        
        create_response = client.post(
            "/api/v1/medical-providers/",
            json=provider_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        provider_id = create_response.json()["id"]
        
        # Get the provider
        response = client.get(
            f"/api/v1/medical-providers/{provider_id}",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == provider_id
        assert data["name"] == provider_data["name"]
    
    def test_update_medical_provider(self, test_user, test_family_id):
        """Test updating a medical provider"""
        # First create a provider
        provider_data = {
            "family_id": test_family_id,
            "name": "Dr. Bob Wilson",
            "specialty": "Dermatology"
        }
        
        create_response = client.post(
            "/api/v1/medical-providers/",
            json=provider_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        provider_id = create_response.json()["id"]
        
        # Update the provider
        update_data = {
            "phone": "555-987-6543",
            "email": "dr.wilson@example.com"
        }
        
        response = client.put(
            f"/api/v1/medical-providers/{provider_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == update_data["phone"]
        assert data["email"] == update_data["email"]
    
    def test_delete_medical_provider(self, test_user, test_family_id):
        """Test deleting a medical provider"""
        # First create a provider
        provider_data = {
            "family_id": test_family_id,
            "name": "Dr. Alice Brown",
            "specialty": "Neurology"
        }
        
        create_response = client.post(
            "/api/v1/medical-providers/",
            json=provider_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        provider_id = create_response.json()["id"]
        
        # Delete the provider
        response = client.delete(
            f"/api/v1/medical-providers/{provider_id}",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_search_medical_providers(self, test_user, test_family_id):
        """Test searching medical providers"""
        # Create some test providers
        providers = [
            {
                "family_id": test_family_id,
                "name": "Dr. Sarah Johnson",
                "specialty": "Pediatrics",
                "address": "456 Oak Ave, Somewhere, CA 90210"
            },
            {
                "family_id": test_family_id,
                "name": "Dr. Mike Davis",
                "specialty": "Orthopedics",
                "address": "789 Pine St, Elsewhere, TX 75001"
            }
        ]
        
        for provider in providers:
            client.post(
                "/api/v1/medical-providers/",
                json=provider,
                headers={"Authorization": f"Bearer {test_user['access_token']}"}
            )
        
        # Search by name
        response = client.get(
            "/api/v1/medical-providers/search?q=Sarah",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["providers"]) > 0
        assert any("Sarah" in p["name"] for p in data["providers"])
    
    def test_search_by_location(self, test_user, test_family_id):
        """Test searching medical providers by location"""
        response = client.get(
            "/api/v1/medical-providers/search?lat=40.7128&lng=-74.0060&radius=25",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data

class TestMedications:
    """Test medications endpoints"""
    
    def test_create_medication(self, test_user, test_family_id):
        """Test creating a medication"""
        medication_data = {
            "family_id": test_family_id,
            "name": "Amoxicillin",
            "dosage": "250mg",
            "frequency": "Twice daily",
            "instructions": "Take with food",
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
            "is_active": True,
            "reminder_enabled": True,
            "reminder_time": "08:00:00",
            "notes": "For ear infection"
        }
        
        response = client.post(
            "/api/v1/medications/",
            json=medication_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == medication_data["name"]
        assert data["dosage"] == medication_data["dosage"]
        assert data["family_id"] == test_family_id
    
    def test_get_medications(self, test_user, test_family_id):
        """Test getting all medications"""
        response = client.get(
            "/api/v1/medications/",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "medications" in data
        assert "total" in data
        assert "page" in data
    
    def test_get_medication_by_id(self, test_user, test_family_id):
        """Test getting a specific medication"""
        # First create a medication
        medication_data = {
            "family_id": test_family_id,
            "name": "Ibuprofen",
            "dosage": "200mg",
            "frequency": "As needed"
        }
        
        create_response = client.post(
            "/api/v1/medications/",
            json=medication_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        medication_id = create_response.json()["id"]
        
        # Get the medication
        response = client.get(
            f"/api/v1/medications/{medication_id}",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == medication_id
        assert data["name"] == medication_data["name"]
    
    def test_update_medication(self, test_user, test_family_id):
        """Test updating a medication"""
        # First create a medication
        medication_data = {
            "family_id": test_family_id,
            "name": "Tylenol",
            "dosage": "500mg"
        }
        
        create_response = client.post(
            "/api/v1/medications/",
            json=medication_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        medication_id = create_response.json()["id"]
        
        # Update the medication
        update_data = {
            "dosage": "1000mg",
            "frequency": "Every 6 hours"
        }
        
        response = client.put(
            f"/api/v1/medications/{medication_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["dosage"] == update_data["dosage"]
        assert data["frequency"] == update_data["frequency"]
    
    def test_delete_medication(self, test_user, test_family_id):
        """Test deleting a medication"""
        # First create a medication
        medication_data = {
            "family_id": test_family_id,
            "name": "Aspirin",
            "dosage": "81mg"
        }
        
        create_response = client.post(
            "/api/v1/medications/",
            json=medication_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        medication_id = create_response.json()["id"]
        
        # Delete the medication
        response = client.delete(
            f"/api/v1/medications/{medication_id}",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_get_active_medications(self, test_user, test_family_id):
        """Test getting active medications"""
        response = client.get(
            "/api/v1/medications/active",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "medications" in data
        assert "total" in data
    
    def test_get_medication_reminders(self, test_user, test_family_id):
        """Test getting medications with reminders"""
        response = client.get(
            "/api/v1/medications/reminders",
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        assert "total" in data

class TestValidation:
    """Test validation and error handling"""
    
    def test_invalid_medication_dates(self, test_user, test_family_id):
        """Test validation of medication date ranges"""
        medication_data = {
            "family_id": test_family_id,
            "name": "Test Medication",
            "start_date": "2024-01-10",
            "end_date": "2024-01-01"  # End before start
        }
        
        response = client.post(
            "/api/v1/medications/",
            json=medication_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 422
    
    def test_invalid_reminder_settings(self, test_user, test_family_id):
        """Test validation of reminder settings"""
        medication_data = {
            "family_id": test_family_id,
            "name": "Test Medication",
            "reminder_enabled": True,
            # Missing reminder_time
        }
        
        response = client.post(
            "/api/v1/medications/",
            json=medication_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 422
    
    def test_invalid_phone_number(self, test_user, test_family_id):
        """Test validation of phone number format"""
        provider_data = {
            "family_id": test_family_id,
            "name": "Dr. Test",
            "phone": "invalid-phone"
        }
        
        response = client.post(
            "/api/v1/medical-providers/",
            json=provider_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 422
    
    def test_invalid_email(self, test_user, test_family_id):
        """Test validation of email format"""
        provider_data = {
            "family_id": test_family_id,
            "name": "Dr. Test",
            "email": "invalid-email"
        }
        
        response = client.post(
            "/api/v1/medical-providers/",
            json=provider_data,
            headers={"Authorization": f"Bearer {test_user['access_token']}"}
        )
        
        assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__]) 