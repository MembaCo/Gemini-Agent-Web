# backend/api/analysis.py
# @author: Memba Co.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
import asyncio 
from ccxt.base.errors import BadSymbol
from google.api_core.exceptions import ResourceExhausted

from core import agent as core_agent, app_config
# --- GÜNCELLENDİ: Haber ve duyarlılık fonksiyonları import edildi ---
from tools import (
    _get_technical_indicators_logic, 
    get_price_with_cache, 
    _get_unified_symbol,
    get_latest_crypto_news,
    get_twitter_sentiment
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])

class NewAnalysisRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"

@router.post("/new", summary="Yeni bir kripto para analizi yap")
async def perform_new_analysis(request: NewAnalysisRequest):
    unified_symbol = _get_unified_symbol(request.symbol)
    logging.info(f"API: Yeni analiz isteği alındı - Sembol: {unified_symbol}, Zaman Aralığı: {request.timeframe}")
    try:
        current_price = await asyncio.to_thread(get_price_with_cache, unified_symbol)
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"Fiyat bilgisi alınamadı: {unified_symbol}")
            
        # --- YENİ: HABER VE DUYARLILIK AYAR KONTROLÜ ---
        use_news = app_config.settings.get('PROACTIVE_SCAN_USE_NEWS', False)
        use_sentiment = app_config.settings.get('PROACTIVE_SCAN_USE_SENTIMENT', False)

        # Tüm verileri asenkron olarak topla
        entry_indicators_task = asyncio.to_thread(_get_technical_indicators_logic, unified_symbol, request.timeframe)
        
        news_task = asyncio.to_thread(get_latest_crypto_news, unified_symbol) if use_news else asyncio.sleep(0, result=[])
        sentiment_task = asyncio.to_thread(get_twitter_sentiment, unified_symbol) if use_sentiment else asyncio.sleep(0, result={})

        entry_indicators_result, news_headlines, sentiment_data = await asyncio.gather(
            entry_indicators_task, news_task, sentiment_task
        )
        # --- BİTİŞ ---

        if entry_indicators_result.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"Analiz yapılamadı: {entry_indicators_result.get('message')}")
            
        final_prompt = ""

        # --- YENİ: HANGİ PROMPT'UN KULLANILACAĞINA KARAR VERME ---
        if use_news or use_sentiment:
            logging.info(f"Manuel Analiz: Bütüncül (Holistic) analiz tetiklendi. Haberler: {use_news}, Duyarlılık: {use_sentiment}")
            final_prompt = core_agent.create_holistic_analysis_prompt(
                symbol=unified_symbol,
                price=current_price,
                timeframe=request.timeframe,
                indicators=entry_indicators_result["data"],
                news_headlines=news_headlines,
                sentiment_score=sentiment_data.get("score", 0.0)
            )
        else:
            # --- ESKİ MANTIĞA GERİ DÖN (SADECE TEKNİK ANALİZ) ---
            logging.info("Manuel Analiz: Sadece teknik analiz tetiklendi.")
            use_mta = app_config.settings.get('USE_MTA_ANALYSIS', True)
            trend_timeframe = app_config.settings.get('MTA_TREND_TIMEFRAME', '4h')
            
            if use_mta and request.timeframe != trend_timeframe:
                trend_indicators_result = await asyncio.to_thread(_get_technical_indicators_logic, unified_symbol, trend_timeframe)
                if trend_indicators_result.get("status") != "success":
                    raise HTTPException(status_code=400, detail=f"Trend analizi ({trend_timeframe}) için veri alınamadı: {trend_indicators_result.get('message')}")
                final_prompt = core_agent.create_mta_analysis_prompt(unified_symbol, current_price, request.timeframe, entry_indicators_result["data"], trend_timeframe, trend_indicators_result["data"])
            else:
                final_prompt = core_agent.create_final_analysis_prompt(unified_symbol, request.timeframe, current_price, entry_indicators_result["data"])
        
        result = await asyncio.to_thread(core_agent.llm_invoke_with_fallback, final_prompt)
        
        parsed_data = core_agent.parse_agent_response(result.content)
        if not parsed_data:
            raise HTTPException(status_code=500, detail="Yapay zekadan geçerli bir analiz yanıtı alınamadı.")
        return parsed_data
        
    except BadSymbol as e:
        raise HTTPException(status_code=404, detail=f"Geçersiz sembol: {str(e)}")
    except ResourceExhausted:
        logging.critical("Tüm AI modellerinin kotaları tükendi. Lütfen planınızı kontrol edin.")
        raise HTTPException(status_code=429, detail="Tüm AI modelleri için kota aşıldı. Lütfen daha sonra tekrar deneyin veya planınızı yükseltin.")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(f"Yeni analiz sırasında beklenmedik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analiz sırasında beklenmedik bir sunucu hatası oluştu: {str(e)}")