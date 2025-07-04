# api/positions.py
# @author: Memba Co.

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging
from urllib.parse import unquote
import asyncio
from google.api_core.exceptions import ResourceExhausted

import database
# YENİ: get_price_with_cache import edildi
from tools import get_open_positions_from_exchange, _get_unified_symbol, get_price_with_cache
from core.trader import open_new_trade, close_existing_trade, TradeException
from core.position_manager import refresh_single_position_pnl
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

@router.get("/", summary="Tüm açık pozisyonları al (Anlık P&L ve Fiyat ile)")
async def get_all_positions():
    """
    Veritabanındaki tüm aktif yönetilen pozisyonları döndürür.
    Her bir pozisyon için P&L ve anlık fiyat bu istek anında yeniden hesaplanır.
    """
    try:
        managed_positions = database.get_all_positions()
        updated_positions = []

        for pos in managed_positions:
            pos_dict = dict(pos)
            try:
                # DEĞİŞİKLİK: _fetch_price_natively yerine get_price_with_cache kullanılıyor
                current_price = await asyncio.to_thread(get_price_with_cache, pos_dict["symbol"])
                
                if current_price is not None:
                    pos_dict['current_price'] = current_price

                    entry_price = pos_dict.get('entry_price', 0)
                    amount = pos_dict.get('amount', 0)
                    leverage = pos_dict.get('leverage', 1)

                    if entry_price > 0 and amount > 0:
                        pnl = (current_price - entry_price) * amount if pos_dict['side'] == 'buy' else (entry_price - current_price) * amount
                        margin = (entry_price * amount) / leverage if leverage > 0 else 0
                        pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
                        pos_dict['pnl'] = pnl
                        pos_dict['pnl_percentage'] = pnl_percentage
                
                updated_positions.append(pos_dict)
            except Exception as e:
                logging.warning(f"Anlık P&L hesaplanırken hata ({pos_dict['symbol']}): {e}")
                updated_positions.append(pos_dict) 

        return { "managed_positions": updated_positions, "unmanaged_positions": [] }
    except Exception as e:
        logging.error(f"Pozisyonlar alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pozisyonlar alınırken bir sunucu hatası oluştu.")

@router.post("/open", summary="Yeni bir ticaret pozisyonu aç")
async def open_position(request: PositionOpenRequest):
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
async def refresh_pnl(symbol: str):
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    logging.info(f"API: Manuel PNL yenileme isteği alındı: {unified_symbol}")
    await refresh_single_position_pnl(unified_symbol)
    return {"message": f"{unified_symbol} için PNL yenileme görevi tamamlandı."}

@router.post("/{symbol:path}/reanalyze", summary="Mevcut bir pozisyonu yeniden analiz et")
async def reanalyze_position(symbol: str):
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    position_to_manage = database.get_position_by_symbol(unified_symbol)
    if not position_to_manage:
        raise HTTPException(status_code=404, detail=f"Yönetilen pozisyon bulunamadı: {unified_symbol}")
    try:
        reanalysis_prompt = core_agent.create_reanalysis_prompt(position_to_manage)
        result = await asyncio.to_thread(core_agent.llm_invoke_with_fallback, reanalysis_prompt)
        parsed_data = core_agent.parse_agent_response(result.content)
        if not parsed_data or "recommendation" not in parsed_data:
            raise HTTPException(status_code=500, detail="Yeniden analiz sırasında Agent'tan geçerli bir tavsiye alınamadı.")
        parsed_data['symbol'] = unified_symbol
        return parsed_data
    except ResourceExhausted:
        raise HTTPException(status_code=429, detail="Tüm AI modelleri için kota aşıldı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pozisyon yeniden analiz edilirken hata: {e}")

# --- TOPLU İŞLEM ENDPOINT'LERİ ---

@router.post("/close-all", summary="Tüm açık pozisyonları kapat")
async def close_all_positions_endpoint(background_tasks: BackgroundTasks):
    positions = database.get_all_positions()
    if not positions:
        raise HTTPException(status_code=404, detail="Kapatılacak açık pozisyon bulunmuyor.")
    
    def close_task():
        for pos in positions:
            try:
                close_existing_trade(pos['symbol'], close_reason="MANUAL_CLOSE_ALL")
            except Exception as e:
                logging.error(f"Toplu kapatma sırasında {pos['symbol']} kapatılamadı: {e}")
                database.log_event("ERROR", "Trade", f"Toplu kapatma sırasında {pos['symbol']} kapatılamadı: {e}")

    background_tasks.add_task(close_task)
    return {"message": f"{len(positions)} pozisyon için kapatma işlemi arka planda başlatıldı."}

@router.post("/close-profitable", summary="Kârda olan tüm pozisyonları kapat")
async def close_profitable_positions_endpoint(background_tasks: BackgroundTasks):
    all_positions = database.get_all_positions()
    for pos in all_positions: await refresh_single_position_pnl(pos['symbol'])
    
    profitable_positions = [p for p in database.get_all_positions() if p.get('pnl', 0) > 0]
    if not profitable_positions:
        raise HTTPException(status_code=404, detail="Kapatılacak kârda pozisyon bulunmuyor.")

    def close_task():
        for pos in profitable_positions:
            try:
                close_existing_trade(pos['symbol'], close_reason="MANUAL_CLOSE_PROFITABLE")
            except Exception as e:
                logging.error(f"Kârdaki pozisyonları kapatırken hata ({pos['symbol']}): {e}")
    
    background_tasks.add_task(close_task)
    return {"message": f"{len(profitable_positions)} kârdaki pozisyon için kapatma işlemi başlatıldı."}

@router.post("/close-losing", summary="Zararda olan tüm pozisyonları kapat")
async def close_losing_positions_endpoint(background_tasks: BackgroundTasks):
    all_positions = database.get_all_positions()
    for pos in all_positions: await refresh_single_position_pnl(pos['symbol'])
    
    losing_positions = [p for p in database.get_all_positions() if p.get('pnl', 0) < 0]
    if not losing_positions:
        raise HTTPException(status_code=404, detail="Kapatılacak zararda pozisyon bulunmuyor.")

    def close_task():
        for pos in losing_positions:
            try:
                close_existing_trade(pos['symbol'], close_reason="MANUAL_CLOSE_LOSING")
            except Exception as e:
                logging.error(f"Zarardaki pozisyonları kapatırken hata ({pos['symbol']}): {e}")
                
    background_tasks.add_task(close_task)
    return {"message": f"{len(losing_positions)} zarardaki pozisyon için kapatma işlemi başlatıldı."}

@router.post("/reanalyze-all", summary="Tüm açık pozisyonları yeniden analiz et")
async def reanalyze_all_positions_endpoint():
    positions = database.get_all_positions()
    if not positions:
        raise HTTPException(status_code=404, detail="Analiz edilecek pozisyon bulunmuyor.")

    async def analyze_task(position):
        try:
            reanalysis_prompt = core_agent.create_reanalysis_prompt(position)
            result = await asyncio.to_thread(core_agent.llm_invoke_with_fallback, reanalysis_prompt)
            parsed_data = core_agent.parse_agent_response(result.content)
            if parsed_data:
                parsed_data['symbol'] = position['symbol']
                return parsed_data
            return {"symbol": position['symbol'], "recommendation": "HATA", "reason": "AI yanıtı ayrıştırılamadı."}
        except Exception as e:
            logging.error(f"Toplu yeniden analiz sırasında hata ({position['symbol']}): {e}")
            return {"symbol": position['symbol'], "recommendation": "HATA", "reason": str(e)}

    tasks = [analyze_task(pos) for pos in positions]
    results = await asyncio.gather(*tasks)
    return results