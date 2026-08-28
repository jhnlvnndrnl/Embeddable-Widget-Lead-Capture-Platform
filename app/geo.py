import logging
import httpx
from typing import Optional, Tuple
from app.config import get_settings

logger = logging.getLogger("geo_enrichment")


async def fetch_from_provider_a(ip: str, client: httpx.AsyncClient) -> Optional[Tuple[str, str]]:
    """Provider A: ip-api.com (Free, no key required).
    Returns (country, city) or None on failure.
    """
    settings = get_settings()
    if settings.MOCK_GEO_PROVIDER_A_DOWN:
        logger.warning("[Geo Fallback] Provider A is mocked as DOWN.")
        return None

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,message,country,city"
        response = await client.get(url, timeout=2.5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                country = data.get("country")
                city = data.get("city")
                if country or city:
                    return country, city
    except Exception as exc:
        logger.warning(f"[Geo Fallback] Provider A failed for IP '{ip}': {exc}")

    return None


async def fetch_from_provider_b(ip: str, client: httpx.AsyncClient) -> Optional[Tuple[str, str]]:
    """Provider B: ipapi.co (Fallback provider).
    Returns (country, city) or None on failure.
    """
    settings = get_settings()
    if settings.MOCK_GEO_PROVIDER_B_DOWN:
        logger.warning("[Geo Fallback] Provider B is mocked as DOWN.")
        return None

    try:
        url = f"https://ipapi.co/{ip}/json/"
        response = await client.get(url, timeout=2.5, headers={"User-Agent": "FastAPI-Widget-App/1.0"})
        if response.status_code == 200:
            data = response.json()
            if not data.get("error"):
                country = data.get("country_name")
                city = data.get("city")
                if country or city:
                    return country, city
    except Exception as exc:
        logger.warning(f"[Geo Fallback] Provider B failed for IP '{ip}': {exc}")

    return None


async def enrich_ip(ip: Optional[str]) -> Tuple[Optional[str], Optional[str], str]:
    """Fallback Chain for IP Geolocation Enrichment.
    
    Order of execution:
      1. Tries Provider A (ip-api.com)
      2. If Provider A fails -> Tries Provider B (ipapi.co)
      3. If both fail -> Degrades gracefully without error (country=None, city=None, provider="none")
    
    Returns:
      (country, city, geo_provider)
    """
    if not ip or ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        # For localhost or test client, provide a friendly default or mock
        return "Localhost / Dev", "Local Environment", "local-dev"

    async with httpx.AsyncClient() as client:
        # Step 1: Attempt Provider A
        result_a = await fetch_from_provider_a(ip, client)
        if result_a:
            return result_a[0], result_a[1], "ip-api.com"

        # Step 2: Attempt Provider B (Fallback)
        result_b = await fetch_from_provider_b(ip, client)
        if result_b:
            return result_b[0], result_b[1], "ipapi.co"

    # Step 3: Graceful degradation (main request never fails)
    logger.info(f"[Geo Fallback] All geo providers unavailable for IP '{ip}'. Degrading gracefully.")
    return None, None, "none"
