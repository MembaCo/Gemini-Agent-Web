# core/position_manager.py
# @author: Memba Co.

import logging
import database
from core import app_config
from tools import _fetch_price_natively, update_stop_loss_order, execute_trade_order
from core.trader import close_existing_trade, TradeException
from notifications import send_telegram_message, format_partial_tp_message

async def check_all_managed_positions():
    """
    Tüm yönetilen pozisyonları periyodik olarak kontrol eder.
    Her döngünün başında en güncel ayarları veritabanından okur.
    PNL durumunu hesaplar ve veritabanını günceller.
    """
    app_config.load_config()
    logging.info("Aktif pozisyonlar kontrol ediliyor...")
    
    active_positions = database.get_all_positions()
    
    for position in active_positions:
        try:
            # Önce PNL'i yenileyelim
            await refresh_single_position_pnl(position['symbol'])
            
            # SL/TP kontrolü için pozisyonun en güncel halini tekrar veritabanından okuyoruz.
            updated_position = database.get_position_by_symbol(position['symbol'])
            if not updated_position:
                continue

            current_price = _fetch_price_natively(updated_position["symbol"])
            if current_price is None:
                logging.warning(f"Fiyat alınamadığı için {updated_position['symbol']} pozisyonu kontrol edilemedi.")
                continue

            side = updated_position.get("side")
            sl_price = updated_position.get("stop_loss", 0.0)
            tp_price = updated_position.get("take_profit", 0.0)
            
            close_reason = None
            if sl_price > 0 and ((side == "buy" and current_price <= sl_price) or (side == "sell" and current_price >= sl_price)):
                close_reason = "SL"
            elif tp_price > 0 and ((side == "buy" and current_price >= tp_price) or (side == "sell" and current_price <= tp_price)):
                close_reason = "TP"
            
            if close_reason:
                logging.info(f"[AUTO-CLOSE] Pozisyon hedefe ulaştı ({close_reason}): {updated_position['symbol']} @ {current_price}")
                close_existing_trade(updated_position['symbol'], close_reason=close_reason)
                continue

            if app_config.settings.get('USE_PARTIAL_TP') and not updated_position.get('partial_tp_executed'):
                handle_partial_tp(updated_position, current_price)

            if app_config.settings.get('USE_TRAILING_STOP_LOSS'):
                handle_trailing_stop_loss(updated_position, current_price)

        except TradeException as te:
            logging.error(f"Pozisyon yönetimi sırasında bilinen hata ({position['symbol']}): {te}")
        except Exception as e:
            logging.error(f"Pozisyon yönetimi sırasında beklenmedik hata ({position['symbol']}): {e}", exc_info=True)

async def refresh_single_position_pnl(symbol: str):
    """Tek bir pozisyonun PNL'ini hesaplar ve veritabanını günceller."""
    position = database.get_position_by_symbol(symbol)
    if not position:
        logging.warning(f"PNL yenileme: {symbol} pozisyonu bulunamadı.")
        return

    current_price = _fetch_price_natively(position["symbol"])
    if current_price is None:
        logging.warning(f"PNL yenileme için fiyat alınamadı: {symbol}")
        # Fiyat alınamazsa PNL'i sıfır olarak işaretle
        database.update_position_pnl(position['symbol'], 0, 0)
        return

    pnl = 0
    pnl_percentage = 0
    entry_price = position.get('entry_price', 0)
    amount = position.get('amount', 0)
    leverage = position.get('leverage', 1)
    
    if entry_price > 0 and amount > 0:
        pnl = (current_price - entry_price) * amount if position['side'] == 'buy' else (entry_price - current_price) * amount
        margin = (entry_price * amount) / leverage if leverage > 0 else 0
        pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
    
    database.update_position_pnl(position['symbol'], pnl, pnl_percentage)
    logging.info(f"PNL güncellendi: {symbol} -> {pnl:.2f} USDT")

def handle_partial_tp(position: dict, current_price: float):
    """Kısmi kâr alma mantığını yönetir."""
    initial_sl = position.get('initial_stop_loss')
    entry_price = position.get('entry_price')
    side = position.get("side")
    
    if not (initial_sl and entry_price):
        return

    risk_distance = abs(entry_price - initial_sl)
    partial_tp_price = entry_price + (risk_distance * app_config.settings['PARTIAL_TP_TARGET_RR']) if side == 'buy' else entry_price - (risk_distance * app_config.settings['PARTIAL_TP_TARGET_RR'])

    if (side == 'buy' and current_price >= partial_tp_price) or (side == 'sell' and current_price <= partial_tp_price):
        logging.info(f"[PARTIAL-TP] {position['symbol']} için kısmi kâr alma hedefi {partial_tp_price:.4f} ulaşıldı.")
        
        initial_amount = position.get('initial_amount') or position.get('amount')
        amount_to_close = initial_amount * (app_config.settings['PARTIAL_TP_CLOSE_PERCENT'] / 100)
        remaining_amount = position['amount'] - amount_to_close
        
        if remaining_amount > 0:
            result = execute_trade_order(symbol=position['symbol'], side='sell' if side == 'buy' else 'buy', amount=amount_to_close)
            
            if result.get("status") == "success":
                logging.info(f"Kısmi kâr alma başarılı: {amount_to_close:.4f} {position['symbol']} kapatıldı.")
                new_sl_price = entry_price
                update_stop_loss_order(symbol=position['symbol'], side=side, amount=remaining_amount, new_stop_price=new_sl_price)
                database.update_position_after_partial_tp(position['symbol'], remaining_amount, new_sl_price)
                send_telegram_message(format_partial_tp_message(position['symbol'], amount_to_close, remaining_amount, entry_price))
            else:
                logging.error(f"Kısmi kâr alma sırasında pozisyon kapatılamadı: {result.get('message')}")

def handle_trailing_stop_loss(position: dict, current_price: float):
    """İz süren zarar durdurma mantığını yönetir."""
    entry_price = position.get("entry_price", 0.0)
    initial_sl = position.get('initial_stop_loss')
    current_sl_price = position.get("stop_loss", 0.0)
    side = position.get("side")
    
    if not (initial_sl and entry_price and current_sl_price):
        return

    profit_perc = ((current_price - entry_price) / entry_price) * 100 * (1 if side == 'buy' else -1)
    
    if profit_perc > app_config.settings['TRAILING_STOP_ACTIVATION_PERCENT']:
        original_sl_distance = abs(entry_price - initial_sl)
        new_sl = 0.0
        
        if side == 'buy' and (new_sl_candidate := current_price - original_sl_distance) > current_sl_price:
            new_sl = new_sl_candidate
        elif side == 'sell' and (new_sl_candidate := current_price + original_sl_distance) < current_sl_price:
            new_sl = new_sl_candidate

        if new_sl > 0:
            logging.info(f"[TRAIL-SL] {position['symbol']} için yeni SL tetiklendi: {current_sl_price:.4f} -> {new_sl:.4f}")
            result = update_stop_loss_order(symbol=position['symbol'], side=side, amount=position['amount'], new_stop_price=new_sl)
            if "Başarılı" in result or "Simülasyon" in result:
                database.update_position_sl(position['symbol'], new_sl)
