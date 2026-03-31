import requests
import time
from app.core.config import settings
from app.core.database import get_db
from app.services.ai_service import get_image_embedding

HEADERS_CRAWL = {
    'accept': 'application/json, text/plain, */*',
    'authorization': f'Bearer {settings.BEARER_TOKEN}',
    'origin': 'https://pub2.accesstrade.vn'
}

SORT_FIELDS = ["RECOMMENDED", "BEST_SELLERS", "HIGH_COMMISSIOM_RATE"]


def generate_affiliate_link(raw_url: str) -> str:
    """Chuyển đổi link TikTok gốc thành link Affiliate AccessTrade."""
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
            return data.get("short_link") or data.get("url") or raw_url
    except Exception:
        pass
    return raw_url


def run_scraper_job() -> dict:
    """
    Cronjob chính: Cào sản phẩm từ AccessTrade TikTok Shop API,
    tạo embedding bằng CLIP, lưu vào pgvector Database.
    """
    total_inserted = 0
    total_skipped = 0

    for sort_field in SORT_FIELDS:
        current_page_token = ""
        pages_scraped = 0

        while pages_scraped < 2:
            url = (
                f"https://pub2-api.accesstrade.vn/v1/tools/tiktok-shop-products"
                f"?sort_field={sort_field}&sort_order=DESC&limit=20"
            )
            if current_page_token:
                url += f"&page_token={current_page_token}"

            try:
                res = requests.get(url, headers=HEADERS_CRAWL, timeout=15)
                if res.status_code != 200:
                    break

                data = res.json()
                products = data.get("data", {}).get("products", [])

                for p in products:
                    product_id = p.get("id")
                    title = p.get("title")
                    if not product_id or not title:
                        continue

                    # Kiểm tra trùng lặp
                    with get_db() as (conn, cur):
                        cur.execute("SELECT 1 FROM decor_items WHERE id = %s", (product_id,))
                        if cur.fetchone():
                            total_skipped += 1
                            continue

                    # Tạo embedding từ ảnh sản phẩm
                    image_url = p.get("main_image_url")
                    vector_embedding = get_image_embedding(image_url)
                    if vector_embedding is None:
                        continue

                    # Tạo affiliate link
                    raw_link = p.get("detail_link", "")
                    aff_link = generate_affiliate_link(raw_link)

                    price = p.get("sales_price", {}).get("minimum_amount")
                    shop_name = p.get("shop", {}).get("name")

                    # Lưu vào Database
                    insert_sql = """
                        INSERT INTO decor_items (id, title, shop_name, price, image_url, affiliate_link, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                    """
                    with get_db() as (conn, cur):
                        cur.execute(insert_sql, (
                            product_id, title, shop_name, price,
                            image_url, aff_link, vector_embedding
                        ))
                    total_inserted += 1

                current_page_token = data.get("data", {}).get("next_page_token", "")
                pages_scraped += 1

                if not current_page_token:
                    break

                time.sleep(1)

            except Exception as e:
                print(f"[Scraper] Lỗi khi cào trang {sort_field}: {e}")
                break

    msg = f"Hoàn thành Cronjob! Đã nạp mới: {total_inserted} SP | Đã bỏ qua: {total_skipped} SP"
    print(f"✅ {msg}")
    return {"status": "success", "inserted": total_inserted, "skipped": total_skipped, "message": msg}


if __name__ == "__main__":
    run_scraper_job()
