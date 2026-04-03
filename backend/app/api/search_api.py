from fastapi import APIRouter, Header, HTTPException, BackgroundTasks, Query
from jobs.auto_scraper_ai import run_scraper_job
from app.core.config import settings

router = APIRouter()

@router.post("/cron/run-scraper", tags=["Cronjobs"])
def trigger_scraper(
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(...),
    sort_field: str | None = Query(default=None, description="Ví dụ: RECOMMENDED hoặc BEST_SELLERS,HIGH_COMMISSIOM_RATE")
):
    """
    Endpoint kích hoạt job cào dữ liệu và cập nhật embedding vào Vector DB.
    Được bảo vệ bằng Header `X-API-KEY`.
    Job sẽ chạy ngầm bằng BackgroundTasks để tránh timeout Request từ phía dịch vụ Cron.
    """
    if x_api_key != settings.API_KEY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Sai API Key")

    sort_fields = None
    if sort_field:
        sort_fields = [s.strip() for s in sort_field.split(",") if s.strip()]
        
    # Thêm hàm scraper vào hàng đợi chạy ngầm của FastAPI
    background_tasks.add_task(run_scraper_job, sort_fields)
    
    return {
        "status": "pending",
        "sort_field": sort_fields or "ALL",
        "message": "Cronjob cào dữ liệu đang chạy ngầm..."
    }
