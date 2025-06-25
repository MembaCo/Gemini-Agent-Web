# ==============================================================================
# File: backend/core/scanner.py
# @author: Memba Co.
#
# --- NİHAİ SÜRÜM 3.0: GÜVENİLİR VERİ KAYNAĞI VE GELİŞMİŞ TEŞHİS ---
# Bu sürüm, API'den veri çekme adımını try-except bloğu içine alarak ve
# sonuçları detaylı loglayarak olası bağlantı veya yetki sorunlarının
# kaynağını net bir şekilde ortaya çıkarmayı hedefler.
# ==============================================================================
import logging
import asyncio
import os
import ccxt.async_support as ccxt_async
import pandas as pd
import pandas_ta as ta

import database
from core import app_config
from tools import _get_unified_symbol
from tools.utils import str_to_bool

# === ASENKRON YARDIMCI FONKSİYONLAR (Değişiklik yok) ===
def _create_async_exchange():
    use_testnet = str_to_bool(os.getenv("USE_TESTNET", "False"))
    api_key = os.getenv("BINANCE_API_KEY")
    secret_key = os.getenv("BINANCE_SECRET_KEY")
    config_data = { "apiKey": api_key, "secret": secret_key, "options": {"defaultType": app_config.settings.get('DEFAULT_MARKET_TYPE', 'future').lower()}, "enableRateLimit": True, 'timeout': 20000, }
    exchange = ccxt_async.binance(config_data)
    if use_testnet and app_config.settings.get('DEFAULT_MARKET_TYPE') == 'future': exchange.set_sandbox_mode(True)
    return exchange

async def _check_volume_spike_async(symbol: str, exchange, settings: dict):
    try:
        timeframe, period, multiplier = settings['PROACTIVE_SCAN_VOLUME_TIMEFRAME'], settings['PROACTIVE_SCAN_VOLUME_PERIOD'], settings['PROACTIVE_SCAN_VOLUME_MULTIPLIER']
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=period + 1)
        if len(bars) < period + 1: return None
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        if len(df) < period + 1: return None
        last_volume = df['volume'].iloc[-1]; average_volume = df['volume'].iloc[-period-1:-1].mean()
        if pd.isna(last_volume) or pd.isna(average_volume) or average_volume == 0: return None
        if last_volume > average_volume * multiplier:
            return {"symbol": _get_unified_symbol(symbol), "source": f"Hacim Patlaması ({last_volume / average_volume:.1f}x)"}
        return None
    except Exception: return None

async def _fetch_and_filter_candidate_async(symbol: str, timeframe: str, source: str, exchange):
    try:
        bars = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
        if not bars or len(bars) < 100: return None
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        for col in ['open', 'high', 'low', 'close', 'volume']: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True);
        if len(df) < 100: return None
        df.ta.rsi(length=14, append=True); df.ta.adx(length=14, append=True)
        df.dropna(inplace=True);
        if df.empty: return None
        last = df.iloc[-1]; rsi, adx = last.get('RSI_14'), last.get('ADX_14')
        if rsi is None or adx is None or pd.isna(rsi) or pd.isna(adx): return None
        if adx > 20 and (rsi < 35 or rsi > 65):
            return {"symbol": symbol, "source": source, "indicators": {"RSI": round(rsi, 2), "ADX": round(adx, 2)}, "timeframe": timeframe}
        return None
    except Exception: return None

# === ANA TARAYICI MANTIĞI (GELİŞMİŞ TEŞHİS İLE) ===
async def get_scan_candidates() -> dict:
    app_config.load_config()
    settings = app_config.settings
    logging.info("--- 🧠 Kapsamlı ve Paralel Aday Tarama Döngüsü Başlatılıyor (v3.0 Teşhis Modu) 🧠 ---")

    potential_symbols = {}
    for symbol in settings.get('PROACTIVE_SCAN_WHITELIST', []):
        potential_symbols[_get_unified_symbol(symbol)] = 'Whitelist'
    logging.info(f"Strateji 1 (Whitelist): {len(potential_symbols)} aday eklendi.")

    exchange = _create_async_exchange()
    try:
        # === YENİ: GELİŞMİŞ HATA YAKALAMA VE TEŞHİS ===
        all_tickers_list = []
        try:
            logging.info(">>> [TEŞHİS] Binance Vadeli İşlemler API'sinden (fapiPublicGetTicker24hr) veri çekiliyor...")
            all_tickers_list = await exchange.fapiPublicGetTicker24hr()
            logging.info(f">>> [TEŞHİS] API çağrısı başarılı. {len(all_tickers_list)} adet ticker verisi alındı.")
            
            if not all_tickers_list:
                logging.critical(">>> [TEŞHİS] KRİTİK HATA: Binance'ten ticker verisi çekilemedi veya boş bir liste döndü! Lütfen `.env` dosyasındaki API anahtarlarınızın VADELİ İŞLEMLER (FUTURES) için 'Okumayı Etkinleştir' iznine sahip olduğundan emin olun.")
                return {"total_scanned": 0, "found_candidates": []}
            
            logging.info(f"Gelen ilk veri örneği: {all_tickers_list[0]}")

        except Exception as e:
            logging.critical(f">>> [TEŞHİS] KRİTİK HATA: `fapiPublicGetTicker24hr` çağrılırken bir istisna oluştu: {e}", exc_info=True)
            logging.critical("Bu hata genellikle API anahtarlarının Vadeli İşlemler (Futures) için yetkili olmamasından veya IP kısıtlamalarından kaynaklanır.")
            await exchange.close()
            return {"total_scanned": 0, "found_candidates": []}

        min_volume = settings.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
        volume_filtered_tickers = [t for t in all_tickers_list if float(t.get('quoteVolume', 0)) > min_volume]
        
        if not volume_filtered_tickers and all_tickers_list:
            logging.warning(f"Minimum ${min_volume:,.0f} hacim filtresini geçen coin bulunamadı!")
            all_tickers_list.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            volume_filtered_tickers = all_tickers_list[:20]
            logging.info(f"YEDEK MEKANİZMA AKTİF: En yüksek hacimli {len(volume_filtered_tickers)} coin işleme alınıyor.")
        
        # ... (Geri kalan kod öncekiyle aynı, değişiklik yok)
        if settings.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
            top_n = settings.get('PROACTIVE_SCAN_TOP_N', 10)
            sorted_by_change = sorted(volume_filtered_tickers, key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
            added_count = 0
            for ticker in sorted_by_change[:top_n] + sorted_by_change[-top_n:]:
                unified_symbol = _get_unified_symbol(ticker['symbol'])
                if unified_symbol not in potential_symbols:
                    potential_symbols[unified_symbol] = 'Gainer/Loser'
                    added_count += 1
            logging.info(f"Strateji 2 (Gainer/Loser): {added_count} yeni aday eklendi.")
        
        if settings.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
            logging.info(f"Strateji 3 (Volume Spike): {len(volume_filtered_tickers)} sembol üzerinde hacim patlaması kontrolü başlatıldı...")
            spike_tasks = [_check_volume_spike_async(t['symbol'], exchange, settings) for t in volume_filtered_tickers]
            spike_results = await asyncio.gather(*spike_tasks)
            added_count = 0
            for result in spike_results:
                if result and result['symbol'] not in potential_symbols:
                    potential_symbols[result['symbol']] = result['source']
                    added_count += 1
            logging.info(f"Strateji 3 (Volume Spike): {added_count} yeni aday eklendi.")

        open_positions = {p['symbol'] for p in database.get_all_positions()}
        blacklist = {_get_unified_symbol(s) for s in settings.get('PROACTIVE_SCAN_BLACKLIST', [])}
        final_symbols_to_scan = {s: src for s, src in potential_symbols.items() if s not in open_positions and s not in blacklist}
        
        total_symbols_to_scan_count = len(final_symbols_to_scan)
        logging.info(f"Filtreleme Sonrası: Toplam {total_symbols_to_scan_count} benzersiz aday üzerinde son analiz yapılacak.")

        if total_symbols_to_scan_count > 0:
            timeframe = settings.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
            filter_tasks = [_fetch_and_filter_candidate_async(symbol, timeframe, source, exchange) for symbol, source in final_symbols_to_scan.items()]
            results = await asyncio.gather(*filter_tasks)
            ready_candidates = [res for res in results if res is not None]
        else:
            ready_candidates = []

    except Exception as e:
        logging.error(f"Kapsamlı tarama sırasında genel hata: {e}", exc_info=True)
        ready_candidates, total_symbols_to_scan_count = [], 0
    finally:
        await exchange.close()

    logging.info(f"--- ✅ Kapsamlı Tarama Tamamlandı: {len(ready_candidates)} aday analize hazır. ---")
    return { "total_scanned": total_symbols_to_scan_count, "found_candidates": ready_candidates }