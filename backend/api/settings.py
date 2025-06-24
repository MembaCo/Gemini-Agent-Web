# ==============================================================================
# File: backend/api/settings.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import database
from core import app_config # Ayarları anlık olarak yeniden yüklemek için

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)

class AppSettings(BaseModel):
    APP_VERSION: str; GEMINI_MODEL: str; USE_MTA_ANALYSIS: bool; MTA_TREND_TIMEFRAME: str; LIVE_TRADING: bool; DEFAULT_ORDER_TYPE: str; DEFAULT_MARKET_TYPE: str; LEVERAGE: float; RISK_PER_TRADE_PERCENT: float; ATR_MULTIPLIER_SL: float; RISK_REWARD_RATIO_TP: float; USE_TRAILING_STOP_LOSS: bool; TRAILING_STOP_ACTIVATION_PERCENT: float; USE_PARTIAL_TP: bool; PARTIAL_TP_TARGET_RR: float; PARTIAL_TP_CLOSE_PERCENT: float; MAX_CONCURRENT_TRADES: int; POSITION_CHECK_INTERVAL_SECONDS: int; TELEGRAM_ENABLED: bool; PROACTIVE_SCAN_ENABLED: bool; PROACTIVE_SCAN_INTERVAL_SECONDS: int; PROACTIVE_SCAN_AUTO_CONFIRM: bool; PROACTIVE_SCAN_IN_LOOP: bool; PROACTIVE_SCAN_USE_GAINERS_LOSERS: bool; PROACTIVE_SCAN_TOP_N: int; PROACTIVE_SCAN_MIN_VOLUME_USDT: int; PROACTIVE_SCAN_BLACKLIST: list[str]; PROACTIVE_SCAN_WHITELIST: list[str]; PROACTIVE_SCAN_MTA_ENABLED: bool; PROACTIVE_SCAN_ENTRY_TIMEFRAME: str; PROACTIVE_SCAN_TREND_TIMEFRAME: str

@router.get("/", response_model=AppSettings, summary="Tüm uygulama ayarlarını al")
async def get_settings():
    """Tüm yapılandırma ayarlarını veritabanından okur ve döndürür."""
    try:
        return database.get_all_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Sunucu ayarları okunurken bir hata oluştu.")

@router.put("/", summary="Uygulama ayarlarını güncelle")
async def update_settings(new_settings: AppSettings):
    """
    Frontend'den gelen yeni ayarları alır, veritabanına kaydeder ve
    çalışan uygulamanın ayarlarını anında günceller.
    """
    logging.info("API: Uygulama ayarlarını güncelleme isteği alındı.")
    try:
        settings_dict = new_settings.dict()
        database.update_settings(settings_dict)
        app_config.load_config()
        
        logging.info("Ayarlar başarıyla güncellendi ve anında yüklendi.")
        return {"message": "Ayarlar başarıyla kaydedildi. Değişiklikler anında geçerli olacak."}
        
    except Exception as e:
        logging.error(f"Ayarlar veritabanına yazılırken hata oluştu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ayarlar kaydedilirken bir sunucu hatası oluştu: {str(e)}")
