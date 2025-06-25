# ==============================================================================
# File: backend/api/settings.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List # YENİ: Optional ve List import edildi

import database
from core import app_config, scanner

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)

# === YENİ: Kısmi güncellemelere izin veren esnek Pydantic modeli ===
# Artık her alan isteğe bağlı (Optional), bu da frontend'in sadece
# değiştirmek istediği alanları göndermesine olanak tanır.
class SettingsUpdate(BaseModel):
    GEMINI_MODEL: Optional[str] = None
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

# === YENİ KOD BAŞLANGICI: Yardımcı Fonksiyon (Değişiklik yok, sadece burada duruyor) ===
def reschedule_jobs(scheduler, new_settings: dict):
    """Çalışan scheduler görevlerini yeni ayarlara göre günceller."""
    try:
        # Arka plan görevlerini yeniden zamanlarken, ayarın gönderilip gönderilmediğini kontrol et
        if 'POSITION_CHECK_INTERVAL_SECONDS' in new_settings:
            scheduler.reschedule_job(
                "position_checker_job",
                trigger="interval",
                seconds=new_settings['POSITION_CHECK_INTERVAL_SECONDS']
            )
            logging.info(f"Pozisyon kontrol görevi yeni interval ile yeniden zamanlandı: {new_settings['POSITION_CHECK_INTERVAL_SECONDS']} saniye.")

        if 'PROACTIVE_SCAN_ENABLED' in new_settings or 'PROACTIVE_SCAN_INTERVAL_SECONDS' in new_settings:
            scanner_job = scheduler.get_job("scanner_job")
            # En son ayarları doğrudan app_config'den oku, çünkü sadece bir ayar değişmiş olabilir
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
# === YENİ KOD SONU ===


@router.get("/", summary="Tüm uygulama ayarlarını al")
async def get_settings():
    """Tüm yapılandırma ayarlarını veritabanından okur ve döndürür."""
    try:
        settings = database.get_all_settings()
        
        # === DEĞİŞTİRİLECEK SATIR BURASI ===
        # Hatalı olan bu satırı:
        # settings['APP_VERSION'] = app_config.APP_VERSION
        
        # Aşağıdaki doğru satır ile değiştirin:
        settings['APP_VERSION'] = "3.9.0-ui-revamp" # Arayüzde kullanılan güncel versiyon
        
        return settings
    except Exception as e:
        # Bu satırda hata `e` yerine `str(e)` olarak değiştirilebilir, ancak mevcut hali de çalışır.
        logging.error(f"Ayarlar okunurken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sunucu ayarları okunurken bir hata oluştu.")


@router.put("/", summary="Uygulama ayarlarını güncelle")
# === DEĞİŞTİRİLDİ: Artık esnek SettingsUpdate modelini kullanıyoruz ===
async def update_settings(new_settings: SettingsUpdate, request: Request):
    """
    Frontend'den gelen yeni ayarları alır, veritabanına kaydeder ve
    çalışan uygulamanın ayarlarını ve arka plan görevlerini anında günceller.
    """
    logging.info("API: Uygulama ayarlarını güncelleme isteği alındı.")
    try:
        # .dict(exclude_unset=True) metodu, sadece frontend'den gönderilen
        # (yani değeri None olmayan) alanları içeren bir sözlük oluşturur.
        # Bu, kısmi güncellemenin anahtarıdır.
        update_data = new_settings.dict(exclude_unset=True)

        if not update_data:
            return {"message": "Güncellenecek herhangi bir ayar gönderilmedi."}

        database.update_settings(update_data)
        app_config.load_config() # Yeni ayarları global state'e yükle
        
        # Scheduler'ı sadece etkilenen ayarlar değiştiyse yeniden zamanla
        scheduler = request.app.state.scheduler
        reschedule_jobs(scheduler, update_data)
        
        logging.info("Ayarlar başarıyla güncellendi ve ilgili arka plan görevleri yeniden zamanlandı.")
        return {"message": "Ayarlar başarıyla kaydedildi. Değişiklikler anında geçerli olacak."}
    except Exception as e:
        logging.error(f"Ayarlar güncellenirken hata oluştu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ayarlar kaydedilirken bir sunucu hatası oluştu: {str(e)}")