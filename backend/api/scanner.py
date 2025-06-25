# api/scanner.py
# @author: Memba Co.

import logging
from fastapi import APIRouter, HTTPException
from core import scanner

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"]
)

# === YENİ ENDPOINT ===
@router.post("/candidates", summary="AI analizi için potansiyel adayları tara ve listele")
async def get_candidates():
    """
    Tüm kaynaklardan potansiyel sembolleri toplar, ön filtreden geçirir
    ve sadece analize hazır olanları bir liste olarak döndürür.
    Bu endpoint, AI analizi YAPMAZ.
    """
    logging.info("API: Tarayıcı aday listesi için istek alındı.")
    try:
        candidates = scanner.get_scan_candidates()
        return candidates
    except Exception as e:
        logging.error(f"Aday tarama API'sinde kritik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Adaylar taranırken bir sunucu hatası oluştu: {str(e)}")

# Eski endpoint'i kaldırabilir veya bırakabiliriz. Şimdilik bırakalım.
@router.post("/run", summary="DEPRECATED: Proaktif tarayıcıyı manuel olarak tetikle")
async def run_manual_scan():
    """
    Bu endpoint artık kullanımdan kaldırılmıştır. Lütfen /candidates kullanın.
    """
    return scanner.execute_single_scan_cycle()

