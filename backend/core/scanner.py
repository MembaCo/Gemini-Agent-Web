# backend/core/scanner.py
# @author: MembaCo.

import pandas as pd
import logging
import asyncio
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted

import database
from core import app_config, agent
from core.trader import open_new_trade, TradeException
from tools import (
    get_top_gainers_losers,
    get_volume_spikes,
    _get_technical_indicators_logic,
    get_price_with_cache,
    get_latest_crypto_news,
    get_twitter_sentiment,
    # YENİ: Yeni piyasa keşif fonksiyonları import ediliyor
    get_technical_screener_results,
    get_socially_trending_coins
)
from tools.utils import _get_unified_symbol
from tools import exchange as exchange_tools

CONCURRENCY_LIMIT = 10
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


async def _fetch_candidates_from_sources(config: dict) -> list[dict]:
    """
    Tüm kaynaklardan (Whitelist, Gainers/Losers, Volume Spike, Screener, Social)
    potansiyel işlem adaylarını toplar ve blacklist ile filtreler.
    """
    all_symbols_with_source = {}

    # --- Mevcut Kaynaklar ---
    whitelist = config.get('PROACTIVE_SCAN_WHITELIST', [])
    for symbol in whitelist:
        unified_symbol = _get_unified_symbol(symbol)
        all_symbols_with_source[unified_symbol] = {"symbol": unified_symbol, "source": "Whitelist"}

    async def fetch_gainers_losers():
        if config.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
            top_n = config.get('PROACTIVE_SCAN_TOP_N', 10)
            min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
            async with semaphore:
                return await asyncio.to_thread(get_top_gainers_losers, top_n, min_volume_usdt)
        return []

    async def fetch_volume_spikes():
        if config.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
            volume_timeframe = config.get('PROACTIVE_SCAN_VOLUME_TIMEFRAME', '1h')
            volume_period = config.get('PROACTIVE_SCAN_VOLUME_PERIOD', 24)
            volume_multiplier = config.get('PROACTIVE_SCAN_VOLUME_MULTIPLIER', 5.0)
            min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
            async with semaphore:
                return await asyncio.to_thread(get_volume_spikes, volume_timeframe, volume_period, volume_multiplier, min_volume_usdt)
        return []

    # --- YENİ: Yeni Kaynakları Çeken Fonksiyonlar ---
    async def fetch_screener_results():
        async with semaphore:
            return await asyncio.to_thread(get_technical_screener_results)

    async def fetch_social_trends():
        async with semaphore:
            return await asyncio.to_thread(get_socially_trending_coins)

    # --- Tüm kaynakları paralel olarak çalıştır ---
    results = await asyncio.gather(
        fetch_gainers_losers(),
        fetch_volume_spikes(),
        fetch_screener_results(),
        fetch_social_trends()
    )
    gainers_losers_results, volume_spikes_results, screener_results, social_results = results

    # --- Sonuçları tek bir listede birleştir ---
    for item in gainers_losers_results:
        if item['symbol'] not in all_symbols_with_source:
            all_symbols_with_source[item['symbol']] = {"symbol": item['symbol'], "source": "Gainers/Losers"}
    for item in volume_spikes_results:
        if item['symbol'] not in all_symbols_with_source:
            all_symbols_with_source[item['symbol']] = {"symbol": item['symbol'], "source": "Volume Spike"}
    for symbol in screener_results:
        unified_symbol = _get_unified_symbol(symbol)
        if unified_symbol not in all_symbols_with_source:
            all_symbols_with_source[unified_symbol] = {"symbol": unified_symbol, "source": "Technical Screener"}
    for symbol in social_results:
        unified_symbol = _get_unified_symbol(symbol)
        if unified_symbol not in all_symbols_with_source:
            all_symbols_with_source[unified_symbol] = {"symbol": unified_symbol, "source": "Social Trend"}


    blacklist = {s.upper().strip() for s in config.get('PROACTIVE_SCAN_BLACKLIST', [])}
    final_candidates = [ data for symbol, data in all_symbols_with_source.items() if symbol.split('/')[0] not in blacklist ]
    return final_candidates


async def get_interactive_scan_candidates() -> list[dict]:
    """İnteraktif tarayıcı için göstergeleriyle birlikte adayları çeker."""
    logging.info("İNTERAKTİF TARAYICI: Aday listesi oluşturuluyor...")
    config = app_config.settings
    candidates_without_indicators = await _fetch_candidates_from_sources(config)
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    
    async def fetch_indicators(cand):
        async with semaphore:
            indicators_result = await asyncio.to_thread(_get_technical_indicators_logic, cand['symbol'], entry_timeframe)
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
        symbol = candidate['symbol']
        async with semaphore:
            try:
                entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
                bars = await asyncio.to_thread(exchange_tools.exchange.fetch_ohlcv, symbol, timeframe=entry_timeframe, limit=100)
                if not bars or len(bars) < 50:
                    logging.debug(f"Ön Filtre BAŞARISIZ ({symbol}): Yetersiz mum verisi.")
                    return None
                
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # İndikatörleri hesapla
                rsi_period = config.get('PROACTIVE_SCAN_RSI_PERIOD', 14)
                adx_period = config.get('PROACTIVE_SCAN_ADX_PERIOD', 14)
                atr_period = config.get('PROACTIVE_SCAN_ATR_PERIOD', 14)
                volume_avg_period = config.get('PROACTIVE_SCAN_VOLUME_AVG_PERIOD', 20)

                df.ta.rsi(length=rsi_period, append=True)
                df.ta.adx(length=adx_period, append=True)
                df.ta.atr(length=atr_period, append=True)
                df['volume_ema'] = df['volume'].ewm(span=volume_avg_period, adjust=False).mean()

                df.dropna(inplace=True)
                if df.empty:
                    logging.debug(f"Ön Filtre BAŞARISIZ ({symbol}): Gösterge hesaplaması sonrası veri kalmadı.")
                    return None

                last = df.iloc[-1]
                rsi = last.get(f"RSI_{rsi_period}")
                adx = last.get(f"ADX_{adx_period}")
                atr = last.get(f"ATRr_{atr_period}")
                
                if rsi is None or adx is None or atr is None:
                    logging.debug(f"Ön Filtre BAŞARISIZ ({symbol}): Gösterge değeri (RSI/ADX/ATR) hesaplanamadı.")
                    return None

                # Filtreleme Mantığı
                rsi_lower = config.get('PROACTIVE_SCAN_RSI_LOWER', 35)
                rsi_upper = config.get('PROACTIVE_SCAN_RSI_UPPER', 65)
                adx_threshold = config.get('PROACTIVE_SCAN_ADX_THRESHOLD', 20)
                
                if not ((rsi < rsi_lower or rsi > rsi_upper) and adx > adx_threshold):
                    logging.debug(f"Ön Filtre BAŞARISIZ ({symbol}): RSI ({rsi:.1f}) veya ADX ({adx:.1f}) kriterini geçemedi.")
                    return None

                if config.get('PROACTIVE_SCAN_USE_VOLATILITY_FILTER', True):
                    atr_threshold = config.get('PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT', 0.5)
                    # pandas-ta ATRr, sonucu 100 ile çarparak yüzde olarak verir.
                    if atr < atr_threshold:
                        logging.debug(f"Ön Filtre BAŞARISIZ ({symbol}): Yetersiz volatilite (ATR: {atr:.2f}% < {atr_threshold}%)")
                        return None
                
                if config.get('PROACTIVE_SCAN_USE_VOLUME_FILTER', True):
                    volume_multiplier = config.get('PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER', 1.2)
                    if last['volume'] < last['volume_ema'] * volume_multiplier:
                        logging.debug(f"Ön Filtre BAŞARISIZ ({symbol}): Yetersiz hacim onayı (Son Hacim: {last['volume']:.0f} < Ort. Hacim: {last['volume_ema']:.0f} * {volume_multiplier})")
                        return None
                
                log_message = f"Ön Filtre BAŞARILI: {symbol} (RSI:{rsi:.1f}, ADX:{adx:.1f}, ATR:{atr:.2f}%)"
                logging.info(log_message)
                database.log_event("INFO", "Scanner", log_message)
                return candidate

            except Exception as e:
                logging.error(f"Ön filtreleme sırasında {symbol} için hata: {e}")
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
        return {"summary": {"total_scanned": len(initial_candidates), "pre_filtered_count": 0, "ai_analyzed": 0, "opportunities_found": 0, "auto_trades_opened": 0, "data_errors": 0}, "details": []}

    opportunities_found = []
    auto_trades_opened = []
    data_errors = 0
    
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')

    async def analyze_symbol(candidate):
        symbol = candidate['symbol']
        async with semaphore:
            try:
                # --- TÜM VERİLERİ ASENKRON OLARAK ÇEK ---
                price_task = asyncio.to_thread(get_price_with_cache, symbol)
                indicators_task = asyncio.to_thread(_get_technical_indicators_logic, symbol, entry_timeframe)
                news_task = asyncio.to_thread(get_latest_crypto_news, symbol)
                sentiment_task = asyncio.to_thread(get_twitter_sentiment, symbol)

                current_price_val, indicators_result, news_headlines, sentiment_data = await asyncio.gather(
                    price_task, indicators_task, news_task, sentiment_task
                )
                # --- VERİ ÇEKME SONU ---

                if not current_price_val:
                    return {"type": "error", "symbol": symbol, "message": "Fiyat bilgisi alınamadı."}
                if indicators_result.get("status") != "success":
                    return {"type": "error", "symbol": symbol, "message": f"Teknik veri hatası: {indicators_result.get('message')}"}

                # --- YENİ BÜTÜNCÜL PROMPT'U KULLAN ---
                final_prompt = agent.create_holistic_analysis_prompt(
                    symbol=symbol,
                    price=current_price_val,
                    timeframe=entry_timeframe,
                    indicators=indicators_result["data"],
                    news_headlines=news_headlines,
                    sentiment_score=sentiment_data.get("score", 0.0)
                )
                
                llm_result = await asyncio.to_thread(agent.llm_invoke_with_fallback, final_prompt)
                parsed_data = agent.parse_agent_response(llm_result.content)

                if not parsed_data:
                    return {"type": "error", "symbol": symbol, "message": "Yapay zekadan geçersiz yanıt."}

                if parsed_data.get('recommendation') in ['AL', 'SAT']:
                    if config.get('PROACTIVE_SCAN_AUTO_CONFIRM'):
                        try:
                            open_new_trade(
                                symbol=symbol, 
                                recommendation=parsed_data['recommendation'], 
                                timeframe=entry_timeframe, 
                                current_price=current_price_val,
                                reason=parsed_data.get('reason', 'Otomatik Tarayıcı')
                            )
                            return {"type": "success", "symbol": symbol, "message": f"Otomatik pozisyon açıldı: {parsed_data['recommendation']}", "data": parsed_data}
                        except TradeException as e:
                             logging.error(f"Otomatik işlem açılırken hata ({symbol}): {e}")
                             return {"type": "error", "symbol": symbol, "message": f"Otomatik işlem hatası: {e}"}
                    else:
                        return {"type": "opportunity", "data": parsed_data}
                
                return {"type": "neutral", "data": parsed_data}

            except ResourceExhausted:
                logging.critical(f"Proaktif tarama döngüsü, tüm modellerin kotası dolduğu için durduruldu. Sembol: {symbol}")
                return {"type": "critical", "symbol": symbol, "message": f"Tüm AI modellerinin kotası doldu."}
            except Exception as e:
                logging.error(f"Proaktif tarama sırasında {symbol} analiz edilirken hata: {e}", exc_info=True)
                return {"type": "critical", "symbol": symbol, "message": f"Analiz sırasında kritik hata: {str(e)}"}

    analysis_tasks = [analyze_symbol(c) for c in final_candidates_to_analyze]
    analysis_results = await asyncio.gather(*analysis_tasks)
    
    final_opportunities = [res['data'] for res in analysis_results if res and res.get('type') == 'opportunity']
    final_auto_trades = [res['data'] for res in analysis_results if res and res.get('type') == 'success']
    final_errors = [res for res in analysis_results if res and res.get('type') in ['error', 'critical']]
    
    summary_msg = f"Tarama tamamlandı. Onay bekleyen: {len(final_opportunities)}, Otomatik açılan: {len(final_auto_trades)}, Hata: {len(final_errors)}"
    logging.info(f"PROAKTİF TARAYICI DÖNGÜSÜ TAMAMLANDI. Taranan: {len(initial_candidates)}, Ön Filtreden Geçen: {len(final_candidates_to_analyze)}, AI Analizi Yapılan: {len(analysis_tasks)}, {summary_msg}")
    database.log_event("INFO", "Scanner", summary_msg)

    return {
        "summary": {
            "total_scanned": len(initial_candidates), 
            "pre_filtered_count": len(final_candidates_to_analyze), 
            "ai_analyzed": len(analysis_tasks), 
            "opportunities_found": len(final_opportunities), 
            "auto_trades_opened": len(final_auto_trades), 
            "data_errors": len(final_errors)
        },
        "details": analysis_results
    }