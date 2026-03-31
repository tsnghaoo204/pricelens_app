from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ==============================================================================
# USER SCHEMAS
# ==============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ==============================================================================
# DECOR ITEM SCHEMAS
# ==============================================================================

class DecorItemBase(BaseModel):
    id: str
    title: str
    shop_name: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    affiliate_link: Optional[str] = None

class DecorItemResponse(DecorItemBase):
    created_at: datetime

    class Config:
        from_attributes = True

class ScanResultItem(BaseModel):
    """Kết quả trả về khi AI scan ảnh - kèm điểm tương đồng"""
    id: str
    title: str
    shop_name: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    affiliate_link: Optional[str] = None
    similarity_score: float  # Điểm tương đồng từ vector search (0.0 - 1.0)

class ScanResponse(BaseModel):
    results: List[ScanResultItem]
    total: int


# ==============================================================================
# SCAN HISTORY SCHEMAS
# ==============================================================================

class ScanHistoryResponse(BaseModel):
    id: int
    user_id: int
    scanned_image_url: Optional[str] = None
    matched_item: Optional[DecorItemResponse] = None
    scanned_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# SAVED ITEMS (WISHLIST) SCHEMAS
# ==============================================================================

class SaveItemRequest(BaseModel):
    item_id: str

class SavedItemResponse(BaseModel):
    item: DecorItemResponse
    saved_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# CRONJOB / ADMIN SCHEMAS
# ==============================================================================

class DecorItemUpsert(BaseModel):
    """Dùng cho cronjob khi đẩy dữ liệu sản phẩm mới vào hệ thống"""
    id: str
    title: str
    shop_name: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    affiliate_link: Optional[str] = None
