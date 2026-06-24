import requests
import json

@st.cache_data(ttl=86400)  # cache for 24 hours
def get_jakarta_boundaries():
    """
    Fetch Jakarta city boundaries from OpenStreetMap via Overpass API.
    Returns GeoJSON FeatureCollection with 5 city regions.
    """
    # Overpass query for Jakarta administrative boundaries level 5
    query = """
    [out:json][timeout:30];
    (
      relation["name"="Jakarta Pusat"]["admin_level"="5"];
      relation["name"="Jakarta Selatan"]["admin_level"="5"];
      relation["name"="Jakarta Utara"]["admin_level"="5"];
      relation["name"="Jakarta Timur"]["admin_level"="5"];
      relation["name"="Jakarta Barat"]["admin_level"="5"];
    );
    out geom;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    resp = requests.post(url, data=query, timeout=30)
    
    if resp.status_code != 200:
        return None
    
    return resp.json()