# backend/database/database.py
# @author: Memba Co.

import sqlite3
import logging
import json
import os

# Bu dosyanın 'backend' klasöründe olması gerekir.
from config_defaults import default_settings 

# Docker konteyneri içinde kalıcı veri sağlamak için '/app/data' dizinini kullanıyoruz.
# Yerel geliştirmede ise projenin ana dizininde bir 'data' klasörü oluşturur.
DATA_DIR = "data"
DB_FILE = os.path.join(DATA_DIR, "trades.db")

def get_db_connection():
    """Veritabanı bağlantısı oluşturur ve döner."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _initialize_settings(conn):
    """
    Ayarlar tablosunu varsayılan değerlerle doldurur veya eksik ayarları tamamlar.
    Bu, yeni ayarlar eklendiğinde bile sistemin sorunsuz çalışmasını sağlar.
    """
    logging.info("Varsayılan ayarlar veritabanı ile senkronize ediliyor...")
    cursor = conn.cursor()
    
    for key, value in default_settings.items():
        cursor.execute("SELECT key FROM settings WHERE key = ?", (key,))
        if cursor.fetchone() is None:
            # Anahtar veritabanında yoksa, varsayılan değeri ekle
            value_type = type(value).__name__
            value_to_store = json.dumps(value) if isinstance(value, list) else str(value)
            cursor.execute(
                "INSERT INTO settings (key, value, type) VALUES (?, ?, ?)",
                (key, value_to_store, value_type)
            )
            logging.info(f"Varsayılan ayar eklendi: {key} = {value_to_store}")
    conn.commit()

def init_db():
    """
    Veritabanı tablolarını (eğer yoksa) oluşturur ve şema güncellemelerini yapar.
    Uygulama her başladığında çalıştırılır.
    """
    # Veritabanı dosyası oluşturulmadan önce 'data' klasörünün var olduğundan emin ol.
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # --- TABLO OLUŞTURMA ---
        cursor.execute('CREATE TABLE IF NOT EXISTS managed_positions (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL UNIQUE, side TEXT NOT NULL, amount REAL NOT NULL, initial_amount REAL, entry_price REAL NOT NULL, timeframe TEXT NOT NULL, leverage REAL NOT NULL, stop_loss REAL NOT NULL, initial_stop_loss REAL, take_profit REAL NOT NULL, partial_tp_executed BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, pnl REAL DEFAULT 0, pnl_percentage REAL DEFAULT 0)')
        cursor.execute('CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, side TEXT NOT NULL, amount REAL NOT NULL, entry_price REAL NOT NULL, close_price REAL NOT NULL, pnl REAL NOT NULL, status TEXT NOT NULL, opened_at TIMESTAMP, closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, type TEXT NOT NULL)')
        
        # --- ŞEMA GÜNCELLEMELERİ (GERİYE DÖNÜK UYUMLULUK) ---
        cursor.execute("PRAGMA table_info(managed_positions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'pnl' not in columns:
            cursor.execute('ALTER TABLE managed_positions ADD COLUMN pnl REAL DEFAULT 0')
        if 'pnl_percentage' not in columns:
            cursor.execute('ALTER TABLE managed_positions ADD COLUMN pnl_percentage REAL DEFAULT 0')

        conn.commit()

        # Ayarları her başlangıçta senkronize et
        _initialize_settings(conn)

        logging.info("Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu.")
    except Exception as e:
        logging.error(f"Veritabanı başlatılırken hata oluştu: {e}", exc_info=True)
        raise e
    finally:
        conn.close()

# --- AYAR YÖNETİMİ FONKSİYONLARI ---

def get_all_settings() -> dict:
    """Tüm ayarları veritabanından okur ve doğru tiplerde bir sözlük olarak döndürür."""
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
    """Gelen ayarlar sözlüğünü veritabanına kaydeder."""
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

# --- POZİSYON YÖNETİMİ FONKSİYONLARI ---

def add_position(pos: dict):
    """managed_positions tablosuna yeni bir pozisyon ekler."""
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO managed_positions (symbol, side, amount, initial_amount, entry_price, timeframe, leverage, stop_loss, take_profit, initial_stop_loss) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (pos['symbol'], pos['side'], pos['amount'], pos['amount'], pos['entry_price'], pos['timeframe'], pos['leverage'], pos['stop_loss'], pos['take_profit'], pos['stop_loss'])
        )
        conn.commit()
    finally:
        conn.close()

def get_all_positions() -> list[dict]:
    """Tüm aktif pozisyonları veritabanından çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM managed_positions ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_position_by_symbol(symbol: str) -> dict | None:
    """Belirtilen sembole göre tek bir aktif pozisyonu veritabanından çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM managed_positions WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def remove_position(symbol: str) -> dict | None:
    """Bir pozisyonu sembolüne göre aktif tablodan siler ve silinen pozisyonu döndürür."""
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
    """Bir pozisyonun sadece stop-loss değerini günceller."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET stop_loss = ? WHERE symbol = ?", (new_sl, symbol))
        conn.commit()
    finally:
        conn.close()
        
def update_position_after_partial_tp(symbol: str, new_amount: float, new_sl: float):
    """Kısmi kâr alındıktan sonra pozisyonu günceller ve durumu işaretler."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET amount = ?, stop_loss = ?, partial_tp_executed = 1 WHERE symbol = ?", (new_amount, new_sl, symbol))
        conn.commit()
    finally:
        conn.close()

def update_position_pnl(symbol: str, pnl: float, pnl_percentage: float):
    """Bir pozisyonun PNL değerlerini günceller."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE managed_positions SET pnl = ?, pnl_percentage = ? WHERE symbol = ?", (pnl, pnl_percentage, symbol))
        conn.commit()
    except Exception as e:
        logging.error(f"PNL güncellenirken hata: {e}")
    finally:
        conn.close()

# --- İŞLEM GEÇMİŞİ FONKSİYONLARI ---

def log_trade_to_history(closed_pos: dict, close_price: float, status: str):
    """Kapanan bir işlemi geçmiş tablosuna kaydeder."""
    conn = get_db_connection()
    try:
        initial_amount = closed_pos.get('initial_amount', closed_pos['amount'])
        pnl = (close_price - closed_pos['entry_price']) * initial_amount if closed_pos['side'] == 'buy' else (closed_pos['entry_price'] - close_price) * initial_amount
        conn.execute('INSERT INTO trade_history (symbol, side, amount, entry_price, close_price, pnl, status, opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (closed_pos['symbol'], closed_pos['side'], initial_amount, closed_pos['entry_price'], close_price, pnl, status, closed_pos['created_at']))
        conn.commit()
    finally:
        conn.close()

def get_trade_history() -> list[dict]:
    """Tüm işlem geçmişini veritabanından çeker."""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT * FROM trade_history ORDER BY closed_at ASC')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
