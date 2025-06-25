# ==============================================================================
# File: backend/core/scanner.py
# @author: Memba Co.
# ==============================================================================
import logging
import time
import database
from core import app_config
from tools import get_top_gainers_losers, get_volume_spikes, _get_unified_symbol, _fetch_price_natively, get_technical_indicators
from core import agent as core_agent
from core.trader import open_new_trade, TradeException
from notifications import send_telegram_message
from google.api_core import exceptions as google_exceptions
from core import cache_manager

BLACKLISTED_SYMBOLS = {}

# === YENİ FONKSİYON: Sadece adayları bulur, AI analizi yapmaz. ===
def get_scan_candidates():
    """
    Tüm kaynaklardan potansiyel işlem adaylarını toplar, ön filtreden geçirir
    ve analiz için hazır bir liste olarak döndürür.
    """
    app_config.load_config()
    logging.info("--- 🔎 Aday Tarama Döngüsü Başlatılıyor 🔎 ---")
    
    # Mevcut pozisyonları ve kara listeleri al
    open_symbols = {p['symbol'] for p in database.get_all_positions()}
    now = time.time()
    for symbol, expiry in list(BLACKLISTED_SYMBOLS.items()):
        if now > expiry:
            del BLACKLISTED_SYMBOLS[symbol]
            logging.info(f"{symbol} dinamik kara listeden çıkarıldı.")
    static_blacklist = {_get_unified_symbol(s) for s in app_config.settings.get('PROACTIVE_SCAN_BLACKLIST', [])}

    # Tarama kaynaklarından sembolleri topla
    symbols_to_scan = []
    seen_sources = {} # Hangi sembolün hangi kaynaktan geldiğini tutmak için

    # 1. Beyaz Liste
    whitelist_symbols = [_get_unified_symbol(s) for s in app_config.settings.get('PROACTIVE_SCAN_WHITELIST', [])]
    for s in whitelist_symbols: seen_sources[s] = 'Whitelist'
    symbols_to_scan.extend(whitelist_symbols)
    
    # 2. En Çok Yükselenler/Düşenler
    if app_config.settings.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
        try:
            gainer_loser_list = get_top_gainers_losers(top_n=app_config.settings.get('PROACTIVE_SCAN_TOP_N', 10), min_volume_usdt=app_config.settings.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000))
            for item in gainer_loser_list:
                if item['symbol'] not in seen_sources: seen_sources[item['symbol']] = 'Gainer/Loser'
            symbols_to_scan.extend([item['symbol'] for item in gainer_loser_list])
        except Exception as e:
            logging.error(f"Yükselen/Düşenler listesi alınamadı: {e}")

    # 3. Hacim Patlaması
    if app_config.settings.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
        try:
            volume_spike_list = get_volume_spikes(timeframe=app_config.settings.get('PROACTIVE_SCAN_VOLUME_TIMEFRAME', '1h'), period=app_config.settings.get('PROACTIVE_SCAN_VOLUME_PERIOD', 24), multiplier=app_config.settings.get('PROACTIVE_SCAN_VOLUME_MULTIPLIER', 5.0), min_volume_usdt=app_config.settings.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000))
            for item in volume_spike_list:
                 if item['symbol'] not in seen_sources: seen_sources[item['symbol']] = f"Hacim Patlaması ({item['spike_ratio']:.1f}x)"
            symbols_to_scan.extend([item['symbol'] for item in volume_spike_list])
        except Exception as e:
            logging.error(f"Hacim patlaması listesi alınamadı: {e}", exc_info=True)

    # Yinelenenleri ve kara listedekileri temizle
    final_scan_list = []
    seen = set()
    for symbol in symbols_to_scan:
        if (symbol not in seen and symbol not in open_symbols and symbol not in static_blacklist and symbol not in BLACKLISTED_SYMBOLS):
            final_scan_list.append(symbol)
            seen.add(symbol)
            
    logging.info(f"Toplam {len(final_scan_list)} benzersiz aday bulundu. Ön filtre uygulanıyor...")

    # Ön filtreden geçen adayları topla
    ready_candidates = []
    for symbol in final_scan_list:
        try:
            entry_tf = app_config.settings.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
            indicator_key = f"indicators_{symbol}_{entry_tf}"
            indicators_result = cache_manager.get(indicator_key)
            if not indicators_result:
                indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{symbol},{entry_tf}"})
                if indicators_result.get("status") == "success":
                    cache_manager.set(indicator_key, indicators_result)
            
            if indicators_result.get("status") != "success":
                continue

            indicators_data = indicators_result["data"]
            adx = indicators_data.get('adx', 0)
            rsi = indicators_data.get('rsi', 50)
            
            is_trending = adx > 20
            is_rsi_potential = (rsi > 65 or rsi < 35)

            if is_trending and is_rsi_potential:
                ready_candidates.append({
                    "symbol": symbol,
                    "source": seen_sources.get(symbol, 'Bilinmiyor'),
                    "indicators": {
                        "RSI": round(rsi, 2),
                        "ADX": round(adx, 2),
                    },
                    "timeframe": entry_tf
                })
        except Exception:
            # Tek bir semboldeki hata döngüyü kırmasın
            continue

    logging.info(f"--- ✅ Aday Tarama Tamamlandı: {len(ready_candidates)} aday analize hazır. ---")
    return ready_candidates

# Mevcut execute_single_scan_cycle fonksiyonu artık kullanılmayacak,
# ancak eski bir entegrasyonu bozmamak için yerinde bırakılabilir veya silinebilir.
def execute_single_scan_cycle():
    logging.warning("execute_single_scan_cycle fonksiyonu artık kullanımdan kaldırılmıştır. Lütfen yeni interaktif tarayıcıyı kullanın.")
    return {"summary": {}, "details": [{"type":"warning", "symbol":"SYSTEM", "message": "Bu tarama yöntemi kullanımdan kaldırıldı."}]}
