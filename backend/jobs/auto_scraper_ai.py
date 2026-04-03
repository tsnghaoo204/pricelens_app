import requests
import time
from typing import List, Optional
from app.core.config import settings
from app.core.database import get_db
from app.services.ai_service import get_image_embedding

HEADERS_CRAWL = {
    'accept': 'application/json, text/plain, */*',
    'authorization': f'Bearer {settings.BEARER_TOKEN}',
    'origin': 'https://pub2.accesstrade.vn'
}

SORT_FIELDS = ["RECOMMENDED", "BEST_SELLERS", "HIGH_COMMISSIOM_RATE"]


def _short_text(value: str, limit: int = 80) -> str:
    if not value:
        return ""
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _normalize_sort_fields(sort_fields: Optional[List[str]]) -> List[str]:
    if not sort_fields:
        return SORT_FIELDS

    valid = set(SORT_FIELDS)
    normalized = []
    for field in sort_fields:
        key = (field or "").strip().upper()
        if key in valid and key not in normalized:
            normalized.append(key)
    return normalized


def run_scraper_job(sort_fields: Optional[List[str]] = None) -> dict:
    """
    Cronjob chính: Cào sản phẩm từ AccessTrade TikTok Shop API,
    tạo embedding bằng CLIP, lưu vào pgvector Database.
    """
    active_sort_fields = _normalize_sort_fields(sort_fields)
    if not active_sort_fields:
        msg = f"Không có sort_field hợp lệ. Chấp nhận: {', '.join(SORT_FIELDS)}"
        print(f"[Scraper][ERROR] {msg}")
        return {"status": "error", "inserted": 0, "skipped": 0, "message": msg}

    total_inserted = 0
    total_skipped = 0
    total_skipped_in_run = 0
    seen_product_ids = set()

    for sort_field in active_sort_fields:
        current_page_token = ""
        pages_scraped = 0
        seen_page_tokens = set()

        while True:
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
                payload = data.get("data") or {}
                products = payload.get("products") or []

                for p in products:
                    product_id = p.get("id")
                    title = p.get("title")
                    if not product_id or not title:
                        print(f"[Scraper][SKIP][missing_required] sort={sort_field} id={product_id} title={_short_text(title)}")
                        continue

                    if product_id in seen_product_ids:
                        total_skipped_in_run += 1
                        print(f"[Scraper][SKIP][duplicate_in_run] sort={sort_field} id={product_id} title={_short_text(title)}")
                        continue

                    seen_product_ids.add(product_id)

                    # Kiểm tra trùng lặp
                    with get_db() as (conn, cur):
                        cur.execute("SELECT 1 FROM decor_items WHERE id = %s", (product_id,))
                        if cur.fetchone():
                            total_skipped += 1
                            print(f"[Scraper][SKIP][duplicate] sort={sort_field} id={product_id} title={_short_text(title)}")
                            continue

                    # Tạo embedding từ ảnh sản phẩm
                    image_url = p.get("main_image_url")
                    vector_embedding = get_image_embedding(image_url)
                    if vector_embedding is None:
                        print(f"[Scraper][SKIP][no_embedding] sort={sort_field} id={product_id} title={_short_text(title)} image_url={image_url}")
                        continue

                    # Lưu link gốc, không tạo affiliate trong cronjob
                    raw_link = p.get("detail_link") or ""

                    sales_price = p.get("sales_price") or {}
                    shop_info = p.get("shop") or {}
                    price = sales_price.get("minimum_amount")
                    shop_name = shop_info.get("name")

                    # Lưu vào Database
                    insert_sql = """
                        INSERT INTO decor_items (id, title, shop_name, price, image_url, detail_link, affiliate_link, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                    """
                    with get_db() as (conn, cur):
                        cur.execute(insert_sql, (
                            product_id, title, shop_name, price,
                            image_url, raw_link, None, vector_embedding
                        ))
                    total_inserted += 1
                    print(
                        "[Scraper][INSERT] "
                        f"sort={sort_field} id={product_id} title={_short_text(title)} "
                        f"shop={_short_text(shop_name or '')} price={price}"
                    )

                next_page_token = payload.get("next_page_token", "")
                pages_scraped += 1

                if not next_page_token:
                    break

                if next_page_token in seen_page_tokens:
                    print(
                        f"[Scraper][WARN] Repeated page token detected sort={sort_field} "
                        f"token={next_page_token}; stopping to avoid infinite loop"
                    )
                    break

                seen_page_tokens.add(next_page_token)
                current_page_token = next_page_token

                time.sleep(1)

            except Exception as e:
                print(f"[Scraper][ERROR] sort={sort_field} page={pages_scraped} token={current_page_token} error={e}")
                break

    msg = (
        f"Hoàn thành Cronjob! Đã nạp mới: {total_inserted} SP | "
        f"Trùng DB: {total_skipped} SP | Trùng trong lần chạy: {total_skipped_in_run} SP"
    )
    print(f"✅ {msg}")
    return {
        "status": "success",
        "inserted": total_inserted,
        "skipped": total_skipped,
        "skipped_in_run": total_skipped_in_run,
        "sort_fields": active_sort_fields,
        "message": msg
    }


if __name__ == "__main__":
    run_scraper_job()
