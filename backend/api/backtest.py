# backend/api/backtest.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import Field
import logging

# YENİ: Borsa bağlantısını doğrudan kontrol etmek yerine modülü import ediyoruz
from tools import exchange as exchange_tools
from core.backtester import Backtester
from core.security import get_current_user
from .schemas import BacktestRunRequest

class BacktestRunRequestWithBalance(BacktestRunRequest):
    initial_balance: int = Field(..., gt=0, description="Initial balance for backtesting")

router = APIRouter(
    prefix="/backtest",
    tags=["Backtest"],
)

@router.post("/run", summary="Geriye dönük test çalıştır")
async def run_backtest(
    request_data: BacktestRunRequestWithBalance,
    current_user: str = Depends(get_current_user)
):
    # --- YENİ VE DAHA ANLAŞILIR HATA KONTROLÜ ---
    # DÜZELTME: Borsa bağlantısının varlığı modül üzerinden kontrol ediliyor.
    if not exchange_tools.exchange:
        logging.error("Backtest API çağrıldı ancak borsa bağlantısı (exchange) mevcut değil. Başlangıçta API anahtarlarıyla ilgili bir sorun var.")
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail={
                "error": "Borsa Bağlantısı Kurulamadı",
                "message": "Backtest işlemi, geçmiş fiyat verilerini çekmek için borsa bağlantısı gerektirir. Uygulama başlangıcında bu bağlantı kurulamadı.",
                "olasi_nedenler": [
                    "1. `backend/.env` dosyasında BINANCE_API_KEY veya BINANCE_SECRET_KEY eksik veya yanlış.",
                    "2. Binance'te oluşturulan API anahtarlarının 'Vadeli İşlemler' veya 'Spot' için okuma izni yok.",
                    "3. Sunucunun internet bağlantısında veya Binance API sunucularına erişiminde bir sorun var."
                ],
                "cozum_onerisi": "Lütfen `backend/.env` dosyanızdaki Binance API anahtarlarınızı dikkatlice kontrol edin ve Docker konteynerini yeniden başlatın (`docker-compose down && docker-compose up --build`)."
            }
        )
    # --- KONTROL SONU ---

    logging.info(f"Kullanıcı '{current_user}' tarafından geriye dönük test isteği alındı.")
    
    try:
        preset_data = request_data.preset.model_dump(exclude_unset=True)
        logging.info(f"Geriye dönük test başlatılıyor: {request_data.symbol} with preset: {preset_data}")

        backtester = Backtester(
            initial_balance=request_data.initial_balance,
            preset=preset_data
        )
        
        results = backtester.run(
            symbol=request_data.symbol,
            interval=request_data.interval,
            start_date=request_data.start_date,
            end_date=request_data.end_date
        )
        
        if results is None:
            raise HTTPException(status_code=500, detail="Geriye dönük test bir sonuç döndürmedi. Sunucu loglarını kontrol edin.")
        
        if isinstance(results, dict) and 'message' in results:
             raise HTTPException(status_code=404, detail=results['message'])

        if 'balance_history' in results and isinstance(results.get('balance_history'), dict):
            results['balance_history'] = {str(k): v for k, v in results['balance_history'].items()}

        return results
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(f"Geriye dönük test sırasında kritik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Geriye dönük test sırasında beklenmedik bir sunucu hatası oluştu: {str(e)}")