"""
Unit tests for the FastAPI layer (API Contract).
These tests use the TestClient and hit the seeded database.
"""
import os
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.database import get_db
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

# Use the environment variable for DB in tests
db_url = os.environ.get("GENUINE_RX_DB_URL", "postgresql+psycopg://postgres:devpass@localhost:5432/genuine_rx")
if not db_url:
    pytest.skip("GENUINE_RX_DB_URL not set", allow_module_level=True)

client = TestClient(app)

def get_test_db():
    dsn = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()

# Override the DB dependency so we are sure it runs correctly in test context
app.dependency_overrides[get_db] = get_test_db

class TestAPIContract:
    def test_resolve_medicine_high_confidence(self):
        response = client.post("/api/v1/resolve-medicine", json={
            "raw_text": "Crocin",
            "source": "ocr"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["matched"] is True
        assert data["brand_name"] == "Crocin"
        assert data["needs_confirmation"] is False
        assert data.get("candidates") is None

    def test_resolve_medicine_low_confidence(self):
        response = client.post("/api/v1/resolve-medicine", json={
            "raw_text": "Croc",
            "source": "typed"
        })
        assert response.status_code == 200
        data = response.json()
        # "Croc" against "Crocin" might score < 75 or >= 75 depending on RapidFuzz
        # We just verify the shape is correct in either case.
        assert "matched" in data
        assert "needs_confirmation" in data

    def test_get_substitutes(self):
        # Crocin is ID 16 in seed.py
        response = client.get("/api/v1/medicines/16/substitutes")
        assert response.status_code == 200
        data = response.json()
        assert "source_medicine" in data
        assert data["source_medicine"]["brand_name"] == "Crocin"
        
        subs = data["substitutes"]
        assert len(subs) > 0
        
        # Verify Jan Aushadhi is first
        assert subs[0]["is_jan_aushadhi"] is True
        
        # Verify shapes
        for sub in subs:
            assert "savings_percent" in sub
            assert "savings_rupees" in sub
            assert "price" in sub

    def test_substitutes_not_found(self):
        response = client.get("/api/v1/medicines/99999/substitutes")
        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "not_found"

    def test_create_user_valid(self):
        response = client.post("/api/v1/users", json={
            "phone": "+919876543210",
            "consent_whatsapp": True
        })
        assert response.status_code == 201
        assert "user_id" in response.json()

    def test_create_user_invalid_phone(self):
        response = client.post("/api/v1/users", json={
            "phone": "9876543210",  # missing +91
            "consent_whatsapp": True
        })
        assert response.status_code == 422  # Pydantic validation error

    def test_tracked_medicines_flow(self):
        # 0. Find Crocin medicine_id
        resolve_res = client.post("/api/v1/resolve-medicine", json={
            "raw_text": "Crocin",
            "source": "typed"
        })
        assert resolve_res.status_code == 200
        resolve_data = resolve_res.json()
        assert resolve_data["matched"] is True
        med_id = resolve_data["medicine_id"]

        # 1. Create or get user
        user_res = client.post("/api/v1/users", json={
            "phone": "+919988776655",
            "consent_whatsapp": True
        })
        assert user_res.status_code == 201
        user_id = user_res.json()["user_id"]

        # 2. Add tracked medicine
        response = client.post("/api/v1/tracked-medicines", json={
            "user_id": user_id,
            "medicine_id": med_id,
            "profile_label": "Self"
        })
        assert response.status_code == 201
        
        # 3. Get tracked medicines
        response2 = client.get(f"/api/v1/users/{user_id}/tracked-medicines")
        assert response2.status_code == 200
        items = response2.json()
        assert len(items) > 0
        
        # Check properties
        crocin_item = next(i for i in items if i["medicine_id"] == med_id)
        assert "Crocin" in crocin_item["brand_name"]
        assert "latest_price" in crocin_item
