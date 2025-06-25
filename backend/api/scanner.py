# api/scanner.py
# @author: Memba Co.

import logging
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException
from core import scanner
import database
from tools import get_technical_indicators, _get_unified_symbol

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"]
)

@router.get("/candidates", summary="Veritabanında kayıtlı adayları listele")
async def get_saved_candidates():
    """
    Veritabanında kayıtlı olan son tarama adaylarını döndürür.
    Yeni bir tarama yapmaz.
    """
    try:
        candidates = database.get_all_scanner_candidates()
        return candidates
    except Exception as e:
        logging.error(f"Kayıtlı adaylar alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Adaylar alınırken bir sunucu hatası oluştu.")


@router.post("/candidates", summary="Yeni bir tarama yap ve sonuçları kaydet")
async def run_new_scan_and_save_candidates():
    """
    Piyasayı yeni fırsatlar için tarar, sonuçları veritabanına kaydeder
    (öncekileri silerek) ve yeni listeyi ve toplam taranan sayısını döndürür.
    """
    logging.info("API: Yeni tarama ve kaydetme isteği alındı.")
    try:
        # scan_result artık {"total_scanned": X, "found_candidates": [...]} formatında bir sözlük
        scan_result = await scanner.get_scan_candidates()
        
        # Veritabanına sadece bulunan adaylar listesini kaydet
        database.save_scanner_candidates(scan_result["found_candidates"])
        
        # Frontend'e tüm sonucu (hem listeyi hem sayıyı) gönder
        return scan_result
        
    except Exception as e:
        logging.error(f"Yeni tarama API'sinde kritik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Adaylar taranırken bir sunucu hatası oluştu: {str(e)}")


@router.post("/candidates/{symbol:path}/refresh", summary="Tek bir adayın verilerini yenile")
async def refresh_single_candidate(symbol: str):
    """
    Belirtilen tek bir sembol için gösterge verilerini yeniden çeker,
    veritabanını günceller ve güncel veriyi döndürür.
    """
    decoded_symbol = unquote(symbol)
    unified_symbol = _get_unified_symbol(decoded_symbol)
    logging.info(f"API: {unified_symbol} için aday yenileme isteği alındı.")
    try:
        all_candidates = database.get_all_scanner_candidates()
        db_candidate = next((c for c in all_candidates if c['symbol'] == unified_symbol), None)

        if not db_candidate:
            raise HTTPException(status_code=404, detail=f"Veritabanında {unified_symbol} adayı bulunamadı.")
        
        timeframe = db_candidate.get('timeframe', '15m')
        
        indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{unified_symbol},{timeframe}"})

        if indicators_result.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"{unified_symbol} için göstergeler alınamadı: {indicators_result.get('message')}")
        
        # GÜNCELLEME: Gelen verinin yapısını ve içeriğini daha sıkı doğrula
        new_indicators = indicators_result.get("data")
        if not new_indicators or "RSI" not in new_indicators or "ADX" not in new_indicators:
            raise HTTPException(status_code=500, detail=f"API'den {unified_symbol} için eksik gösterge verisi döndü.")

        database.update_scanner_candidate(unified_symbol, new_indicators)
        
        updated_candidate = next((c for c in database.get_all_scanner_candidates() if c['symbol'] == unified_symbol), None)
        
        if not updated_candidate:
            raise HTTPException(status_code=404, detail=f"Güncellenmiş aday veritabanında bulunamadı: {unified_symbol}")
            
        return updated_candidate

    except HTTPException as e:
        # FastAPI hatalarını doğrudan geri gönder
        raise e
    except Exception as e:
        logging.error(f"Aday yenileme sırasında hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Aday yenilenirken bir sunucu hatası oluştu.")
