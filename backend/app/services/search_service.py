from app.core.database import get_db
from app.services.ai_service import get_image_embedding
from typing import List


def search_by_image_url(image_url: str, top_k: int = 10) -> List[dict]:
    """
    Nhận URL ảnh → tạo embedding bằng CLIP → tìm sản phẩm tương đồng trong pgvector.
    Trả về top_k sản phẩm giống nhất theo Cosine Similarity.
    """
    embedding = get_image_embedding(image_url)
    if embedding is None:
        return []

    return _vector_search(embedding, top_k)


def search_by_embedding(embedding: list, top_k: int = 10) -> List[dict]:
    """
    Nhận trực tiếp embedding vector (từ ảnh người dùng chụp) → tìm sản phẩm tương đồng.
    Dùng cho luồng: App upload ảnh → Backend xử lý → Trả kết quả.
    """
    if embedding is None:
        return []

    return _vector_search(embedding, top_k)


def _vector_search(embedding: list, top_k: int) -> List[dict]:
    """
    Thực hiện truy vấn pgvector để tìm kiếm sản phẩm theo cosine similarity.
    Công thức: 1 - (embedding <=> query_vector) = cosine similarity score
    """
    sql = """
        SELECT
            id,
            title,
            shop_name,
            price,
            image_url,
            detail_link,
            affiliate_link,
            1 - (embedding <=> %s::vector) AS similarity_score
        FROM decor_items
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    with get_db() as (conn, cur):
        cur.execute(sql, (embedding, embedding, top_k))
        rows = cur.fetchall()

    return [dict(row) for row in rows]
