import sys
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Bảo đảm Python nhận diện thư mục backend/ làm root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.api import search_api, scan_api, user_api
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo database schema khi ứng dụng startup."""
    print("🚀 PriceLens API đang khởi động...")
    init_db()
    yield
    print("🛑 PriceLens API đã tắt.")


app = FastAPI(
    title="PriceLens API",
    description="AI-powered product scanner with affiliate link tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# Đăng ký các router
app.include_router(search_api.router, prefix="/api/v1")
app.include_router(scan_api.router,   prefix="/api/v1")
app.include_router(user_api.router,   prefix="/api/v1")


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "PriceLens API is up and running! 🚀"}

