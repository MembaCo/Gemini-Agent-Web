# ==============================================================================
# File: backend/api/presets.py
# @author: Memba Co.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import database

router = APIRouter(
    prefix="/presets",
    tags=["Strategy Presets"],
)

class PresetCreate(BaseModel):
    name: str
    settings: dict

@router.get("/", summary="Tüm strateji ön ayarlarını listele")
async def get_presets():
    """Veritabanında kayıtlı tüm strateji ön ayarlarını döndürür."""
    try:
        return database.get_all_presets()
    except Exception as e:
        logging.error(f"Ön ayarlar alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ön ayarlar alınırken sunucu hatası oluştu.")

@router.post("/", summary="Yeni bir strateji ön ayarı kaydet", status_code=status.HTTP_201_CREATED)
async def create_preset(preset: PresetCreate):
    """Yeni bir strateji ön ayarını veritabanına kaydeder."""
    try:
        new_preset = database.add_preset(name=preset.name, settings=preset.settings)
        return new_preset
    except Exception as e:
        # Veritabanında aynı isimde kayıt varsa (UNIQUE constraint) hata dönecektir.
        logging.error(f"Ön ayar kaydedilirken hata: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Ön ayar kaydedilemedi. Muhtemelen bu isimde bir kayıt zaten var: {preset.name}")

@router.delete("/{preset_id}", summary="Bir strateji ön ayarını sil", status_code=status.HTTP_204_NO_CONTENT)
async def remove_preset(preset_id: int):
    """Belirtilen ID'ye sahip strateji ön ayarını veritabanından siler."""
    try:
        success = database.delete_preset(preset_id)
        if not success:
            raise HTTPException(status_code=404, detail="Silinecek ön ayar bulunamadı.")
    except Exception as e:
        logging.error(f"Ön ayar silinirken hata (ID: {preset_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ön ayar silinirken sunucu hatası oluştu.")
