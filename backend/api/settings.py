# ==============================================================================
# File: backend/api/settings.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import database
from core import app_config, scanner # scanner'ı import ediyoruz

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)

class AppSettings(BaseModel):
    APP_VERSION: str; GEMINI_MODEL: str; USE_MTA_ANALYSIS: bool; MTA_TREND_TIMEFRAME: str; LIVE_TRADING: bool; DEFAULT_ORDER_TYPE: str; DEFAULT_MARKET_TYPE: str; LEVERAGE: float; RISK_PER_TRADE_PERCENT: float; ATR_MULTIPLIER_SL: float; RISK_REWARD_RATIO_TP: float; USE_TRAILING_STOP_LOSS: bool; TRAILING_STOP_ACTIVATION_PERCENT: float; USE_PARTIAL_TP: bool; PARTIAL_TP_TARGET_RR: float; PARTIAL_TP_CLOSE_PERCENT: float; MAX_CONCURRENT_TRADES: int; POSITION_CHECK_INTERVAL_SECONDS: int; TELEGRAM_ENABLED: bool; PROACTIVE_SCAN_ENABLED: bool; PROACTIVE_SCAN_INTERVAL_SECONDS: int; PROACTIVE_SCAN_AUTO_CONFIRM: bool; PROACTIVE_SCAN_IN_LOOP: bool; PROACTIVE_SCAN_USE_GAINERS_LOSERS: bool; PROACTIVE_SCAN_TOP_N: int; PROACTIVE_SCAN_MIN_VOLUME_USDT: int; PROACTIVE_SCAN_BLACKLIST: list[str]; PROACTIVE_SCAN_WHITELIST: list[str]; PROACTIVE_SCAN_MTA_ENABLED: bool; PROACTIVE_SCAN_ENTRY_TIMEFRAME: str; PROACTIVE_SCAN_TREND_TIMEFRAME: str


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


@router.get("/", response_model=AppSettings, summary="Tüm uygulama ayarlarını al")
async def get_settings():
    """Tüm yapılandırma ayarlarını veritabanından okur ve döndürür."""
    try:
        return database.get_all_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Sunucu ayarları okunurken bir hata oluştu.")

# === DEĞİŞTİRİLDİ: Request objesi eklendi ve reschedule_jobs çağrıldı ===
@router.put("/", summary="Uygulama ayarlarını güncelle")
async def update_settings(new_settings: AppSettings, request: Request):
    """
    Frontend'den gelen yeni ayarları alır, veritabanına kaydeder ve
    çalışan uygulamanın ayarlarını ve arka plan görevlerini anında günceller.
    """
    logging.info("API: Uygulama ayarlarını güncelleme isteği alındı.")
    try:
        settings_dict = new_settings.dict()
        
        # 1. Ayarları veritabanına kaydet
        database.update_settings(settings_dict)
        
        # 2. Çalışan uygulamanın config'ini anında yeniden yükle
        app_config.load_config()
        
        # 3. Arka plan görevlerini yeni ayarlarla yeniden zamanla
        scheduler = request.app.state.scheduler
        reschedule_jobs(scheduler, settings_dict)
        
        logging.info("Ayarlar başarıyla güncellendi ve arka plan görevleri yeniden zamanlandı.")
        return {"message": "Ayarlar başarıyla kaydedildi. Değişiklikler anında geçerli olacak."}
        
    except Exception as e:
        logging.error(f"Ayarlar güncellenirken hata oluştu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ayarlar kaydedilirken bir sunucu hatası oluştu: {str(e)}")