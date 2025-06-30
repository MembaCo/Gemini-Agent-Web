# api/positions.py
# @author: Memba Co.

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging
from urllib.parse import unquote
from google.api_core.exceptions import ResourceExhausted

import database
from tools import get_open_positions_from_exchange, _get_unified_symbol, get_technical_indicators
from core.trader import open_new_trade, close_existing_trade, TradeException
from core.position_manager import refresh_single_position_pnl
from core import agent as core_agent
from tools import _fetch_price_natively

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

@router.get("/", summary="Tüm açık pozisyonları al (Anlık P&L ile)")
async def get_all_positions():
    """
    Veritabanındaki tüm aktif yönetilen pozisyonları döndürür.
    Her bir pozisyon için P&L, bu istek anında güncel fiyata göre yeniden hesaplanır.
    """
    try:
        managed_positions = database.get_all_positions()
        
        # Her pozisyon için P&L'i anlık olarak yeniden hesapla
        for pos in managed_positions:
            try:
                current_price = _fetch_price_natively(pos["symbol"])
                if current_price is not None:
                    entry_price = pos.get('entry_price', 0)
                    amount = pos.get('amount', 0)
                    leverage = pos.get('leverage', 1)

                    if entry_price > 0 and amount > 0:
                        pnl = (current_price - entry_price) * amount if pos['side'] == 'buy' else (entry_price - current_price) * amount
                        margin = (entry_price * amount) / leverage if leverage > 0 else 0
                        pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
                        
                        # Pozisyon sözlüğündeki değerleri güncelle
                        pos['pnl'] = pnl
                        pos['pnl_percentage'] = pnl_percentage
            except Exception as e:
                # Tek bir pozisyonda hata olursa logla ama devam et
                logging.warning(f"Anlık P&L hesaplanırken hata ({pos['symbol']}): {e}")


        return { "managed_positions": managed_positions, "unmanaged_positions": [] }
    except Exception as e:
        logging.error(f"Pozisyonlar alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pozisyonlar alınırken bir sunucu hatası oluştu.")



@router.post("/open", summary="Yeni bir ticaret pozisyonu aç")
async def open_position(request: PositionOpenRequest):
    """
    Bir analiz sonucuna dayanarak yeni bir ticaret pozisyonu açar.
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
    """
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    
    logging.info(f"API: Manuel PNL yenileme isteği alındı: {unified_symbol}")
    background_tasks.add_task(refresh_single_position_pnl, unified_symbol)
    
    return {"message": f"{unified_symbol} için PNL yenileme görevi başlatıldı."}

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
        
    try:
        # DÜZELTME: Eskiden agent'a devredilen bu mantık artık burada işleniyor.
        # Daha iyi bir analiz için güncel teknik verileri de prompt'a ekleyebiliriz,
        # ancak şimdilik eski basit yapıyı koruyoruz.
        reanalysis_prompt = core_agent.create_reanalysis_prompt(position_to_manage)
        
        logging.info(f"AI ile pozisyon yeniden analiz ediliyor: {unified_symbol}")
        
        # DÜZELTME: `llm_invoke_with_fallback` kullanılarak kota hatalarına karşı dayanıklılık sağlandı.
        result = core_agent.llm_invoke_with_fallback(reanalysis_prompt)
        
        parsed_data = core_agent.parse_agent_response(result.content)

        if not parsed_data or "recommendation" not in parsed_data:
            raise HTTPException(status_code=500, detail="Yeniden analiz sırasında Agent'tan geçerli bir tavsiye alınamadı.")
        
        parsed_data['symbol'] = unified_symbol
        return parsed_data
        
    except ResourceExhausted:
        logging.critical(f"Yeniden analiz sırasında tüm AI modellerinin kotası doldu: {unified_symbol}")
        raise HTTPException(status_code=429, detail="Tüm AI modelleri için kota aşıldı. Lütfen daha sonra tekrar deneyin veya planınızı yükseltin.")
    except Exception as e:
        logging.error(f"Pozisyon yeniden analiz edilirken hata oluştu ({unified_symbol}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pozisyon yeniden analiz edilirken beklenmedik bir hata oluştu.")
