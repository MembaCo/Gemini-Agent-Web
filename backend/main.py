# ==============================================================================
# File: backend/main.py
# @author: Memba Co.
# ==============================================================================
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
    logging.info("Uygulama başlatılıyor (lifespan)...")
    
    app.state.scheduler = scheduler

    database.init_db()
    app_config.load_config()
    
    # Global borsa örneğini başlat
    exchange_tools.initialize_exchange(app_config.settings.get('DEFAULT_MARKET_TYPE'))
    
    # Scanner modülü artık sınıf tabanlı olmadığından, ayrıca başlatılmasına gerek yoktur.
    
    agent.initialize_agent()
    
    try:
        position_manager.sync_positions_on_startup()
    except Exception as e:
        logging.critical(f"Uygulama başlangıcında pozisyon senkronizasyonu başarısız oldu: {e}")
    
    telegram_app = create_telegram_app()
    if telegram_app:
        app.state.telegram_app = telegram_app
        await telegram_app.initialize()
        await telegram_app.start()
        asyncio.create_task(telegram_app.updater.start_polling())
        logging.info("Telegram botu başlatıldı ve komutları dinliyor.")
    
    logging.info("Arka plan görevleri (Scheduler) ayarlanıyor...")
    scheduler.add_job(
        position_manager.check_all_managed_positions, 
        "interval", 
        seconds=app_config.settings.get('POSITION_CHECK_INTERVAL_SECONDS', 60), 
        id="position_checker_job",
        max_instances=1
    )
    if app_config.settings.get('PROACTIVE_SCAN_ENABLED'):
        scheduler.add_job(
            scanner.execute_single_scan_cycle, 
            "interval", 
            seconds=app_config.settings.get('PROACTIVE_SCAN_INTERVAL_SECONDS', 900), 
            id="scanner_job",
            max_instances=1
        )
    
    scheduler.start()
    logging.info("Uygulama başlangıcı tamamlandı. API kullanıma hazır.")
    yield
    logging.info("Uygulama kapatılıyor (lifespan)...")
    if hasattr(app.state, "telegram_app") and app.state.telegram_app and hasattr(app.state.telegram_app, 'updater') and app.state.telegram_app.updater.running:
        await app.state.telegram_app.updater.stop()
        await app.state.telegram_app.stop()
        await app.state.telegram_app.shutdown()
        logging.info("Telegram botu durduruldu.")
    scheduler.shutdown()

app = FastAPI(title="Gemini Trading Agent API", version="4.0.0", lifespan=lifespan)
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

# === STATİK DOSYA SUNMA BÖLÜMÜ DÜZELTİLDİ ===
try:
    # Dockerfile, frontend dosyalarını /app/static içine koyduğu için
    # doğrudan bu klasörü hedefliyoruz.
    # main.py /app içinde çalıştığı için, göreceli yol /app/static olur.
    static_files_path = os.path.join(os.path.dirname(__file__), "static")
    
    if os.path.exists(static_files_path):
        # '/assets' yolunu /app/static/assets klasörüne bağla
        app.mount('/assets', StaticFiles(directory=os.path.join(static_files_path, "assets")), name='assets')
        
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_react_app(full_path: str):
            index_path = os.path.join(static_files_path, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            # Eğer index.html bulunamazsa 404 hatası ver
            raise HTTPException(status_code=404, detail="index.html not found")
    else:
        logging.warning(f"Statik dosyalar ('{static_files_path}') bulunamadı. Sadece API modunda çalışılıyor.")

except Exception:
    logging.warning("Statik dosya yolu ayarlanırken hata oluştu. Sadece API modunda çalışılıyor.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
