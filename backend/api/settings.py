# backend/api/settings.py
# @author: Memba Co.

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

import database
from core import app_config, scanner, agent, position_manager
from config import APP_VERSION as CONFIG_APP_VERSION

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)

class SettingsUpdate(BaseModel):
    GEMINI_MODEL: Optional[str] = None
    GEMINI_MODEL_FALLBACK_ORDER: Optional[List[str]] = None
    LIVE_TRADING: Optional[bool] = None
    DEFAULT_MARKET_TYPE: Optional[str] = None
    DEFAULT_ORDER_TYPE: Optional[str] = None
    USE_MTA_ANALYSIS: Optional[bool] = None
    MTA_TREND_TIMEFRAME: Optional[str] = None
    LEVERAGE: Optional[float] = None
    RISK_PER_TRADE_PERCENT: Optional[float] = None
    MAX_CONCURRENT_TRADES: Optional[int] = None
    USE_ATR_FOR_SLTP: Optional[bool] = None
    ATR_MULTIPLIER_SL: Optional[float] = None
    RISK_REWARD_RATIO_TP: Optional[float] = None
    USE_TRAILING_STOP_LOSS: Optional[bool] = None
    TRAILING_STOP_ACTIVATION_PERCENT: Optional[float] = None
    USE_PARTIAL_TP: Optional[bool] = None
    PARTIAL_TP_TARGET_RR: Optional[float] = None
    PARTIAL_TP_CLOSE_PERCENT: Optional[float] = None
    POSITION_CHECK_INTERVAL_SECONDS: Optional[int] = None
    ORPHAN_ORDER_CHECK_INTERVAL_SECONDS: Optional[int] = None # YENİ
    PROACTIVE_SCAN_ENABLED: Optional[bool] = None
    PROACTIVE_SCAN_INTERVAL_SECONDS: Optional[int] = None
    PROACTIVE_SCAN_AUTO_CONFIRM: Optional[bool] = None
    PROACTIVE_SCAN_IN_LOOP: Optional[bool] = None
    PROACTIVE_SCAN_USE_GAINERS_LOSERS: Optional[bool] = None
    PROACTIVE_SCAN_TOP_N: Optional[int] = None
    PROACTIVE_SCAN_MIN_VOLUME_USDT: Optional[int] = None
    PROACTIVE_SCAN_MTA_ENABLED: Optional[bool] = None
    PROACTIVE_SCAN_ENTRY_TIMEFRAME: Optional[str] = None
    PROACTIVE_SCAN_TREND_TIMEFRAME: Optional[str] = None
    PROACTIVE_SCAN_BLACKLIST: Optional[List[str]] = None
    PROACTIVE_SCAN_WHITELIST: Optional[List[str]] = None
    TELEGRAM_ENABLED: Optional[bool] = None
    PROACTIVE_SCAN_USE_VOLUME_SPIKE: Optional[bool] = None
    PROACTIVE_SCAN_VOLUME_TIMEFRAME: Optional[str] = None
    PROACTIVE_SCAN_VOLUME_MULTIPLIER: Optional[float] = None
    PROACTIVE_SCAN_VOLUME_PERIOD: Optional[int] = None

def reschedule_jobs(scheduler, new_settings: dict):
    """Çalışan scheduler görevlerini yeni ayarlara göre günceller."""
    try:
        if 'GEMINI_MODEL' in new_settings or 'GEMINI_MODEL_FALLBACK_ORDER' in new_settings:
            agent.initialize_agent()
            logging.info("Gemini modeli veya yedek listesi değişti. AI ajanı yeni ayarlarla yeniden başlatıldı.")
            
        if 'POSITION_CHECK_INTERVAL_SECONDS' in new_settings:
            scheduler.reschedule_job(
                "position_checker_job",
                trigger="interval",
                seconds=new_settings['POSITION_CHECK_INTERVAL_SECONDS']
            )
            logging.info(f"Pozisyon kontrol görevi yeni interval ile yeniden zamanlandı: {new_settings['POSITION_CHECK_INTERVAL_SECONDS']} saniye.")

        # YENİ: Yetim emir kontrol görevinin zamanlamasını güncelle
        if 'ORPHAN_ORDER_CHECK_INTERVAL_SECONDS' in new_settings:
            scheduler.reschedule_job(
                "orphan_order_job",
                trigger="interval",
                seconds=new_settings['ORPHAN_ORDER_CHECK_INTERVAL_SECONDS']
            )
            logging.info(f"Yetim emir kontrol görevi yeni interval ile yeniden zamanlandı: {new_settings['ORPHAN_ORDER_CHECK_INTERVAL_SECONDS']} saniye.")

        if 'PROACTIVE_SCAN_ENABLED' in new_settings or 'PROACTIVE_SCAN_INTERVAL_SECONDS' in new_settings:
            scanner_job = scheduler.get_job("scanner_job")
            is_enabled = app_config.settings['PROACTIVE_SCAN_ENABLED']
            interval = app_config.settings['PROACTIVE_SCAN_INTERVAL_SECONDS']

            if is_enabled:
                if scanner_job:
                    scheduler.reschedule_job("scanner_job", trigger="interval", seconds=interval)
                    logging.info(f"Tarayıcı görevi yeni interval ile yeniden zamanlandı: {interval} saniye.")
                else:
                    scheduler.add_job(scanner.execute_single_scan_cycle, "interval", seconds=interval, id="scanner_job", max_instances=1)
                    logging.info("Tarayıcı görevi etkinleştirildi ve zamanlandı.")
            elif scanner_job:
                scheduler.remove_job("scanner_job")
                logging.info("Tarayıcı görevi devre dışı bırakıldı ve kaldırıldı.")

    except Exception as e:
        logging.error(f"Scheduler görevleri yeniden zamanlanırken hata oluştu: {e}", exc_info=True)


@router.get("/", summary="Tüm uygulama ayarlarını al")
async def get_settings():
    try:
        settings = database.get_all_settings()
        settings['APP_VERSION'] = CONFIG_APP_VERSION
        return settings
    except Exception as e:
        logging.error(f"Ayarlar okunurken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sunucu ayarları okunurken bir sunucu hatası oluştu.")


@router.put("/", summary="Uygulama ayarlarını güncelle")
async def update_settings_endpoint(new_settings: SettingsUpdate, request: Request):
    logging.info("API: Uygulama ayarlarını güncelleme isteği alındı.")
    try:
        update_data = new_settings.dict(exclude_unset=True)
        if not update_data:
            return {"message": "Güncellenecek herhangi bir ayar gönderilmedi."}
        database.update_settings(update_data)
        app_config.load_config()
        scheduler = request.app.state.scheduler
        reschedule_jobs(scheduler, update_data)
        logging.info("Ayarlar başarıyla güncellendi ve ilgili arka plan görevleri yeniden zamanlandı.")
        return {"message": "Ayarlar başarıyla kaydedildi. Değişiklikler anında geçerli olacak."}
    except Exception as e:
        logging.error(f"Ayarlar güncellenirken hata oluştu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ayarlar kaydedilirken bir sunucu hatası oluştu: {str(e)}")
