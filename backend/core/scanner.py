# ==============================================================================
# File: backend/core/scanner.py
# @author: Memba Co.
# ==============================================================================
import logging
import time
import asyncio  # YENİ: Eşzamanlı işlemler için asyncio kütüphanesi eklendi
import database
from core import app_config
from tools import get_top_gainers_losers, get_volume_spikes, _get_unified_symbol, get_technical_indicators
from core import agent as core_agent
from core.trader import open_new_trade, TradeException
from notifications import send_telegram_message
from google.api_core import exceptions as google_exceptions
from core import cache_manager

BLACKLISTED_SYMBOLS = {}


# YENİ: Tek bir sembolü asenkron olarak analiz eden yardımcı fonksiyon
async def _get_and_filter_candidate(symbol: str, entry_tf: str, source: str):
    """
    Tek bir sembol için verileri çeker, ön filtreden geçirir ve
    uygunsa aday verisini döndürür.
    """
    try:
        # Bu fonksiyon paralel çalıştığı için cache'i burada doğrudan kullanmıyoruz,
        # çünkü her interaktif taramada en taze veriyi almak istiyoruz.
        # `get_technical_indicators` içindeki kendi cache mekanizması hala geçerlidir.
        indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{symbol},{entry_tf}"})

        if indicators_result.get("status") != "success":
            return None

        indicators_data = indicators_result["data"]
        adx = indicators_data.get('adx', 0)
        rsi = indicators_data.get('rsi', 50)

        # Stratejiye göre filtreleme koşulları
        is_trending = adx > 20
        is_rsi_potential = (rsi > 65 or rsi < 35)

        if is_trending and is_rsi_potential:
            return {
                "symbol": symbol,
                "source": source, # Kaynak bilgisi artık korunuyor
                "indicators": {
                    "RSI": round(rsi, 2),
                    "ADX": round(adx, 2),
                },
                "timeframe": entry_tf
            }
        return None
    except Exception:
        # Tek bir semboldeki hata ana döngüyü kırmamalı
        return None


# === GÜNCELLENDİ: Fonksiyon artık asenkron ve tamamen optimize edilmiş ===
async def get_scan_candidates():
    """
    Tüm kaynaklardan potansiyel işlem adaylarını toplar, ön filtreden geçirir
    ve analiz için hazır bir liste olarak DÖNER. API istekleri paralelleştirilmiştir.
    """
    app_config.load_config()
    logging.info("--- 🔎 OPTİMİZE Aday Tarama Döngüsü Başlatılıyor 🔎 ---")

    # 1. Adım: Aday kaynaklarını topla (Bu bölüm senkron ve hızlıdır)
    open_symbols = {p['symbol'] for p in database.get_all_positions()}
    static_blacklist = {_get_unified_symbol(s) for s in app_config.settings.get('PROACTIVE_SCAN_BLACKLIST', [])}
    
    # Hangi sembolün hangi kaynaktan geldiğini takip etmek için bir sözlük
    potential_candidates = {}

    # Kaynak 1: Beyaz Liste
    for s in [_get_unified_symbol(s) for s in app_config.settings.get('PROACTIVE_SCAN_WHITELIST', [])]:
        potential_candidates[s] = 'Whitelist'

    # Kaynak 2: En Çok Yükselenler/Düşenler
    if app_config.settings.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
        try:
            for item in get_top_gainers_losers(top_n=app_config.settings.get('PROACTIVE_SCAN_TOP_N', 10), min_volume_usdt=app_config.settings.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)):
                if item['symbol'] not in potential_candidates:
                    potential_candidates[item['symbol']] = 'Gainer/Loser'
        except Exception as e:
            logging.error(f"Yükselen/Düşenler listesi alınamadı: {e}")

    # Kaynak 3: Hacim Patlaması
    if app_config.settings.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
        try:
            for item in get_volume_spikes(timeframe=app_config.settings.get('PROACTIVE_SCAN_VOLUME_TIMEFRAME', '1h'), period=app_config.settings.get('PROACTIVE_SCAN_VOLUME_PERIOD', 24), multiplier=app_config.settings.get('PROACTIVE_SCAN_VOLUME_MULTIPLIER', 5.0), min_volume_usdt=app_config.settings.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)):
                if item['symbol'] not in potential_candidates:
                    potential_candidates[item['symbol']] = f"Hacim Patlaması ({item['spike_ratio']:.1f}x)"
        except Exception as e:
            logging.error(f"Hacim patlaması listesi alınamadı: {e}", exc_info=True)
    
    # Filtrelenmiş son tarama listesini oluştur
    final_scan_list = {s: src for s, src in potential_candidates.items() if s not in open_symbols and s not in static_blacklist}
    logging.info(f"Toplam {len(final_scan_list)} benzersiz aday bulundu. Paralel ön filtre uygulanıyor...")

    # 2. Adım: Tüm adayları paralel olarak filtrele
    entry_tf = app_config.settings.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    
    # Her bir sembol için asenkron görevler oluştur
    tasks = [_get_and_filter_candidate(symbol, entry_tf, source) for symbol, source in final_scan_list.items()]
    
    # Tüm görevleri eşzamanlı olarak çalıştır ve sonuçları bekle
    results = await asyncio.gather(*tasks)
    
    # `None` olmayan (yani filtreden geçen) sonuçları topla
    ready_candidates = [res for res in results if res is not None]

    logging.info(f"--- ✅ OPTİMİZE Aday Tarama Tamamlandı: {len(ready_candidates)} aday analize hazır. ---")
    return ready_candidates


def execute_single_scan_cycle():
    """Bu fonksiyon artık kullanılmıyor, ancak uyumluluk için bırakıldı."""
    logging.warning("execute_single_scan_cycle fonksiyonu artık kullanımdan kaldırılmıştır. Lütfen yeni interaktif tarayıcıyı kullanın.")
    return {"summary": {}, "details": [{"type":"warning", "symbol":"SYSTEM", "message": "Bu tarama yöntemi kullanımdan kaldırıldı."}]}