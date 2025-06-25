# ==============================================================================
# File: backend/api/backtest.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import date

from core.backtester import Backtester

router = APIRouter(
    prefix="/backtest",
    tags=["Backtesting"],
)

class BacktestRequest(BaseModel):
    symbol: str = Field(..., example="BTC/USDT")
    timeframe: str = Field(..., example="4h")
    start_date: date = Field(..., example="2023-01-01")
    end_date: date = Field(..., example="2023-12-31")
    initial_balance: float = Field(1000, gt=0)
    # Strateji ayarları isteğe bağlı, gönderilmezse mevcut ayarlar kullanılır
    strategy_settings: dict | None = None

@router.post("/run", summary="Yeni bir geriye dönük test (backtest) başlat")
async def run_backtest(request: BacktestRequest):
    """
    Belirtilen parametreler ve strateji ile bir backtest simülasyonu çalıştırır
    ve sonuçları döndürür.
    """
    logging.info(f"API: Yeni backtest isteği alındı - {request.symbol}")
    try:
        backtester = Backtester(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date.strftime('%Y-%m-%d'),
            end_date=request.end_date.strftime('%Y-%m-%d'),
            initial_balance=request.initial_balance,
            strategy_settings=request.strategy_settings
        )
        report = backtester.run()
        return report
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Backtest sırasında kritik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest sırasında beklenmedik bir sunucu hatası oluştu: {str(e)}")