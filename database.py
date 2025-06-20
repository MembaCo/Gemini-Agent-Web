# database.py
# @author: Memba Co.

import sqlite3
import logging
from contextlib import contextmanager
from tools import calculate_pnl
import config

DB_FILE = config.DATABASE_FILE

@contextmanager
def get_db_connection():
    """Veritabanı bağlantısı oluşturur ve bir context manager olarak sunar."""
    conn = None
    try:
        # check_same_thread=False, Telegram botu gibi çoklu thread ortamları için gereklidir.
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logging.error(f"Veritabanı bağlantı hatası: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def init_db():
    """Veritabanı tablolarını (eğer yoksa) oluşturur ve şema güncellemelerini yapar."""
    try:
        with get_db_connection() as conn:
            if not conn:
                logging.error("Veritabanı başlatılamadı: Bağlantı kurulamadı.")
                return

            # Yönetilen pozisyonları tutan ana tablo
            conn.execute('''
                CREATE TABLE IF NOT EXISTS managed_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    timeframe TEXT NOT NULL,
                    leverage REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    initial_stop_loss REAL,
                    initial_amount REAL,
                    partial_tp_executed BOOLEAN DEFAULT 0,
                    realized_pnl REAL DEFAULT 0.0
                )
            ''')
            
            # Kapanan tüm işlemleri kaydeden geçmiş tablosu
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    pnl REAL NOT NULL,
                    status TEXT NOT NULL,
                    opened_at TIMESTAMP,
                    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # --- Şema Güncelleme (Migration) ---
            # Programın eski versiyonlarından geçiş yapanlar için eksik sütunları ekler.
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(managed_positions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'initial_stop_loss' not in columns:
                cursor.execute('ALTER TABLE managed_positions ADD COLUMN initial_stop_loss REAL')
            if 'initial_amount' not in columns:
                cursor.execute('ALTER TABLE managed_positions ADD COLUMN initial_amount REAL')
            if 'partial_tp_executed' not in columns:
                cursor.execute('ALTER TABLE managed_positions ADD COLUMN partial_tp_executed BOOLEAN DEFAULT 0')
            if 'realized_pnl' not in columns:
                cursor.execute('ALTER TABLE managed_positions ADD COLUMN realized_pnl REAL DEFAULT 0.0')

            conn.commit()
            logging.info("Veritabanı tabloları başarıyla kontrol edildi/oluşturuldu.")
    except Exception as e:
        logging.error(f"Veritabanı başlatılırken kritik bir hata oluştu: {e}", exc_info=True)


def add_position(pos: dict):
    """managed_positions tablosuna yeni bir pozisyon ekler."""
    sql = '''INSERT INTO managed_positions 
             (symbol, side, amount, initial_amount, entry_price, timeframe, leverage, stop_loss, take_profit, initial_stop_loss, realized_pnl) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    try:
        with get_db_connection() as conn:
            if not conn: return
            initial_amount = pos['amount']
            initial_sl = pos['stop_loss']
            conn.execute(sql, (
                pos['symbol'], pos['side'], pos['amount'], initial_amount, 
                pos['entry_price'], pos['timeframe'], pos['leverage'], 
                pos['stop_loss'], pos['take_profit'], initial_sl,
                0.0 # Yeni pozisyon için realize edilmiş PNL başlangıçta sıfırdır.
            ))
            conn.commit()
            logging.info(f"VERİTABANI: Yeni pozisyon eklendi -> {pos['symbol']}")
    except sqlite3.IntegrityError:
        logging.warning(f"VERİTABANI UYARI: {pos['symbol']} için zaten aktif bir pozisyon mevcut. Ekleme yapılmadı.")
    except Exception as e:
        logging.error(f"Pozisyon eklenirken hata: {e}", exc_info=True)


def update_position_after_partial_tp(symbol: str, new_amount: float, new_sl: float, realized_pnl: float):
    """Kısmi kâr alındıktan sonra pozisyonu günceller, durumu ve realize PNL'i işaretler."""
    sql = "UPDATE managed_positions SET amount = ?, stop_loss = ?, partial_tp_executed = 1, realized_pnl = ? WHERE symbol = ?"
    try:
        with get_db_connection() as conn:
            if not conn: return
            conn.execute(sql, (new_amount, new_sl, realized_pnl, symbol))
            conn.commit()
            logging.info(f"VERİTABANI: {symbol} için Kısmi TP sonrası pozisyon güncellendi. Toplam Realize PNL: {realized_pnl:.2f}")
    except Exception as e:
        logging.error(f"Kısmi TP sonrası veritabanı güncellenirken hata: {e}", exc_info=True)


def get_all_positions() -> list[dict]:
    """Tüm aktif pozisyonları veritabanından çeker."""
    try:
        with get_db_connection() as conn:
            if not conn: return []
            cursor = conn.execute('SELECT * FROM managed_positions')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Tüm pozisyonlar alınırken hata: {e}", exc_info=True)
        return []


def remove_position(symbol: str) -> dict | None:
    """Bir pozisyonu sembolüne göre aktif tablodan siler ve silinen pozisyonu döndürür."""
    try:
        with get_db_connection() as conn:
            if not conn: return None
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM managed_positions WHERE symbol = ?", (symbol,))
            pos_to_remove = cursor.fetchone()
            
            if pos_to_remove:
                cursor.execute("DELETE FROM managed_positions WHERE symbol = ?", (symbol,))
                conn.commit()
                logging.info(f"VERİTABANI: Pozisyon silindi -> {symbol}")
                return dict(pos_to_remove)
            return None
    except Exception as e:
        logging.error(f"Pozisyon silinirken hata: {e}", exc_info=True)
        return None


def update_position_sl(symbol: str, new_sl: float):
    """Bir pozisyonun sadece stop-loss değerini günceller."""
    sql = "UPDATE managed_positions SET stop_loss = ? WHERE symbol = ?"
    try:
        with get_db_connection() as conn:
            if not conn: return
            conn.execute(sql, (new_sl, symbol))
            conn.commit()
            logging.info(f"VERİTABANI: {symbol} için SL güncellendi -> {new_sl}")
    except Exception as e:
        logging.error(f"SL güncellenirken hata: {e}", exc_info=True)


def log_trade_to_history(closed_pos: dict, close_price: float, status: str):
    """Kapanan bir işlemi geçmiş tablosuna kaydeder."""
    sql = '''INSERT INTO trade_history 
             (symbol, side, amount, entry_price, close_price, pnl, status, opened_at) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
    try:
        with get_db_connection() as conn:
            if not conn: return
            
            # Geçmişe kaydederken, pozisyonun ORİJİNAL miktarını kullanırız.
            initial_amount = closed_pos.get('initial_amount') or closed_pos.get('amount')
            
            # Pozisyonun kalan kısmının PNL'ini hesapla
            remaining_amount_pnl = calculate_pnl(
                closed_pos.get('side', ''), 
                closed_pos.get('entry_price', 0), 
                close_price, 
                closed_pos.get('amount', 0)
            )
            
            # Varsa, kısmi kâr almadan dolayı önceden realize edilmiş PNL'i al
            previously_realized_pnl = closed_pos.get('realized_pnl', 0.0)
            
            # Toplam PNL = Önceki Kazanç (kısmi TP'den) + Son Kapanışın Kazancı
            total_pnl = previously_realized_pnl + remaining_amount_pnl

            conn.execute(sql, (
                closed_pos.get('symbol'), 
                closed_pos.get('side'), 
                initial_amount, # Geçmişe ORİJİNAL miktarı kaydet
                closed_pos.get('entry_price', 0), 
                close_price, 
                total_pnl, # Geçmişe TOPLAM PNL'i kaydet
                status, 
                closed_pos.get('created_at')
            ))
            conn.commit()
            logging.info(f"VERİTABANI: İşlem geçmişe kaydedildi -> {closed_pos.get('symbol')}, PNL: {total_pnl:.2f} USDT, Durum: {status}")
    except Exception as e:
        logging.error(f"İşlem geçmişi kaydedilirken hata: {e}", exc_info=True)
