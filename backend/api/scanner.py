# api/scanner.py
# @author: Memba Co.

import logging
from fastapi import APIRouter, HTTPException
from core import scanner

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"]
)

@router.post("/run", summary="Proaktif tarayıcıyı manuel olarak tetikle ve sonuçları al")
async def run_manual_scan():
    """
    Proaktif tarama döngüsünü çalıştırır ve taramanın sonuçlarını
    doğrudan JSON olarak döndürür. Bu, frontend'in sonuçları bir modalda
    göstermesini sağlar.
    """
    logging.info("API: Manuel proaktif tarama isteği alındı.")
    try:
        # DÜZELTME: Fonksiyonu doğrudan çağırıp sonucunu alıyoruz.
        # Arka plan görevi yerine, sonucun dönmesini bekliyoruz.
        scan_results = scanner.execute_single_scan_cycle()
        return scan_results
    except Exception as e:
        logging.error(f"Tarama API'sinde kritik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tarama sırasında bir sunucu hatası oluştu: {str(e)}")

