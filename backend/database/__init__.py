# backend/database/__init__.py
# @author: Memba Co.

# Bu dosya, 'database' klasörünün bir Python paketi olarak tanınmasını sağlar
# ve .database modülündeki (database.py) tüm fonksiyonları dışa aktarır.

from .database import (
    init_db,
    get_db_connection,
    
    # Ayar Fonksiyonları
    get_all_settings,
    update_settings,
    
    # Pozisyon Fonksiyonları
    add_position,
    get_all_positions,
    get_position_by_symbol,
    remove_position,
    update_position_sl,
    update_position_after_partial_tp,
    update_position_pnl,
    
    # İşlem Geçmişi Fonksiyonları
    log_trade_to_history,
    get_trade_history,

    # === YENİ KOD BAŞLANGICI: Strateji Ön Ayarları Fonksiyonları ===
    get_all_presets,
    add_preset,
    delete_preset,
    # === YENİ KOD SONU ===
)
