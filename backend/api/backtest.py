# backend/api/backtest.py

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError, Field, conint, constr
from typing import Dict, Any
import logging # Standard logging modülü eklendi

from core.backtester import Backtester
from core.security import get_current_user # Kimlik doğrulama için gerekli
from .schemas import BacktestRunRequest, format_pydantic_errors # format_pydantic_errors hala kullanılabilir durumda

# BacktestRunRequest şemasına initial_balance alanını eklemek için yeni bir model oluşturuldu
class BacktestRunRequestWithBalance(BacktestRunRequest):
    initial_balance: conint(gt=0) = Field(..., description="Initial balance for backtesting")


router = APIRouter(
    prefix="/backtest", # Bu önek, main.py'deki /api ile birleşerek /api/backtest yolunu oluşturur
    tags=["Backtest"],
)

@router.post("/run", summary="Geriye dönük test çalıştır")
async def run_backtest(
    request_data: BacktestRunRequestWithBalance, # FastAPI, Pydantic modelini otomatik olarak enjekte eder
    current_user: str = Depends(get_current_user) # Kimlik doğrulama bağımlılığı
):
    logging.info(f"Kullanıcı tarafından geriye dönük test isteği: {current_user}") # Kimlik doğrulanmış kullanıcıyı logla

    try:
        # Pydantic doğrulaması FastAPI tarafından request_data tipiyle otomatik olarak yapılır,
        # bu nedenle temel doğrulamalar için açık bir try-except ValidationError bloğuna gerek yoktur
        # çünkü FastAPI, doğrulama hataları için HTTP 422 döndürür.
        
        logging.info(f"Geriye dönük test başlatılıyor: {request_data.symbol}")

        # Backtester sınıfını initial_balance ile başlatın
        backtester = Backtester(initial_balance=request_data.initial_balance)
        
        results = backtester.run(
            symbol=request_data.symbol,
            interval=request_data.interval,
            start_date=request_data.start_date,
            end_date=request_data.end_date,
            preset=request_data.preset.model_dump() # Nested Pydantic modeli için .model_dump() doğru
        )
        
        if results is None:
            raise HTTPException(status_code=500, detail="Geriye dönük test sonuç üretemedi. Belirtilen dönem için veri olup olmadığını kontrol edin.")
        
        # Sonuçları JSON serileştirmesi için hazır hale getiriyoruz.
        # Özellikle balance_history'deki pandas zaman damgaları için bu önemlidir.
        if 'balance_history' in results:
            # Zaman damgası anahtarlarını JSON serileştirmesi için string'e dönüştür
            results['balance_history'] = {str(k): v for k, v in results['balance_history'].items()}

        return results # FastAPI, JSON serileştirmesini otomatik olarak halleder
    
    except HTTPException as http_exc:
        # FastAPI'nin HTTP hatalarını tekrar fırlat
        raise http_exc
    except Exception as e:
        # Beklenmedik hataları logla ve HTTP 500 hatası döndür
        logging.error(f"Geriye dönük test sırasında hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Geriye dönük test sırasında beklenmedik bir sunucu hatası oluştu: {str(e)}")