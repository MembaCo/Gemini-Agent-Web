# backend/database/database.py
# @author: Memba Co.

import sqlite3
import logging
import json
import os

from config_defaults import default_settings

# --- DÜZELTME BAŞLANGICI: Veritabanı Yolu Sabitlendi ---
# Proje kök dizinini dinamik olarak bulur. Konteyner içindeki yol /app olacaktır.
# Bu sayede betiğin nereden çalıştırıldığından bağımsız olarak yol her zaman doğru olur.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_FILE = os.path.join(DATA_DIR, "trades.db")
# --- DÜZELTME SONU ---


def get_db_connection():
    """Veritabanı bağlantısı oluşturur ve döner."""
    # Artık DB_FILE mutlak bir yol olduğu için bağlantı her zaman doğru dosyaya yapılır.
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _initialize_settings(conn):
    logging.info("Varsayılan ayarlar veritabanı ile senkronize ediliyor...")
    cursor = conn.cursor()
    for key, value in default_settings.items():
        cursor.execute("SELECT key FROM settings WHERE key = ?", (key,))
        if cursor.fetchone() is None:
            value_type = type(value).__name__
            value_to_store = json.dumps(value) if isinstance(value, list) else str(value)
            cursor.execute("INSERT INTO settings (key, value, type) VALUES (?, ?, ?)", (key, value_to_store, value_type))
            logging.info(f"Varsayılan ayar eklendi: {key} = {value_to_store}")
    conn.commit()

def init_db():
    # DATA_DIR artık mutlak bir yol olduğu için doğru dizini oluşturacaktır.
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS managed_positions (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL UNIQUE, side TEXT NOT NULL, amount REAL NOT NULL, initial_amount REAL, entry_price REAL NOT NULL, timeframe TEXT NOT NULL, leverage REAL NOT NULL, stop_loss REAL NOT NULL, initial_stop_loss REAL, take_profit REAL NOT NULL, partial_tp_executed BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, pnl REAL DEFAULT 0, pnl_percentage REAL DEFAULT 0, reason TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, side TEXT NOT NULL, amount REAL NOT NULL, entry_price REAL NOT NULL, close_price REAL NOT NULL, pnl REAL NOT NULL, status TEXT NOT NULL, timeframe TEXT, opened_at TIMESTAMP, closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, type TEXT NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS strategy_presets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, settings TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS scanner_candidates (symbol TEXT PRIMARY KEY, source TEXT, timeframe TEXT, indicators TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        
        cursor.execute("PRAGMA table_info(managed_positions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'pnl' not in columns: cursor.execute('ALTER TABLE managed_positions ADD COLUMN pnl REAL DEFAULT 0')
        if 'pnl_percentage' not in columns: cursor.execute('ALTER TABLE managed_positions ADD COLUMN pnl_percentage REAL DEFAULT 0')
        if 'bailout_armed' not in columns: cursor.execute('ALTER TABLE managed_positions ADD COLUMN bailout_armed BOOLEAN DEFAULT 0')
        if 'extremum_price' not in columns: cursor.execute('ALTER TABLE managed_positions ADD COLUMN extremum_price REAL DEFAULT 0')
        if 'bailout_analysis_triggered' not in columns: cursor.execute('ALTER TABLE managed_positions ADD COLUMN bailout_analysis_triggered BOOLEAN DEFAULT 0')
        if 'reason' not in columns: cursor.execute('ALTER TABLE managed_positions ADD COLUMN reason TEXT')

        cursor.execute("PRAGMA table_info(trade_history)")
        history_columns = [row[1] for row in cursor.fetchall()]
        if 'timeframe' not in history_columns: cursor.execute('ALTER TABLE trade_history ADD COLUMN timeframe TEXT')

        conn.commit()
        _initialize_settings(conn)
        logging.info(f"Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu. Yol: {DB_FILE}")
    finally:
        conn.close()


def log_event(level: str, category: str, message: str):
    """Sistem olaylarını veritabanına kaydeder."""
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO events (level, category, message) VALUES (?, ?, ?)", (level.upper(), category, message))
        conn.commit()
    except Exception as e:
        logging.error(f"Olay loglanırken veritabanı hatası: {e}")
    finally:
        conn.close()

def get_events(limit: int = 50) -> list[dict]:
    """En son olayları veritabanından çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM events ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_settings() -> dict:
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT key, value, type FROM settings')
        settings = {}
        for row in cursor.fetchall():
            key, value, value_type = row
            if value_type == 'int': settings[key] = int(value)
            elif value_type == 'float': settings[key] = float(value)
            elif value_type == 'bool': settings[key] = (value.lower() == 'true')
            elif value_type == 'list': settings[key] = json.loads(value)
            else: settings[key] = value
        return {**default_settings, **settings}
    finally:
        conn.close()

def update_settings(settings: dict):
    conn = get_db_connection()
    try:
        for key, value in settings.items():
            value_type = type(value).__name__
            value_to_store = json.dumps(value) if isinstance(value, list) else str(value)
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (value_to_store, key))
        conn.commit()
        logging.info("Ayarlar veritabanında başarıyla güncellendi.")
    finally:
        conn.close()

def add_position(pos: dict):
    conn = get_db_connection()
    try:
        # YENİ: 'reason' alanı eklendi
        conn.execute('INSERT INTO managed_positions (symbol, side, amount, initial_amount, entry_price, timeframe, leverage, stop_loss, take_profit, initial_stop_loss, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                     (pos['symbol'], pos['side'], pos['amount'], pos['amount'], pos['entry_price'], pos['timeframe'], pos['leverage'], pos['stop_loss'], pos['take_profit'], pos['stop_loss'], pos.get('reason', 'N/A')))
        conn.commit()
    finally:
        conn.close()

def get_all_positions() -> list[dict]:
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM managed_positions ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_position_by_symbol(symbol: str) -> dict | None:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM managed_positions WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def remove_position(symbol: str) -> dict | None:
    conn = get_db_connection()
    try:
        pos_to_remove = get_position_by_symbol(symbol)
        if pos_to_remove:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM managed_positions WHERE symbol = ?", (symbol,))
            conn.commit()
            return pos_to_remove
        return None
    finally:
        conn.close()

def update_position_sl(symbol: str, new_sl: float):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET stop_loss = ? WHERE symbol = ?", (new_sl, symbol))
        conn.commit()
    finally:
        conn.close()
        
def update_position_after_partial_tp(symbol: str, new_amount: float, new_sl: float):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET amount = ?, stop_loss = ?, partial_tp_executed = 1 WHERE symbol = ?", (new_amount, new_sl, symbol))
        conn.commit()
    finally:
        conn.close()

def update_position_pnl(symbol: str, pnl: float, pnl_percentage: float):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET pnl = ?, pnl_percentage = ? WHERE symbol = ?", (pnl, pnl_percentage, symbol))
        conn.commit()
    except Exception as e:
        logging.error(f"PNL güncellenirken hata: {e}")
    finally:
        conn.close()

# --- İŞLEM GEÇMİŞİ FONKSİYONLARI (Değişiklik yok) ---
# ... (log_trade_to_history ve get_trade_history fonksiyonları burada) ...
def log_trade_to_history(closed_pos: dict, close_price: float, status: str):
    """Kapanan bir işlemi (zaman aralığı dahil) geçmiş tablosuna kaydeder."""
    conn = get_db_connection()
    try:
        initial_amount = closed_pos.get('initial_amount', closed_pos['amount'])
        pnl = (close_price - closed_pos['entry_price']) * initial_amount if closed_pos['side'] == 'buy' else (closed_pos['entry_price'] - close_price) * initial_amount
        
        timeframe = closed_pos.get('timeframe', 'N/A')
        
        conn.execute(
            'INSERT INTO trade_history (symbol, side, amount, entry_price, close_price, pnl, status, opened_at, timeframe) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (closed_pos['symbol'], closed_pos['side'], initial_amount, closed_pos['entry_price'], close_price, pnl, status, closed_pos['created_at'], timeframe)
        )
        conn.commit()
    finally:
        conn.close()

def get_trade_history() -> list[dict]:
    """Tüm işlem geçmişini veritabanından çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM trade_history ORDER BY closed_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

# --- STRATEJİ ÖN AYARLARI FONKSİYONLARI (Değişiklik yok) ---
# ... (get_all_presets, add_preset, delete_preset fonksiyonları burada) ...
def get_all_presets() -> list[dict]:
    """Veritabanındaki tüm strateji ön ayarlarını çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM strategy_presets ORDER BY name ASC')
        presets = []
        for row in cursor.fetchall():
            preset_dict = dict(row)
            preset_dict['settings'] = json.loads(preset_dict['settings'])
            presets.append(preset_dict)
        return presets
    finally:
        conn.close()

def add_preset(name: str, settings: dict):
    """Veritabanına yeni bir strateji ön ayarı ekler."""
    conn = get_db_connection()
    try:
        settings_json = json.dumps(settings)
        conn.execute("INSERT INTO strategy_presets (name, settings) VALUES (?, ?)", (name, settings_json))
        conn.commit()
        cursor = conn.cursor()
        cursor.execute("SELECT last_insert_rowid()")
        new_id = cursor.fetchone()[0]
        return {"id": new_id, "name": name, "settings": settings}
    finally:
        conn.close()

def delete_preset(preset_id: int):
    """Veritabanından bir strateji ön ayarını ID'sine göre siler."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM strategy_presets WHERE id = ?", (preset_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

# YENİ: SCANNER ADAYLARI İÇİN VERİTABANI FONKSİYONLARI
def save_scanner_candidates(candidates: list[dict]):
    """Mevcut adayları siler ve yenilerini veritabanına kaydeder."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scanner_candidates")
        
        if candidates:
            for candidate in candidates:
                cursor.execute(
                    """
                    INSERT INTO scanner_candidates (symbol, source, timeframe, indicators, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        candidate['symbol'],
                        candidate.get('source', 'N/A'),
                        candidate.get('timeframe', 'N/A'),
                        json.dumps(candidate.get('indicators', {}))
                    )
                )
        conn.commit()
        logging.info(f"{len(candidates)} tarama adayı veritabanına kaydedildi.")
    finally:
        conn.close()

def get_all_scanner_candidates() -> list[dict]:
    """Kaydedilmiş tüm tarayıcı adaylarını veritabanından çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM scanner_candidates ORDER BY symbol ASC')
        candidates = []
        for row in cursor.fetchall():
            candidate_dict = dict(row)
            candidate_dict['indicators'] = json.loads(candidate_dict.get('indicators', '{}'))
            candidates.append(candidate_dict)
        return candidates
    finally:
        conn.close()

def update_scanner_candidate(symbol: str, new_indicators: dict):
    """Tek bir adayın gösterge verilerini ve güncelleme zamanını günceller."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            UPDATE scanner_candidates
            SET indicators = ?, last_updated = CURRENT_TIMESTAMP
            WHERE symbol = ?
            """,
            (json.dumps(new_indicators), symbol)
        )
        conn.commit()
        logging.info(f"{symbol} adayı veritabanında güncellendi.")
    finally:
        conn.close()

# YENİ: Bailout durumunu güncellemek için fonksiyonlar
def arm_bailout_for_position(symbol: str, extremum_price: float):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET bailout_armed = 1, extremum_price = ? WHERE symbol = ?", (extremum_price, symbol))
        conn.commit()
    finally:
        conn.close()

def update_extremum_price_for_position(symbol: str, new_extremum_price: float):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET extremum_price = ? WHERE symbol = ?", (new_extremum_price, symbol))
        conn.commit()
    finally:
        conn.close()

def set_bailout_analysis_triggered(symbol: str):
    """Bir pozisyon için bailout analizinin yapıldığını işaretler."""
    conn = get_db_connection()
    try:
        # Bu fonksiyon, pozisyon kâra geçip tekrar zarara girdiğinde sıfırlanmalıdır.
        # Bu mantık position_manager'da ele alınabilir. Şimdilik sadece set ediyoruz.
        conn.execute("UPDATE managed_positions SET bailout_analysis_triggered = 1 WHERE symbol = ?", (symbol,))
        conn.commit()
    finally:
        conn.close()

# YENİ: Pozisyon kâra geçtiğinde bailout durumunu sıfırlamak için
def reset_bailout_status(symbol: str):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET bailout_armed = 0, bailout_analysis_triggered = 0, extremum_price = 0 WHERE symbol = ?", (symbol,))
        conn.commit()
    finally:
        conn.close()