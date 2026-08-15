import requests
from typing import Optional, Tuple

# Nominatim API base URL
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

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
        "User-Agent": "LocationTodoApp/1.0"
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