# backend/core/scanner.py
# @author: Memba Co.

import pandas as pd
import logging
import asyncio
from datetime import datetime

from core import app_config, agent
from core.trader import open_new_trade, TradeException
from tools.exchange import get_top_gainers_losers, get_volume_spikes, get_technical_indicators
from tools.utils import _get_unified_symbol
from tools import _fetch_price_natively

# --- İndikatör Hesaplama Fonksiyonları ---

def calculate_ma_signal(close_prices: pd.Series, short_window: int, long_window: int) -> str:
    """
    Verilen kısa ve uzun vadeli periyotlara göre Hareketli Ortalama Kesişim sinyali üretir.
    """
    if len(close_prices) < long_window:
        return 'NEUTRAL'
        
    ma_short = close_prices.rolling(window=short_window).mean()
    ma_long = close_prices.rolling(window=long_window).mean()
    
    if ma_short.iloc[-1] > ma_long.iloc[-1] and ma_short.iloc[-2] <= ma_long.iloc[-2]:
        return 'BUY'
    elif ma_short.iloc[-1] < ma_long.iloc[-1] and ma_short.iloc[-2] >= ma_long.iloc[-2]:
        return 'SELL'
    else:
        return 'NEUTRAL'

def calculate_rsi_signal(close_prices: pd.Series, period: int, overbought_threshold: int, oversold_threshold: int) -> str:
    """
    Standart RSI (Wilder's Smoothing kullanarak) hesaplar ve sinyal üretir.
    """
    if len(close_prices) < period + 1:
        return 'NEUTRAL'

    delta = close_prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    # Bölme hatasını önlemek için kontrol
    if avg_loss.iloc[-1] == 0:
        return 'NEUTRAL'

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    last_rsi = rsi.iloc[-1]
    
    if last_rsi > overbought_threshold:
        return 'SELL'
    elif last_rsi < oversold_threshold:
        return 'BUY'
    else:
        return 'NEUTRAL'


async def _fetch_candidates_from_sources(config: dict) -> list[dict]:
    """
    Whitelist, gainers/losers ve volume spike kaynaklarından potansiyel işlem
    adaylarını toplar ve blacklist ile filtreler.
    """
    all_symbols_with_source = {}  # Yinelenenleri önlemek için dict kullanılıyor

    # 1. Whitelist en yüksek önceliğe sahip
    whitelist = config.get('PROACTIVE_SCAN_WHITELIST', [])
    for symbol in whitelist:
        unified_symbol = _get_unified_symbol(symbol)
        all_symbols_with_source[unified_symbol] = {"symbol": unified_symbol, "source": "Whitelist"}

    # 2. Gainers/Losers
    if config.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
        top_n = config.get('PROACTIVE_SCAN_TOP_N', 10)
        min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
        gainers_losers = get_top_gainers_losers(top_n, min_volume_usdt)
        for item in gainers_losers:
            if item['symbol'] not in all_symbols_with_source:
                all_symbols_with_source[item['symbol']] = {"symbol": item['symbol'], "source": "Gainers/Losers"}

    # 3. Volume Spike
    if config.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
        volume_timeframe = config.get('PROACTIVE_SCAN_VOLUME_TIMEFRAME', '1h')
        volume_period = config.get('PROACTIVE_SCAN_VOLUME_PERIOD', 24)
        volume_multiplier = config.get('PROACTIVE_SCAN_VOLUME_MULTIPLIER', 5.0)
        min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
        volume_spikes = get_volume_spikes(volume_timeframe, volume_period, volume_multiplier, min_volume_usdt)
        for item in volume_spikes:
            if item['symbol'] not in all_symbols_with_source:
                all_symbols_with_source[item['symbol']] = {"symbol": item['symbol'], "source": "Volume Spike"}

    # 4. Blacklist ile filtreleme
    blacklist = config.get('PROACTIVE_SCAN_BLACKLIST', [])
    blacklist_upper = {s.upper() for s in blacklist}
    
    final_candidates = [
        data for symbol, data in all_symbols_with_source.items()
        if symbol.split('/')[0] not in blacklist_upper
    ]
            
    return final_candidates

async def get_interactive_scan_candidates() -> list[dict]:
    """
    Yapılandırılmış kaynaklardan potansiyel adayların bir listesini alır ve
    interaktif tarayıcı sayfasında görüntülenmek üzere temel teknik göstergelerle zenginleştirir.
    Bu fonksiyon AI analizi YAPMAZ.
    """
    logging.info("İNTERAKTİF TARAYICI: Aday listesi oluşturuluyor...")
    config = app_config.settings
    candidates_without_indicators = await _fetch_candidates_from_sources(config)
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    
    async def fetch_indicators(cand):
        indicators_result = get_technical_indicators(f"{cand['symbol']},{entry_timeframe}")
        if indicators_result.get("status") == "success":
            cand['indicators'] = indicators_result['data']
            cand['timeframe'] = entry_timeframe
            cand['last_updated'] = datetime.now().isoformat()
            return cand
        else:
            logging.warning(f"İnteraktif tarama için {cand['symbol']} göstergeleri alınamadı: {indicators_result.get('message')}")
            return None

    tasks = [fetch_indicators(c) for c in candidates_without_indicators]
    results = await asyncio.gather(*tasks)
    
    final_candidates = [res for res in results if res is not None]
    logging.info(f"İNTERAKTİF TARAYICI: {len(final_candidates)} adet aday, göstergeleriyle birlikte bulundu.")
    return final_candidates

async def execute_single_scan_cycle():
    """
    Tam bir proaktif tarama döngüsü yürütür. Adayları bulur, üzerlerinde AI analizi çalıştırır
    ve ayarlara göre ya otomatik olarak işlem açar ya da fırsatları kaydeder.
    """
    logging.info("PROAKTİF TARAYICI: Tam tarama döngüsü başlatılıyor...")
    config = app_config.settings
    initial_candidates = await _fetch_candidates_from_sources(config)

    total_scanned_count = len(initial_candidates)
    opportunities_found = []
    auto_trades_opened = []
    data_errors = 0
    
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    trend_timeframe = config.get('PROACTIVE_SCAN_TREND_TIMEFRAME', '4h')
    use_mta = config.get('PROACTIVE_SCAN_MTA_ENABLED', True)

    async def analyze_symbol(candidate):
        symbol = candidate['symbol']
        try:
            current_price_val = _fetch_price_natively(symbol)
            if not current_price_val:
                logging.warning(f"Proaktif tarama: {symbol} için fiyat alınamadı.")
                return {"type": "error", "symbol": symbol, "message": "Fiyat bilgisi alınamadı."}

            entry_indicators_result = get_technical_indicators(f"{symbol},{entry_timeframe}")
            if entry_indicators_result.get("status") != "success":
                return {"type": "error", "symbol": symbol, "message": f"Teknik veri hatası: {entry_indicators_result.get('message')}"}

            final_prompt = ""
            if use_mta:
                trend_indicators_result = get_technical_indicators(f"{symbol},{trend_timeframe}")
                if trend_indicators_result.get("status") != "success":
                    return {"type": "error", "symbol": symbol, "message": f"Trend verisi hatası: {trend_indicators_result.get('message')}"}
                final_prompt = agent.create_mta_analysis_prompt(symbol, current_price_val, entry_timeframe, entry_indicators_result["data"], trend_timeframe, trend_indicators_result["data"])
            else:
                final_prompt = agent.create_final_analysis_prompt(symbol, entry_timeframe, current_price_val, entry_indicators_result["data"])
            
            llm_result = agent.llm.invoke(final_prompt)
            parsed_data = agent.parse_agent_response(llm_result.content)

            if not parsed_data:
                return {"type": "error", "symbol": symbol, "message": "Yapay zekadan geçersiz yanıt."}

            if parsed_data.get('recommendation') in ['AL', 'SAT']:
                if config.get('PROACTIVE_SCAN_AUTO_CONFIRM'):
                    try:
                        open_new_trade(symbol=symbol, recommendation=parsed_data['recommendation'], timeframe=entry_timeframe, current_price=current_price_val)
                        auto_trades_opened.append(symbol)
                        return {"type": "success", "symbol": symbol, "message": f"Otomatik pozisyon açıldı: {parsed_data['recommendation']}"}
                    except TradeException as te:
                        return {"type": "critical", "symbol": symbol, "message": f"Otomatik işlem hatası: {te}"}
                else:
                    opportunities_found.append(parsed_data)
                    return {"type": "opportunity", "symbol": symbol, "message": f"Fırsat bulundu: {parsed_data['recommendation']} - {parsed_data.get('reason', '')}", "data": parsed_data}
            
            return {"type": "info", "symbol": symbol, "message": f"Analiz sonucu: BEKLE. Gerekçe: {parsed_data.get('reason', '')}"}
            
        except Exception as e:
            logging.error(f"Proaktif tarama sırasında {symbol} analiz edilirken hata: {e}", exc_info=True)
            return {"type": "critical", "symbol": symbol, "message": f"Analiz sırasında kritik hata: {str(e)}"}

    analysis_results = await asyncio.gather(*[analyze_symbol(c) for c in initial_candidates])
    
    for res in analysis_results:
        if res and res['type'] in ['error', 'critical']: data_errors += 1

    logging.info(f"PROAKTİF TARAYICI DÖNGÜSÜ TAMAMLANDI. Taranan: {total_scanned_count}, Otomatik açılan: {len(auto_trades_opened)}, Onay bekleyen: {len(opportunities_found)}, Hata: {data_errors}")

    return {
        "summary": {"total_scanned": total_scanned_count, "opportunities_found": len(opportunities_found), "auto_trades_opened": len(auto_trades_opened), "data_errors": data_errors},
        "details": analysis_results
    }