# api/positions.py
# @author: Memba Co.

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging
from urllib.parse import unquote

# Gerekli modülleri import ediyoruz
import database
from tools import get_open_positions_from_exchange, _get_unified_symbol
from core.trader import open_new_trade, close_existing_trade, TradeException
from core.position_manager import refresh_single_position_pnl
# YENİ: Yeniden analiz için AI agent modülünü import ediyoruz.
from core import agent as core_agent

router = APIRouter(
    prefix="/positions",
    tags=["Positions"],
)

class PositionOpenRequest(BaseModel):
    """Yeni pozisyon açma isteği için veri modeli."""
    symbol: str
    recommendation: str
    timeframe: str
    price: float

@router.get("/", summary="Tüm açık pozisyonları al")
async def get_all_positions():
    """
    Veritabanındaki tüm aktif yönetilen pozisyonları döndürür.
    PNL ve diğer anlık veriler, arka planda çalışan position_manager tarafından
    periyodik olarak güncellenir.
    """
    try:
        managed_positions = database.get_all_positions()
        return {
            "managed_positions": managed_positions,
            "unmanaged_positions": [] # Gelecekte borsa ile senkronizasyon eklenebilir
        }
    except Exception as e:
        logging.error(f"Pozisyonlar alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pozisyonlar alınırken bir sunucu hatası oluştu.")


@router.post("/open", summary="Yeni bir ticaret pozisyonu aç")
async def open_position(request: PositionOpenRequest):
    """
    Bir analiz sonucuna dayanarak yeni bir ticaret pozisyonu açar.
    Tüm ticaret mantığı `core.trader` modülüne devredilir.
    """
    logging.info(f"API: Yeni pozisyon açma isteği alındı: {request.symbol}")
    try:
        result = open_new_trade(
            symbol=_get_unified_symbol(request.symbol),
            recommendation=request.recommendation,
            timeframe=request.timeframe,
            current_price=request.price
        )
        return result
    except TradeException as te:
        raise HTTPException(status_code=400, detail=str(te))
    except Exception as e:
        logging.error(f"Pozisyon açma API'sinde hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pozisyon açılırken beklenmedik bir sunucu hatası oluştu.")


@router.post("/{symbol:path}/close", summary="Belirtilen bir pozisyonu manuel olarak kapat")
async def close_position(symbol: str):
    """
    Belirtilen semboldeki açık pozisyonu manuel olarak kapatır.
    {symbol:path} kullanımı, sembol içindeki '/' karakterlerinin
    doğru bir şekilde tek bir parametre olarak okunmasını sağlar.
    """
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    logging.info(f"API: Pozisyon kapatma isteği alındı: {unified_symbol}")
    
    try:
        result = close_existing_trade(unified_symbol, close_reason="MANUAL_API_CLOSE")
        return result
    except TradeException as te:
        raise HTTPException(status_code=404, detail=str(te))
    except Exception as e:
        logging.error(f"Pozisyon kapatılırken beklenmedik bir hata oluştu ({unified_symbol}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pozisyon kapatılırken beklenmedik bir hata oluştu.")


@router.post("/{symbol:path}/refresh-pnl", summary="Tek bir pozisyonun PNL'ini anlık olarak yenile")
async def refresh_pnl(symbol: str, background_tasks: BackgroundTasks):
    """
    Belirtilen pozisyon için PNL'i anlık olarak yeniden hesaplar.
    İşlemi bir arka plan görevi olarak çalıştırarak arayüzün beklemesini önler.
    """
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    
    logging.info(f"API: Manuel PNL yenileme isteği alındı: {unified_symbol}")
    background_tasks.add_task(refresh_single_position_pnl, unified_symbol)
    
    return {"message": f"{unified_symbol} için PNL yenileme görevi başlatıldı."}

# YENİ API ENDPOINT'İ
@router.post("/{symbol:path}/reanalyze", summary="Mevcut bir pozisyonu yeniden analiz et")
async def reanalyze_position(symbol: str):
    """
    Veritabanından pozisyon detaylarını alarak, yapay zekaya bu pozisyonu
    yeniden analiz ettirir ve 'TUT' veya 'KAPAT' tavsiyesi döndürür.
    """
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    logging.info(f"API: Pozisyon yeniden analiz isteği alındı: {unified_symbol}")
    
    position_to_manage = database.get_position_by_symbol(unified_symbol)
    if not position_to_manage:
        raise HTTPException(status_code=404, detail=f"Yönetilen pozisyon bulunamadı: {unified_symbol}")
        
    reanalysis_prompt = core_agent.create_reanalysis_prompt(position_to_manage)
    
    try:
        logging.info(f"Agent Executor ile pozisyon yeniden analiz ediliyor: {unified_symbol}")
        result = core_agent.agent_executor.invoke({"input": reanalysis_prompt})
        parsed_data = core_agent.parse_agent_response(result.get("output", ""))

        if not parsed_data or "recommendation" not in parsed_data:
            raise HTTPException(status_code=500, detail="Yeniden analiz sırasında Agent'tan geçerli bir tavsiye alınamadı.")
        
        # Frontend'in pozisyonu tanıması için sembolü yanıta ekliyoruz.
        parsed_data['symbol'] = unified_symbol
        return parsed_data

    except Exception as e:
        logging.error(f"Pozisyon yeniden analiz edilirken hata oluştu ({unified_symbol}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pozisyon yeniden analiz edilirken beklenmedik bir hata oluştu.")
