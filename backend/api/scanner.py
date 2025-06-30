# api/scanner.py
# @author: Memba Co.

import logging
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException
# DÜZELTME: İsim çakışmasını önlemek için 'core.scanner' modülü 'core_scanner' olarak import ediliyor.
from core import scanner as core_scanner
import database
from tools import get_technical_indicators, _get_unified_symbol

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"]
)

@router.get("/candidates", summary="Get saved candidates for the interactive scanner")
async def get_saved_candidates():
    """
    Veritabanında kayıtlı olan son tarama adaylarını döndürür.
    Bu, interaktif tarayıcı sayfasını başlangıçta doldurmak için kullanılır.
    Yeni bir tarama yapmaz.
    """
    try:
        candidates = database.get_all_scanner_candidates()
        return candidates
    except Exception as e:
        logging.error(f"Kayıtlı adaylar alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Adaylar alınırken bir sunucu hatası oluştu.")

@router.post("/run-interactive-scan", summary="Run a new interactive scan and save candidates")
async def run_new_interactive_scan():
    """
    Piyasayı potansiyel fırsatlar için teknik göstergelere göre tarar (AI analizi OLMADAN),
    sonuçları veritabanına kaydeder (öncekileri silerek) ve yeni listeyi döndürür.
    """
    logging.info("API: Yeni interaktif tarama isteği alındı.")
    try:
        # DÜZELTME: Çağrı, yeniden adlandırılan 'core_scanner' üzerinden yapılıyor.
        candidates = await core_scanner.get_interactive_scan_candidates()
        database.save_scanner_candidates(candidates)
        return candidates
    except Exception as e:
        logging.error(f"Yeni interaktif tarama API'sinde hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Adaylar taranırken bir sunucu hatası oluştu: {str(e)}")

@router.post("/run-proactive-scan", summary="Manually trigger a full proactive scan cycle")
async def run_proactive_scan():
    """
    Ayarlara dayalı olarak AI analizi ve potansiyel otomatik işlem gerçekleştirmeyi
    içeren tam bir proaktif tarama döngüsünü manuel olarak tetikler.
    Tarama sonuçlarının bir raporunu döndürür.
    """
    logging.info("API: Proaktif tarama döngüsünü manuel tetikleme isteği alındı.")
    try:
        # DÜZELTME: Çağrı, yeniden adlandırılan 'core_scanner' üzerinden yapılıyor.
        scan_result = await core_scanner.execute_single_scan_cycle()
        return scan_result
    except Exception as e:
        logging.error(f"Proaktif tarama API'sinde hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Proaktif tarama sırasında sunucu hatası: {str(e)}")

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
        
        indicators_result = get_technical_indicators(f"{unified_symbol},{timeframe}")

        if indicators_result.get("status") != "success":
            raise HTTPException(status_code=400, detail=f"{unified_symbol} için göstergeler alınamadı: {indicators_result.get('message')}")
        
        new_indicators = indicators_result.get("data")
        if not new_indicators or "RSI" not in new_indicators or "ADX" not in new_indicators:
            raise HTTPException(status_code=500, detail=f"API'den {unified_symbol} için eksik gösterge verisi döndü.")

        database.update_scanner_candidate(unified_symbol, new_indicators)
        
        updated_candidate = next((c for c in database.get_all_scanner_candidates() if c['symbol'] == unified_symbol), None)
        
        if not updated_candidate:
            raise HTTPException(status_code=404, detail=f"Güncellenmiş aday veritabanında bulunamadı: {unified_symbol}")
            
        return updated_candidate

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Aday yenileme sırasında hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Aday yenilenirken bir sunucu hatası oluştu.")