from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from jobs.auto_scraper_ai import run_scraper_job
from app.core.config import settings

router = APIRouter()

@router.post("/cron/run-scraper", tags=["Cronjobs"])
def trigger_scraper(background_tasks: BackgroundTasks, x_api_key: str = Header(...)):
    """
    Endpoint kích hoạt job cào dữ liệu và cập nhật embedding vào Vector DB.
    Được bảo vệ bằng Header `X-API-KEY`.
    Job sẽ chạy ngầm bằng BackgroundTasks để tránh timeout Request từ phía dịch vụ Cron.
    """
    if x_api_key != settings.API_KEY_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Sai API Key")
        
    # Thêm hàm scraper vào hàng đợi chạy ngầm của FastAPI
    background_tasks.add_task(run_scraper_job)
    
    return {
        "status": "pending",
        "message": "Cronjob cào dữ liệu đang chạy ngầm..."
    }
