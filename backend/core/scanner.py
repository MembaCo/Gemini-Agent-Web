# backend/core/scanner.py
# @author: Memba Co.

import pandas as pd
import logging
import asyncio
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted

import database 
from core import app_config, agent
from core.trader import open_new_trade, TradeException
from tools.exchange import get_top_gainers_losers, get_volume_spikes, get_technical_indicators
from tools.utils import _get_unified_symbol
from tools import _fetch_price_natively

# --- YENİ KOD ---
# Binance API'sine yapılacak eşzamanlı istek sayısını sınırlamak için bir semafor oluştur.
# Bu, "Connection pool is full" hatasını önler.
CONCURRENCY_LIMIT = 10
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
# --- YENİ KOD SONU ---


async def _fetch_candidates_from_sources(config: dict) -> list[dict]:
    """
    Whitelist, gainers/losers ve volume spike kaynaklarından potansiyel işlem
    adaylarını toplar ve blacklist ile filtreler.
    """
    all_symbols_with_source = {}
    whitelist = config.get('PROACTIVE_SCAN_WHITELIST', [])
    for symbol in whitelist:
        unified_symbol = _get_unified_symbol(symbol)
        all_symbols_with_source[unified_symbol] = {"symbol": unified_symbol, "source": "Whitelist"}

    async def fetch_gainers_losers():
        if config.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
            top_n = config.get('PROACTIVE_SCAN_TOP_N', 10)
            min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
            # Semafor ile eşzamanlı çağrıyı sınırla
            async with semaphore:
                return await asyncio.to_thread(get_top_gainers_losers, top_n, min_volume_usdt)
        return []

    async def fetch_volume_spikes():
        if config.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
            volume_timeframe = config.get('PROACTIVE_SCAN_VOLUME_TIMEFRAME', '1h')
            volume_period = config.get('PROACTIVE_SCAN_VOLUME_PERIOD', 24)
            volume_multiplier = config.get('PROACTIVE_SCAN_VOLUME_MULTIPLIER', 5.0)
            min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
            # Semafor ile eşzamanlı çağrıyı sınırla
            async with semaphore:
                return await asyncio.to_thread(get_volume_spikes, volume_timeframe, volume_period, volume_multiplier, min_volume_usdt)
        return []

    # Kaynakları paralel olarak, ancak kontrollü bir şekilde çek
    gainers_losers_results, volume_spikes_results = await asyncio.gather(
        fetch_gainers_losers(),
        fetch_volume_spikes()
    )

    for item in gainers_losers_results:
        if item['symbol'] not in all_symbols_with_source:
            all_symbols_with_source[item['symbol']] = {"symbol": item['symbol'], "source": "Gainers/Losers"}
    for item in volume_spikes_results:
        if item['symbol'] not in all_symbols_with_source:
            all_symbols_with_source[item['symbol']] = {"symbol": item['symbol'], "source": "Volume Spike"}

    blacklist = config.get('PROACTIVE_SCAN_BLACKLIST', [])
    blacklist_upper = {s.upper() for s in blacklist}
    final_candidates = [ data for symbol, data in all_symbols_with_source.items() if symbol.split('/')[0] not in blacklist_upper ]
    return final_candidates


async def get_interactive_scan_candidates() -> list[dict]:
    """İnteraktif tarayıcı için göstergeleriyle birlikte adayları çeker."""
    logging.info("İNTERAKTİF TARAYICI: Aday listesi oluşturuluyor...")
    config = app_config.settings
    candidates_without_indicators = await _fetch_candidates_from_sources(config)
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    
    async def fetch_indicators(cand):
        # Her bir gösterge çekme işlemini semafor ile sınırla
        async with semaphore:
            indicators_result = await asyncio.to_thread(get_technical_indicators, f"{cand['symbol']},{entry_timeframe}")
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
    Tam bir proaktif tarama döngüsü yürütür. Adayları bulur, ön filtreden geçirir,
    kalanlar üzerinde AI analizi çalıştırır ve ayarlara göre işlem açar.
    """
    logging.info("PROAKTİF TARAYICI: Tam tarama döngüsü başlatılıyor...")
    database.log_event("INFO", "Scanner", "Proaktif tarama döngüsü başlatıldı.")
    
    config = app_config.settings
    initial_candidates = await _fetch_candidates_from_sources(config)
    logging.info(f"PROAKTİF TARAYICI: {len(initial_candidates)} adet potansiyel aday bulundu.")
    database.log_event("INFO", "Scanner", f"{len(initial_candidates)} potansiyel aday ile tarama başladı.")

    final_candidates_to_analyze = []
    
    async def pre_filter_candidate(candidate):
        async with semaphore:
            try:
                entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
                indicators_result = await asyncio.to_thread(get_technical_indicators, f"{candidate['symbol']},{entry_timeframe}")
                
                if indicators_result.get("status") == "success":
                    rsi = indicators_result['data'].get('RSI')
                    adx = indicators_result['data'].get('ADX')
                    
                    if rsi is None or adx is None: return None

                    rsi_lower = config.get('PROACTIVE_SCAN_RSI_LOWER', 35)
                    rsi_upper = config.get('PROACTIVE_SCAN_RSI_UPPER', 65)
                    adx_threshold = config.get('PROACTIVE_SCAN_ADX_THRESHOLD', 20)

                    if (rsi < rsi_lower or rsi > rsi_upper) and adx > adx_threshold:
                        logging.info(f"Ön Filtre BAŞARILI: {candidate['symbol']} (RSI: {rsi:.2f}, ADX: {adx:.2f})")
                        return candidate
                return None
            except Exception as e:
                logging.error(f"Ön filtreleme sırasında {candidate['symbol']} için hata: {e}")
                return None

    if config.get("PROACTIVE_SCAN_PREFILTER_ENABLED", True):
        logging.info("PROAKTİF TARAYICI: AI öncesi teknik filtreleme başlatılıyor...")
        filter_tasks = [pre_filter_candidate(c) for c in initial_candidates]
        results = await asyncio.gather(*filter_tasks)
        final_candidates_to_analyze = [res for res in results if res is not None]
        log_msg = f"{len(initial_candidates)} adaydan {len(final_candidates_to_analyze)} tanesi ön filtreden geçti."
        logging.info(f"PROAKTİF TARAYICI: {log_msg}")
        database.log_event("INFO", "Scanner", log_msg)
    else:
        final_candidates_to_analyze = initial_candidates
        logging.info("PROAKTİF TARAYICI: Ön filtreleme kapalı, tüm adaylar AI analizine gönderilecek.")
    
    if not final_candidates_to_analyze:
        logging.info("PROAKTİF TARAYICI: AI ile analiz edilecek aday bulunamadı. Döngü sonlandırılıyor.")
        database.log_event("INFO", "Scanner", "AI analizi için kriterlere uyan aday bulunamadı.")
        return {"summary": {"total_scanned": len(initial_candidates), "pre_filtered_count": len(initial_candidates), "ai_analyzed": 0, "opportunities_found": 0, "auto_trades_opened": 0, "data_errors": 0}, "details": []}

    opportunities_found = []
    auto_trades_opened = []
    data_errors = 0
    
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    trend_timeframe = config.get('PROACTIVE_SCAN_TREND_TIMEFRAME', '4h')
    use_mta = config.get('PROACTIVE_SCAN_MTA_ENABLED', True)

    async def analyze_symbol(candidate):
        symbol = candidate['symbol']
        async with semaphore:
            try:
                current_price_val = await asyncio.to_thread(_fetch_price_natively, symbol)
                if not current_price_val:
                    return {"type": "error", "symbol": symbol, "message": "Fiyat bilgisi alınamadı."}

                entry_indicators_result = await asyncio.to_thread(get_technical_indicators, f"{symbol},{entry_timeframe}")
                if entry_indicators_result.get("status") != "success":
                    return {"type": "error", "symbol": symbol, "message": f"Teknik veri hatası: {entry_indicators_result.get('message')}"}

                final_prompt = ""
                if use_mta:
                    trend_indicators_result = await asyncio.to_thread(get_technical_indicators, f"{symbol},{trend_timeframe}")
                    if trend_indicators_result.get("status") != "success":
                        return {"type": "error", "symbol": symbol, "message": f"Trend verisi hatası: {trend_indicators_result.get('message')}"}
                    final_prompt = agent.create_mta_analysis_prompt(symbol, current_price_val, entry_timeframe, entry_indicators_result["data"], trend_timeframe, trend_indicators_result["data"])
                else:
                    final_prompt = agent.create_final_analysis_prompt(symbol, entry_timeframe, current_price_val, entry_indicators_result["data"])
                
                llm_result = await asyncio.to_thread(agent.llm_invoke_with_fallback, final_prompt)
                parsed_data = agent.parse_agent_response(llm_result.content)

                if not parsed_data:
                    return {"type": "error", "symbol": symbol, "message": "Yapay zekadan geçersiz yanıt."}

                if parsed_data.get('recommendation') in ['AL', 'SAT']:
                    if config.get('PROACTIVE_SCAN_AUTO_CONFIRM'):
                        try:
                            await asyncio.to_thread(open_new_trade, symbol=symbol, recommendation=parsed_data['recommendation'], timeframe=entry_timeframe, current_price=current_price_val)
                            return {"type": "success", "symbol": symbol, "message": f"Otomatik pozisyon açıldı: {parsed_data['recommendation']}"}
                        except TradeException as te:
                            return {"type": "critical", "symbol": symbol, "message": f"Otomatik işlem hatası: {te}"}
                    else:
                        database.log_event("SUCCESS", "Scanner", f"Fırsat bulundu: {parsed_data.get('recommendation')} {symbol}. Kullanıcı onayı bekleniyor.")
                        return {"type": "opportunity", "symbol": symbol, "data": parsed_data}
                
                return {"type": "info", "symbol": symbol, "message": f"Analiz sonucu: BEKLE."}
                
            except ResourceExhausted:
                logging.critical(f"Proaktif tarama döngüsü, tüm modellerin kotası dolduğu için durduruldu. Sembol: {symbol}")
                return {"type": "critical", "symbol": symbol, "message": f"Tüm AI modellerinin kotası doldu."}
            except Exception as e:
                logging.error(f"Proaktif tarama sırasında {symbol} analiz edilirken hata: {e}", exc_info=True)
                return {"type": "critical", "symbol": symbol, "message": f"Analiz sırasında kritik hata: {str(e)}"}

    analysis_tasks = [analyze_symbol(c) for c in final_candidates_to_analyze]
    analysis_results = await asyncio.gather(*analysis_tasks)
    
    for res in analysis_results:
        if res:
            if res['type'] == 'success': auto_trades_opened.append(res['symbol'])
            elif res['type'] == 'opportunity': opportunities_found.append(res['data'])
            elif res['type'] in ['error', 'critical']: data_errors += 1

    summary_msg = f"Tarama tamamlandı. Onay bekleyen: {len(opportunities_found)}, Otomatik açılan: {len(auto_trades_opened)}, Hata: {data_errors}"
    logging.info(f"PROAKTİF TARAYICI DÖNGÜSÜ TAMAMLANDI. Taranan: {len(initial_candidates)}, AI Analizi Yapılan: {len(final_candidates_to_analyze)}, Otomatik Açılan: {len(auto_trades_opened)}, Onay Bekleyen: {len(opportunities_found)}, Hata: {data_errors}")
    database.log_event("INFO", "Scanner", summary_msg)

    return {
        "summary": {
            "total_scanned": len(initial_candidates), 
            "pre_filtered_count": len(final_candidates_to_analyze), 
            "ai_analyzed": len(analysis_results), 
            "opportunities_found": len(opportunities_found), 
            "auto_trades_opened": len(auto_trades_opened), 
            "data_errors": data_errors
        },
        "details": analysis_results
    }