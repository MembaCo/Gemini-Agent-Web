# ==============================================================================
# File: backend/api/settings.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import database
from core import app_config, scanner

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)

# === DEĞİŞTİRİLDİ: Pydantic modelinden APP_VERSION kaldırıldı ===
class AppSettings(BaseModel):
    GEMINI_MODEL: str
    LIVE_TRADING: bool
    DEFAULT_MARKET_TYPE: str
    DEFAULT_ORDER_TYPE: str
    USE_MTA_ANALYSIS: bool
    MTA_TREND_TIMEFRAME: str
    LEVERAGE: float
    RISK_PER_TRADE_PERCENT: float
    MAX_CONCURRENT_TRADES: int
    USE_ATR_FOR_SLTP: bool
    ATR_MULTIPLIER_SL: float
    RISK_REWARD_RATIO_TP: float
    USE_TRAILING_STOP_LOSS: bool
    TRAILING_STOP_ACTIVATION_PERCENT: float
    USE_PARTIAL_TP: bool
    PARTIAL_TP_TARGET_RR: float
    PARTIAL_TP_CLOSE_PERCENT: float
    POSITION_CHECK_INTERVAL_SECONDS: int
    PROACTIVE_SCAN_ENABLED: bool
    PROACTIVE_SCAN_INTERVAL_SECONDS: int
    PROACTIVE_SCAN_AUTO_CONFIRM: bool
    PROACTIVE_SCAN_IN_LOOP: bool
    PROACTIVE_SCAN_USE_GAINERS_LOSERS: bool
    PROACTIVE_SCAN_TOP_N: int
    PROACTIVE_SCAN_MIN_VOLUME_USDT: int
    PROACTIVE_SCAN_MTA_ENABLED: bool
    PROACTIVE_SCAN_ENTRY_TIMEFRAME: str
    PROACTIVE_SCAN_TREND_TIMEFRAME: str
    PROACTIVE_SCAN_BLACKLIST: list[str]
    PROACTIVE_SCAN_WHITELIST: list[str]
    TELEGRAM_ENABLED: bool
    PROACTIVE_SCAN_USE_VOLUME_SPIKE: bool
    PROACTIVE_SCAN_VOLUME_TIMEFRAME: str
    PROACTIVE_SCAN_VOLUME_MULTIPLIER: float
    PROACTIVE_SCAN_VOLUME_PERIOD: int

# === YENİ KOD BAŞLANGICI: Yardımcı Fonksiyon ===
def reschedule_jobs(scheduler, new_settings: dict):
    """Çalışan scheduler görevlerini yeni ayarlara göre günceller."""
    try:
        # 1. Pozisyon kontrolcüsünün interval'ını güncelle
        scheduler.reschedule_job(
            "position_checker_job",
            trigger="interval",
            seconds=new_settings['POSITION_CHECK_INTERVAL_SECONDS']
        )
        logging.info(f"Pozisyon kontrol görevi yeni interval ile yeniden zamanlandı: {new_settings['POSITION_CHECK_INTERVAL_SECONDS']} saniye.")

        # 2. Proaktif tarayıcı görevini yönet
        scanner_job = scheduler.get_job("scanner_job")
        if new_settings['PROACTIVE_SCAN_ENABLED']:
            if scanner_job:
                # Görev zaten var, interval'ını güncelle
                scheduler.reschedule_job(
                    "scanner_job",
                    trigger="interval",
                    seconds=new_settings['PROACTIVE_SCAN_INTERVAL_SECONDS']
                )
                logging.info(f"Tarayıcı görevi yeni interval ile yeniden zamanlandı: {new_settings['PROACTIVE_SCAN_INTERVAL_SECONDS']} saniye.")
            else:
                # Görev yok, yeni ayarlarla ekle
                scheduler.add_job(
                    scanner.execute_single_scan_cycle,
                    "interval",
                    seconds=new_settings['PROACTIVE_SCAN_INTERVAL_SECONDS'],
                    id="scanner_job",
                    max_instances=1
                )
                logging.info("Tarayıcı görevi etkinleştirildi ve zamanlandı.")
        else:
            if scanner_job:
                # Görev var ama artık etkin değil, kaldır
                scheduler.remove_job("scanner_job")
                logging.info("Tarayıcı görevi devre dışı bırakıldı ve kaldırıldı.")

    except Exception as e:
        logging.error(f"Scheduler görevleri yeniden zamanlanırken hata oluştu: {e}", exc_info=True)
# === YENİ KOD SONU ===


@router.get("/", summary="Tüm uygulama ayarlarını al")
async def get_settings():
    """Tüm yapılandırma ayarlarını veritabanından okur ve döndürür."""
    try:
        # APP_VERSION'ı manuel olarak yanıta ekliyoruz.
        settings = database.get_all_settings()
        settings['APP_VERSION'] = "3.9.0-ui-revamp"
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail="Sunucu ayarları okunurken bir hata oluştu.")

@router.put("/", summary="Uygulama ayarlarını güncelle")
async def update_settings(new_settings: AppSettings, request: Request):
    """
    Frontend'den gelen yeni ayarları alır, veritabanına kaydeder ve
    çalışan uygulamanın ayarlarını ve arka plan görevlerini anında günceller.
    """
    logging.info("API: Uygulama ayarlarını güncelleme isteği alındı.")
    try:
        settings_dict = new_settings.dict()
        database.update_settings(settings_dict)
        app_config.load_config()
        scheduler = request.app.state.scheduler
        reschedule_jobs(scheduler, settings_dict)
        logging.info("Ayarlar başarıyla güncellendi ve arka plan görevleri yeniden zamanlandı.")
        return {"message": "Ayarlar başarıyla kaydedildi. Değişiklikler anında geçerli olacak."}
    except Exception as e:
        logging.error(f"Ayarlar güncellenirken hata oluştu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ayarlar kaydedilirken bir sunucu hatası oluştu: {str(e)}")