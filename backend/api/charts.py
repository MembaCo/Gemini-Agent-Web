# ==============================================================================
# File: backend/api/charts.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta

from tools import exchange as exchange_tools

router = APIRouter(
    prefix="/charts",
    tags=["Charts"],
)

@router.get("/ohlcv", summary="Geçmiş mum grafiği verilerini al")
async def get_ohlcv_data(
    symbol: str = Query(..., example="BTC/USDT"), 
    timeframe: str = Query(..., example="1h"), 
    limit: int = Query(300, gt=0, le=1000) # Son 'limit' adet mumu çek
):
    """
    Belirtilen sembol ve zaman aralığı için frontend'de kullanılacak
    OHLCV (mum) verilerini çeker.
    """
    logging.info(f"API: OHLCV verisi isteği alındı - Sembol: {symbol}, Zaman Aralığı: {timeframe}")
    try:
        # ccxt'den veriyi çek
        bars = exchange_tools.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not bars:
            return []

        # lightweight-charts uyumlu formata dönüştür: {time, open, high, low, close}
        formatted_bars = [
            {
                "time": int(bar[0] / 1000), # Zaman damgasını saniyeye çevir
                "open": bar[1],
                "high": bar[2],
                "low": bar[3],
                "close": bar[4]
            }
            for bar in bars
        ]
        return formatted_bars
    except Exception as e:
        logging.error(f"OHLCV verisi çekilirken hata oluştu: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Grafik verileri alınırken bir sunucu hatası oluştu: {str(e)}")