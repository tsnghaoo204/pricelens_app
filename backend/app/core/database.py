import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from contextlib import contextmanager
from app.core.config import settings


def _create_connection():
    """Tạo một kết nối raw psycopg2 tới PostgreSQL kèm pgvector."""
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    register_vector(conn)  # Đăng ký Vector type để đọc/ghi VECTOR(512)
    return conn


@contextmanager
def get_db():
    """
    Context manager để dùng DB an toàn.
    - Tự động commit nếu thành công
    - Tự động rollback nếu có lỗi
    - Tự động đóng connection khi xong

    Cách dùng:
        with get_db() as (conn, cur):
            cur.execute("SELECT ...")
            rows = cur.fetchall()
    """
    conn = _create_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    """
    Khởi tạo toàn bộ schema Database (chỉ chạy 1 lần khi startup).
    Tạo extension pgvector và tất cả các bảng theo thiết kế.
    """
    sql = """
        -- Kích hoạt extension pgvector
        CREATE EXTENSION IF NOT EXISTS vector;

        -- Bảng Users
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Bảng sản phẩm decor tích hợp AI embedding
        CREATE TABLE IF NOT EXISTS decor_items (
            id VARCHAR(50) PRIMARY KEY,
            title TEXT NOT NULL,
            shop_name VARCHAR(255),
            price INTEGER,
            image_url TEXT,
            affiliate_link TEXT,
            embedding VECTOR(512),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Index HNSW cho tìm kiếm vector Cosine Similarity (cực nhanh)
        CREATE INDEX IF NOT EXISTS idx_decor_embedding
        ON decor_items
        USING hnsw (embedding vector_cosine_ops);

        -- Bảng Wishlist
        CREATE TABLE IF NOT EXISTS saved_items (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            item_id VARCHAR(50) REFERENCES decor_items(id) ON DELETE CASCADE,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, item_id)
        );

        -- Bảng Lịch sử quét Camera AI
        CREATE TABLE IF NOT EXISTS scan_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            scanned_image_url TEXT,
            matched_item_id VARCHAR(50) REFERENCES decor_items(id) ON DELETE SET NULL,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes cho query nhanh trên mobile
        CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_items(user_id);
        CREATE INDEX IF NOT EXISTS idx_history_user ON scan_history(user_id);
    """
    with get_db() as (conn, cur):
        cur.execute(sql)
    print("✅ Database schema initialized successfully!")
