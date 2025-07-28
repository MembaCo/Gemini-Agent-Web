# backend/tools/market_discovery.py
# @author: MembaCo.

import os
import logging
import requests
from core import app_config, cache_manager
from tools.utils import _get_unified_symbol

TAAPI_API_KEY = os.getenv("TAAPI_API_KEY")

def get_technical_screener_results() -> list[str]:
    """
    TAAPI.io kullanarak belirli teknik kriterlere uyan coin'leri tarar.
    """
    if not app_config.settings.get("DISCOVERY_USE_TAAPI_SCANNER", False):
        return []
    if not TAAPI_API_KEY:
        logging.warning("TAAPI.io taraması atlanıyor: TAAPI_API_KEY .env dosyasında bulunamadı.")
        return []

    cache_key = "screener_taapi_rsi_oversold_bulk"
    cached_result = cache_manager.get(cache_key)
    if cached_result:
        logging.info("Teknik tarama sonuçları önbellekten okundu.")
        return cached_result

    logging.info("TAAPI.io üzerinden toplu teknik sorgulama (bulk) yapılıyor...")
    try:
        url = "https://api.taapi.io/bulk"
        payload = {
            "secret": TAAPI_API_KEY,
            "construct": {
                "exchange": "binance",
                "symbol": "*USDT",
                "interval": "15m",
                "indicators": [
                    {
                        "indicator": "rsi",
                        "backtracks": 1
                    }
                ]
            }
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        rsi_oversold_threshold = 35
        symbols = [
            item['symbol'] for item in data.get('data', [])
            if item.get('result') and item['result'].get('value') is not None and item['result']['value'] < rsi_oversold_threshold
        ]
        
        logging.info(f"TAAPI.io taraması sonucu {len(symbols)} adet RSI'ı {rsi_oversold_threshold} altında olan sembol bulundu.")
        cache_manager.set(cache_key, symbols, ttl=900)
        return symbols

    except requests.RequestException as e:
        logging.error(f"TAAPI.io teknik tarama sırasında hata: {e}")
        return []

def get_socially_trending_coins() -> list[str]:
    """
    CoinGecko API'sini kullanarak sosyal medyada ve platformda popüler olan coin'leri çeker.
    """
    if not app_config.settings.get("DISCOVERY_USE_COINGECKO_TRENDING", False):
        return []
        
    cache_key = "trending_coingecko_search"
    cached_result = cache_manager.get(cache_key)
    if cached_result:
        logging.info("Sosyal trend verileri (CoinGecko) önbellekten okundu.")
        return cached_result

    logging.info("CoinGecko üzerinden trend verileri çekiliyor...")
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        symbols = [
            _get_unified_symbol(item['item']['symbol']) for item in data.get('coins', [])
            if 'symbol' in item.get('item', {})
        ]
        
        logging.info(f"CoinGecko'dan {len(symbols)} adet trend coini bulundu.")
        cache_manager.set(cache_key, symbols, ttl=1800)
        return symbols
        
    except requests.RequestException as e:
        logging.error(f"CoinGecko trend verisi alınırken hata: {e}")
        return []