from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt as pyjwt
from datetime import datetime, timedelta
import os

from app.core.database import get_db
from app.models.schemas import UserCreate, UserResponse, LoginRequest, Token, SaveItemRequest, SavedItemResponse
from typing import List

router = APIRouter(tags=["Users"])

# ---- Auth Config ----
SECRET_KEY = os.getenv("SECRET_KEY", "pricelens-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 ngày

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return pyjwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> int:
    """Dependency: Giải mã Bearer Token, trả về user_id. Dùng cho các route cần đăng nhập."""
    try:
        payload = pyjwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (pyjwt.PyJWTError, KeyError):
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")


# ==============================================================================
# AUTH ENDPOINTS
# ==============================================================================

@router.post("/auth/register", response_model=UserResponse, summary="Đăng ký tài khoản")
def register(body: UserCreate):
    with get_db() as (conn, cur):
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email đã được đăng ký")

        cur.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s) RETURNING *",
            (body.email, _hash_password(body.password), body.full_name)
        )
        user = cur.fetchone()

    return dict(user)


@router.post("/auth/login", response_model=Token, summary="Đăng nhập")
def login(body: LoginRequest):
    with get_db() as (conn, cur):
        cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
        user = cur.fetchone()

    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    return Token(access_token=_create_token(user["id"]))


@router.get("/me", response_model=UserResponse, summary="Thông tin tài khoản hiện tại")
def get_me(user_id: int = Depends(get_current_user_id)):
    with get_db() as (conn, cur):
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    return dict(user)


# ==============================================================================
# WISHLIST ENDPOINTS
# ==============================================================================

@router.post("/wishlist", summary="Lưu sản phẩm vào Wishlist")
def save_item(body: SaveItemRequest, user_id: int = Depends(get_current_user_id)):
    with get_db() as (conn, cur):
        cur.execute(
            "INSERT INTO saved_items (user_id, item_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, body.item_id)
        )
    return {"status": "saved", "item_id": body.item_id}


@router.delete("/wishlist/{item_id}", summary="Xóa sản phẩm khỏi Wishlist")
def remove_saved_item(item_id: str, user_id: int = Depends(get_current_user_id)):
    with get_db() as (conn, cur):
        cur.execute(
            "DELETE FROM saved_items WHERE user_id = %s AND item_id = %s",
            (user_id, item_id)
        )
    return {"status": "removed", "item_id": item_id}


@router.get("/wishlist", summary="Lấy danh sách sản phẩm đã lưu")
def get_wishlist(user_id: int = Depends(get_current_user_id)):
    sql = """
        SELECT d.*, s.saved_at
        FROM saved_items s
        JOIN decor_items d ON d.id = s.item_id
        WHERE s.user_id = %s
        ORDER BY s.saved_at DESC;
    """
    with get_db() as (conn, cur):
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


# ==============================================================================
# SCAN HISTORY ENDPOINTS
# ==============================================================================

@router.get("/history", summary="Lịch sử quét Camera AI")
def get_scan_history(user_id: int = Depends(get_current_user_id)):
    sql = """
        SELECT h.id, h.scanned_image_url, h.scanned_at,
               d.id AS item_id, d.title, d.price, d.image_url, d.affiliate_link
        FROM scan_history h
        LEFT JOIN decor_items d ON d.id = h.matched_item_id
        WHERE h.user_id = %s
        ORDER BY h.scanned_at DESC
        LIMIT 50;
    """
    with get_db() as (conn, cur):
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()
    return [dict(r) for r in rows]
