import os
import threading
import time
from math import cos, radians
from typing import Optional, Tuple

import requests

# Nominatim (OpenStreetMap) search endpoint. Overridable so tests can use a stand-in server.
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")

# OSM's usage policy requires identifying your app with a real User-Agent.
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "LocationTodoApp/1.0 (github.com/naren10031920374)")

# How far from the user to look for a branch of the named store
SEARCH_RADIUS_KM = 15.0

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert an address to latitude and longitude using Nominatim API
    
    Args:
        address: Address string (e.g., "Walmart, Ann Arbor, MI")
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    
    Raises:
        Requests error if API call fails
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }
    
    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            return None
        
        # Extract latitude and longitude from first result
        result = data[0]
        latitude = float(result["lat"])
        longitude = float(result["lon"])
        
        return (latitude, longitude)
    
    except requests.exceptions.RequestException as e:
        print(f"Geocoding error: {e}")
        return None

def geocode_store_name(store_name: str) -> Optional[Tuple[float, float]]:
    """
    Convert a store name to coordinates
    
    Args:
        store_name: Store name (e.g., "Walmart")
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    return geocode_address(store_name)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    
    Args:
        lat1, lon1: First coordinate (user location)
        lat2, lon2: Second coordinate (store location)
    
    Returns:
        Distance in kilometers
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    
    return c * r

# ---------------------------------------------------------------------------
# Find the nearest branch of a named store (e.g. "Walmart") around the user.
#
# Nominatim's public service allows at most 1 request per second for the whole
# app and asks clients to cache results, so lookups are throttled and the raw
# candidate list is cached per (store name, ~1 km grid cell).
# ---------------------------------------------------------------------------
_MIN_INTERVAL_SECONDS = 1.1
_throttle_lock = threading.Lock()
_last_call = 0.0

_CACHE_MAX_ENTRIES = 500
_cache: dict = {}


def _throttle() -> None:
    """Block until at least _MIN_INTERVAL_SECONDS have passed since the last request."""
    global _last_call
    with _throttle_lock:
        wait = _MIN_INTERVAL_SECONDS - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _viewbox(lat: float, lon: float, radius_km: float) -> str:
    """Nominatim viewbox 'left,top,right,bottom' (lon,lat,lon,lat) around a point."""
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(cos(radians(lat)), 0.01))
    return f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}"


def find_nearest_store(
    name: str, latitude: float, longitude: float, radius_km: float = SEARCH_RADIUS_KM
) -> Optional[dict]:
    """
    Find the branch of `name` closest to (latitude, longitude), within radius_km.

    Returns {"name", "address", "latitude", "longitude", "distance_km"} or None if the
    lookup failed or nothing was found nearby. Never raises.
    """
    key = (name.strip().lower(), round(latitude, 2), round(longitude, 2), radius_km)

    candidates = _cache.get(key)
    if candidates is None:
        params = {
            "q": name,
            "format": "jsonv2",
            "limit": 40,
            "bounded": 1,
            "viewbox": _viewbox(latitude, longitude, radius_km),
        }
        try:
            _throttle()
            response = requests.get(
                NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=6
            )
            response.raise_for_status()
            results = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Store lookup error: {e}")
            return None  # failures are not cached, so a later attempt can succeed

        candidates = []
        for item in results if isinstance(results, list) else []:
            try:
                candidates.append(
                    {
                        "name": item.get("name") or name,
                        "address": item.get("display_name"),
                        "latitude": float(item["lat"]),
                        "longitude": float(item["lon"]),
                    }
                )
            except (KeyError, TypeError, ValueError, AttributeError):
                continue

        if len(_cache) >= _CACHE_MAX_ENTRIES:
            _cache.clear()
        _cache[key] = candidates

    best = None
    for c in candidates:
        distance = calculate_distance(latitude, longitude, c["latitude"], c["longitude"])
        if distance <= radius_km and (best is None or distance < best["distance_km"]):
            best = {**c, "distance_km": round(distance, 2)}
    return best
