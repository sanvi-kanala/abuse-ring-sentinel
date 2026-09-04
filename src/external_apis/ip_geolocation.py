"""
ip_geolocation.py

Wraps the free ip-api.com geolocation endpoint (no API key required for the
free, non-commercial tier — 45 requests/minute). Used to compute a
"geographic dispersion" signal: a genuine friend/family cluster is usually
tightly clustered around one city, while a professional fraud ring often
signs up from IPs spread across unrelated regions (VPN/proxy rotation) OR
suspiciously from a single data-center IP block.

This module degrades gracefully: if the network call fails (rate-limited,
offline, or — as in this project's sandboxed dev environment — no egress to
ip-api.com), it falls back to a deterministic local mock so the rest of the
pipeline keeps working end to end.
"""
import logging
import requests

logger = logging.getLogger("abuse_ring_sentinel.ip_geo")

IP_API_URL = "http://ip-api.com/json/{ip}"


def lookup_ip(ip: str, timeout: float = 2.0) -> dict:
    """Returns {'ip', 'city', 'region', 'country', 'lat', 'lon', 'isp', 'is_mock'}"""
    try:
        resp = requests.get(IP_API_URL.format(ip=ip), timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return {
                "ip": ip, "city": data.get("city"), "region": data.get("regionName"),
                "country": data.get("country"), "lat": data.get("lat"), "lon": data.get("lon"),
                "isp": data.get("isp"), "is_mock": False,
            }
        raise ValueError(data.get("message", "ip-api lookup failed"))
    except Exception as e:
        logger.warning(f"ip-api.com lookup failed for {ip} ({e}); using local fallback")
        return _mock_lookup(ip)


def _mock_lookup(ip: str) -> dict:
    """Deterministic offline fallback so the pipeline is testable without
    network egress. Buckets the IP into a pseudo-region by hash so repeated
    lookups of the same IP are stable within a run."""
    bucket = abs(hash(ip)) % 8
    cities = ["Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad"]
    return {
        "ip": ip, "city": cities[bucket], "region": cities[bucket], "country": "India",
        "lat": None, "lon": None, "isp": "unknown", "is_mock": True,
    }


def geo_dispersion_score(ips: list) -> dict:
    """Given a cluster's list of signup IPs, return a summary of how
    geographically concentrated or dispersed they are."""
    locations = [lookup_ip(ip) for ip in ips]
    cities = {loc["city"] for loc in locations if loc.get("city")}
    return {
        "n_ips": len(ips),
        "n_unique_cities": len(cities),
        "cities": sorted(cities),
        "dispersion_ratio": (len(cities) / len(ips)) if ips else 0.0,
        "used_mock_fallback": any(loc.get("is_mock") for loc in locations),
    }
