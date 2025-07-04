# backend/database/__init__.py
# @author: Memba Co.

from .database import (
    init_db,
    get_db_connection,
    
    # Olay (Event) Fonksiyonları - YENİ
    log_event,
    get_events,
    
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
    
    # Bailout Stratejisi Fonksiyonları
    arm_bailout_for_position,
    update_extremum_price_for_position,
    set_bailout_analysis_triggered,
    reset_bailout_status,
    
    # İşlem Geçmişi Fonksiyonları
    log_trade_to_history,
    get_trade_history,

    # Strateji Ön Ayarları Fonksiyonları
    get_all_presets,
    add_preset,
    delete_preset,
    
    # Scanner Adayları Fonksiyonları
    save_scanner_candidates,
    get_all_scanner_candidates,
    update_scanner_candidate,
)