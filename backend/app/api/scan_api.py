from fastapi import APIRouter, File, UploadFile, HTTPException
from PIL import Image
from io import BytesIO
import torch
from transformers import CLIPProcessor, CLIPModel

from app.core.database import get_db
from app.models.schemas import ScanResponse, ScanResultItem
from app.services.affiliate_service import generate_affiliate_link
from app.services.search_service import search_by_embedding

router = APIRouter(tags=["AI Scan"])

# Load CLIP model một lần duy nhất khi khởi động
_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


def _image_to_embedding(image_bytes: bytes) -> list:
    """Chuyển bytes ảnh từ Upload thành vector embedding 512 chiều."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = _processor(images=img, return_tensors="pt")
    with torch.no_grad():
        features = _model.get_image_features(**inputs)

    if hasattr(features, "pooler_output"):
        features = features.pooler_output
    elif hasattr(features, "image_embeds"):
        features = features.image_embeds

    return features.squeeze().tolist()


@router.post("/scan", response_model=ScanResponse, summary="Quét ảnh tìm sản phẩm tương đồng")
async def scan_product(
    file: UploadFile = File(..., description="Ảnh chụp từ camera của người dùng"),
    top_k: int = 10
):
    """
    **Luồng chính của app:**
    1. Nhận ảnh do người dùng chụp từ camera
    2. Tạo embedding vector 512 chiều bằng CLIP
    3. Tìm top {top_k} sản phẩm tương đồng nhất trong vector database
    4. Trả về danh sách sản phẩm kèm điểm tương đồng và affiliate link
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File phải là hình ảnh (jpg, png, webp,...)")

    image_bytes = await file.read()
    embedding = _image_to_embedding(image_bytes)
    raw_results = search_by_embedding(embedding, top_k=top_k)

    results = []
    for item in raw_results:
        affiliate_link = item.get("affiliate_link")
        if not affiliate_link and item.get("detail_link"):
            affiliate_link = generate_affiliate_link(item["detail_link"])

        results.append(ScanResultItem(
            id=item["id"],
            title=item["title"],
            shop_name=item.get("shop_name"),
            price=item.get("price"),
            image_url=item.get("image_url"),
            affiliate_link=affiliate_link,
            similarity_score=item["similarity_score"],
        ))

    return ScanResponse(results=results, total=len(results))


@router.get("/go/{item_id}", summary="Redirect đến Affiliate Link và tăng lượt click")
def go_to_affiliate(item_id: str):
    """
    **Tracking Affiliate Click:**
    - Khi người dùng bấm vào sản phẩm, app gọi endpoint này
    - Backend tăng click_count (có thể mở rộng sau) và redirect sang link Affiliate
    - Đây là cách theo dõi conversion và doanh thu affiliate
    """
    from fastapi.responses import RedirectResponse

    with get_db() as (conn, cur):
        cur.execute(
            "SELECT affiliate_link, detail_link FROM decor_items WHERE id = %s",
            (item_id,)
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

    target_url = row["affiliate_link"]
    if not target_url and row.get("detail_link"):
        target_url = generate_affiliate_link(row["detail_link"])

    if not target_url:
        raise HTTPException(status_code=404, detail="Sản phẩm không có link affiliate")

    # TODO: Lưu log click vào DB để phân tích sau
    return RedirectResponse(url=target_url, status_code=302)
