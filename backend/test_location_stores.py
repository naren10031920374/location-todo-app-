"""Tests for finding the nearest real branch of a store (OpenStreetMap Nominatim, mocked)."""
import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import geocoding
from database import Base
from models import Store
from schemas import UserCreate
from services import (
    create_store,
    create_todos_from_parsed_text,
    create_user,
    get_nearby_todos,
    get_or_create_store_near,
)

# User is in Ann Arbor, MI
USER_LAT, USER_LON = 42.2808, -83.7430


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def fresh_cache_and_no_sleep(monkeypatch):
    geocoding._cache.clear()
    monkeypatch.setattr(geocoding, "_MIN_INTERVAL_SECONDS", 0)


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


def osm(name, lat, lon):
    return {"name": name, "display_name": f"{name}, Michigan, USA", "lat": str(lat), "lon": str(lon)}


def mock_nominatim(monkeypatch, payload, calls=None):
    def fake_get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append({"url": url, "params": params, "headers": headers})
        if isinstance(payload, Exception):
            raise payload
        return FakeResponse(payload)

    monkeypatch.setattr(geocoding.requests, "get", fake_get)


# ---------- find_nearest_store ----------

def test_picks_closest_branch(monkeypatch):
    mock_nominatim(monkeypatch, [
        osm("Walmart far", 42.30, -83.70),     # ~3.5 km
        osm("Walmart near", 42.2830, -83.7440),  # ~0.3 km
        osm("Walmart mid", 42.29, -83.72),
    ])
    result = geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON)
    assert result["name"] == "Walmart near"
    assert result["distance_km"] < 0.5


def test_ignores_results_outside_radius(monkeypatch):
    mock_nominatim(monkeypatch, [osm("Walmart Detroit", 42.33, -83.05)])  # ~57 km away
    assert geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON) is None


def test_sends_viewbox_user_agent_and_bounded(monkeypatch):
    calls = []
    mock_nominatim(monkeypatch, [], calls)
    geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON)
    params = calls[0]["params"]
    assert params["bounded"] == 1 and params["q"] == "Walmart"
    left, top, right, bottom = map(float, params["viewbox"].split(","))
    assert left < USER_LON < right and bottom < USER_LAT < top  # box surrounds the user
    assert "LocationTodoApp" in calls[0]["headers"]["User-Agent"]


def test_network_error_returns_none_and_is_not_cached(monkeypatch):
    mock_nominatim(monkeypatch, requests.exceptions.ConnectionError("down"))
    assert geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON) is None

    calls = []
    mock_nominatim(monkeypatch, [osm("Walmart", 42.2830, -83.7440)], calls)
    assert geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON) is not None
    assert len(calls) == 1  # retried because the failure was not cached


def test_results_are_cached(monkeypatch):
    calls = []
    mock_nominatim(monkeypatch, [osm("Walmart", 42.2830, -83.7440)], calls)
    geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON)
    geocoding.find_nearest_store("walmart ", USER_LAT + 0.0001, USER_LON)  # same name/cell
    assert len(calls) == 1


def test_malformed_results_are_skipped(monkeypatch):
    mock_nominatim(monkeypatch, [{"name": "bad"}, {"lat": "x", "lon": "y"}, osm("Good", 42.2830, -83.7440)])
    assert geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON)["name"] == "Good"


def test_non_list_response_is_handled(monkeypatch):
    mock_nominatim(monkeypatch, {"error": "rate limited"})
    assert geocoding.find_nearest_store("Walmart", USER_LAT, USER_LON) is None


# ---------- get_or_create_store_near ----------

def test_creates_store_with_coordinates(db, monkeypatch):
    mock_nominatim(monkeypatch, [osm("Walmart Supercenter", 42.2830, -83.7440)])
    store, distance = get_or_create_store_near(db, "Walmart", USER_LAT, USER_LON)
    assert store.name == "Walmart"
    assert store.latitude == pytest.approx(42.2830) and store.longitude == pytest.approx(-83.7440)
    assert "Michigan" in store.address
    assert distance < 0.5


def test_reuses_saved_nearby_branch_without_network(db, monkeypatch):
    create_store(db, "Walmart", "Main St", 42.2830, -83.7440)
    calls = []
    mock_nominatim(monkeypatch, [], calls)
    store, distance = get_or_create_store_near(db, "walmart", USER_LAT, USER_LON)
    assert calls == []
    assert store.address == "Main St" and distance is not None
    assert db.query(Store).count() == 1


def test_other_citys_branch_is_not_reused(db, monkeypatch):
    create_store(db, "Walmart", "Detroit", 42.33, -83.05)
    mock_nominatim(monkeypatch, [osm("Walmart AA", 42.2830, -83.7440)])
    store, _ = get_or_create_store_near(db, "Walmart", USER_LAT, USER_LON)
    assert store.address != "Detroit"
    assert db.query(Store).count() == 2


def test_falls_back_to_plain_store_when_lookup_fails(db, monkeypatch):
    mock_nominatim(monkeypatch, requests.exceptions.Timeout("slow"))
    store, distance = get_or_create_store_near(db, "Walmart", USER_LAT, USER_LON)
    assert store.name == "Walmart" and store.latitude is None and distance is None


# ---------- end to end through the service layer ----------

def test_reminder_fires_near_located_store_and_not_far_away(db, monkeypatch):
    mock_nominatim(monkeypatch, [osm("Walmart", 42.2830, -83.7440)])
    user = create_user(db, UserCreate(email="a@b.com", password="pw12345678", full_name="A"))
    store, _ = get_or_create_store_near(db, "Walmart", USER_LAT, USER_LON)

    todos = create_todos_from_parsed_text(
        db, user.id, {"items": ["milk", "eggs"], "store": "Walmart", "date": None, "category": "groceries"},
        store=store,
    )
    assert len(todos) == 2

    near = get_nearby_todos(db, user.id, 42.2831, -83.7441)
    assert len(near) == 2 and near[0]["store_name"] == "Walmart"
    assert get_nearby_todos(db, user.id, 40.7128, -74.0060) == []  # New York


def test_fallback_never_reuses_another_citys_branch(db, monkeypatch):
    create_store(db, "Walmart", "Detroit", 42.33, -83.05)
    mock_nominatim(monkeypatch, [])  # nothing found near the user
    store, distance = get_or_create_store_near(db, "Walmart", 34.05, -118.24)
    assert store.latitude is None and distance is None
    again, _ = get_or_create_store_near(db, "Walmart", 34.05, -118.24)
    assert again.id == store.id  # unlocated store is reused, not duplicated
