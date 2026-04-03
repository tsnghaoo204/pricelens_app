import requests
from typing import Optional

from app.core.config import settings


def generate_affiliate_link(raw_url: str) -> Optional[str]:
    """Chuyển đổi link gốc thành link Affiliate AccessTrade."""
    if not raw_url:
        return None

    api_url = "https://pub2-api.accesstrade.vn/v1/product_link/core-create"
    headers = {
        "authorization": f"Bearer {settings.BEARER_TOKEN}",
        "content-type": "application/json",
        "origin": "https://pub2.accesstrade.vn"
    }
    payload = {
        "original_url": raw_url,
        "tracking_domain": "go.isclix.com",
        "short_link": "https://shorten.asia",
        "create_shorten": "1",
        "sub4": "bot_decor_ai",
        "campaign_id": settings.CAMPAIGN_ID
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", {})
            candidate = (
                data.get("short_affiliate_link")
                or data.get("affiliate_link")
                or data.get("short_link")
                or data.get("url")
            )
            if candidate and candidate != raw_url:
                return candidate
    except Exception:
        pass
    return None