# backend/main.py
# @author: Memba Co.

import logging
import uvicorn
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database
from tools import exchange as exchange_tools
from core import agent, scanner, position_manager, app_config
from core.security import get_current_user
from api import (
    analysis_router,
    auth_router,
    charts_router,
    dashboard_router,
    positions_router,
    scanner_router,
    settings_router,
    backtest_router,
    presets_router,
)
from telegram_bot import create_telegram_app

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü yöneticisi."""
    logging.info("Uygulama başlatılıyor (lifespan)...")
    
    app.state.scheduler = scheduler
    database.init_db()
    app_config.load_config()
    
    try:
        exchange_tools.initialize_exchange(app_config.settings.get('DEFAULT_MARKET_TYPE'))
        logging.info(f"--- BAŞLANGIÇ KONTROLÜ --- Borsa bağlantı objesi durumu: {'Kuruldu' if exchange_tools.exchange else '!!! KURULAMADI (None) !!!'}")
        if not exchange_tools.exchange:
            raise ConnectionError("Borsa bağlantısı initialize edilemedi ancak hata fırlatmadı. .env dosyasını kontrol edin.")
            
    except Exception as e:
        logging.critical(f"--- KRİTİK BAŞLANGIÇ HATASI --- Borsa bağlantısı kurulamadı: {e}", exc_info=True)
        database.log_event("CRITICAL", "Application", f"Uygulama başlatılamadı: Borsa bağlantı hatası - {e}")
        raise e

    agent.initialize_agent()
    
    try:
        database.log_event("INFO", "Sync", "Başlangıçta pozisyon senkronizasyonu başlatıldı.")
        await position_manager.sync_positions_with_exchange()
    except Exception as e:
        error_msg = f"Başlangıçta pozisyon senkronizasyonu başarısız oldu: {e}"
        logging.critical(error_msg)
        database.log_event("CRITICAL", "Sync", error_msg)
    
    telegram_app = create_telegram_app()
    if telegram_app:
        app.state.telegram_app = telegram_app
        await telegram_app.initialize()
        await telegram_app.updater.start_polling()
        await telegram_app.start()
        logging.info("Telegram botu başlatıldı ve komutları dinliyor.")
        database.log_event("INFO", "Telegram", "Telegram botu başarıyla başlatıldı.")
    
    logging.info("Arka plan görevleri (Scheduler) ayarlanıyor...")
    scheduler.add_job(position_manager.sync_positions_with_exchange, "interval", seconds=app_config.settings.get('POSITION_SYNC_INTERVAL_SECONDS', 300), id="position_sync_job", max_instances=1)
    scheduler.add_job(position_manager.check_all_managed_positions, "interval", seconds=app_config.settings.get('POSITION_CHECK_INTERVAL_SECONDS', 60), id="position_checker_job", max_instances=1)
    scheduler.add_job(position_manager.check_for_orphaned_orders, "interval", seconds=app_config.settings.get('ORPHAN_ORDER_CHECK_INTERVAL_SECONDS', 300), id="orphan_order_job", max_instances=1)
    if app_config.settings.get('PROACTIVE_SCAN_ENABLED'):
        scheduler.add_job(scanner.execute_single_scan_cycle, "interval", seconds=app_config.settings.get('PROACTIVE_SCAN_INTERVAL_SECONDS', 900), id="scanner_job", max_instances=1)
    
    scheduler.start()
    logging.info("Uygulama başlangıcı tamamlandı. API kullanıma hazır.")
    database.log_event("SUCCESS", "Application", "Uygulama başarıyla başlatıldı ve çalışıyor.")
    yield
    
    logging.info("Uygulama kapatılıyor (lifespan)...")
    database.log_event("INFO", "Application", "Uygulama kapatılıyor...")
    
    # DÜZELTME: Kapatma kontrolü, 'is_running' yerine 'running' özelliği ile yapılıyor.
    # Bu, 'AttributeError' hatasını çözer ve uygulamanın kararlı bir şekilde kapanmasını sağlar.
    if hasattr(app.state, "telegram_app") and app.state.telegram_app.running:
        await app.state.telegram_app.updater.stop()
        await app.state.telegram_app.stop()
        await app.state.telegram_app.shutdown()
        logging.info("Telegram botu durduruldu.")
        
    scheduler.shutdown()
    logging.info("Arka plan görevleri (Scheduler) kapatıldı.")


app = FastAPI(title="Gemini Trading Agent API", version="4.5.4", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(backtest_router, dependencies=[Depends(get_current_user)])
api_router.include_router(charts_router, dependencies=[Depends(get_current_user)])
api_router.include_router(analysis_router, dependencies=[Depends(get_current_user)])
api_router.include_router(positions_router, dependencies=[Depends(get_current_user)])
api_router.include_router(dashboard_router, dependencies=[Depends(get_current_user)])
api_router.include_router(settings_router, dependencies=[Depends(get_current_user)])
api_router.include_router(scanner_router, dependencies=[Depends(get_current_user)])
api_router.include_router(presets_router, dependencies=[Depends(get_current_user)])
app.include_router(api_router)

try:
    static_files_path = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_files_path):
        app.mount('/assets', StaticFiles(directory=os.path.join(static_files_path, "assets")), name='assets')
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_react_app(full_path: str):
            index_path = os.path.join(static_files_path, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="index.html not found")
    else:
        logging.warning(f"Statik dosyalar ('{static_files_path}') bulunamadı. Sadece API modunda çalışılıyor.")
except Exception:
    logging.warning("Statik dosya yolu ayarlanırken hata oluştu. Sadece API modunda çalışılıyor.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
