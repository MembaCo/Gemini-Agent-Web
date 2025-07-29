# backend/core/trader.py
# @author: Memba Co.

import logging
import database
from core import app_config
from tools import (
    execute_trade_order, get_atr_value, get_wallet_balance,
    cancel_all_open_orders
)
from notifications import send_telegram_message, format_open_position_message, format_close_position_message

class TradeException(Exception):
    pass

def open_new_trade(symbol: str, recommendation: str, timeframe: str, current_price: float, reason: str = "N/A"):
    logging.info(f"Ticaret mantığı başlatıldı: {symbol} için yeni pozisyon açılıyor.")

    if database.get_position_by_symbol(symbol):
        raise TradeException(f"'{symbol}' için zaten açık bir pozisyon mevcut. Yeni pozisyon açılamaz.")

    is_live = app_config.settings.get('LIVE_TRADING', False)
    if is_live and len(database.get_all_positions()) >= app_config.settings['MAX_CONCURRENT_TRADES']:
        raise TradeException("Maksimum eşzamanlı pozisyon limitine ulaşıldı.")

    trade_side = "buy" if "AL" in recommendation else "sell"
    
    # ATR periyodunu dinamik risk ayarından veya varsayılan SL/TP ayarından al
    atr_period = app_config.settings.get('DYNAMIC_RISK_ATR_PERIOD', 14) if app_config.settings.get('USE_DYNAMIC_RISK') else 14
    atr_result = get_atr_value(symbol, timeframe) # timeframe parametresini düzelt
    if atr_result.get("status") != "success":
        raise TradeException(f"ATR değeri alınamadı: {atr_result.get('message')}")
    
    atr_value = atr_result['value']

    # --- YENİ: DİNAMİK RİSK HESAPLAMA MANTIĞI ---
    risk_per_trade_percent = app_config.settings['RISK_PER_TRADE_PERCENT']

    if app_config.settings.get('USE_DYNAMIC_RISK'):
        volatility_percentage = (atr_value / current_price) * 100
        base_risk = app_config.settings.get('DYNAMIC_RISK_BASE_RISK', 1.5)
        low_thresh = app_config.settings.get('DYNAMIC_RISK_LOW_VOL_THRESHOLD', 1.5)
        high_thresh = app_config.settings.get('DYNAMIC_RISK_HIGH_VOL_THRESHOLD', 4.0)
        low_multi = app_config.settings.get('DYNAMIC_RISK_LOW_VOL_MULTIPLIER', 1.5)
        high_multi = app_config.settings.get('DYNAMIC_RISK_HIGH_VOL_MULTIPLIER', 0.75)
        
        dynamic_risk_per_trade = base_risk
        if volatility_percentage < low_thresh:
            dynamic_risk_per_trade *= low_multi
            logging.info(f"Dinamik Risk: Düşük volatilite tespit edildi ({volatility_percentage:.2f}% < {low_thresh}%), risk artırıldı: {dynamic_risk_per_trade:.2f}%")
        elif volatility_percentage > high_thresh:
            dynamic_risk_per_trade *= high_multi
            logging.info(f"Dinamik Risk: Yüksek volatilite tespit edildi ({volatility_percentage:.2f}% > {high_thresh}%), risk azaltıldı: {dynamic_risk_per_trade:.2f}%")
        else:
            logging.info(f"Dinamik Risk: Ortalama volatilite tespit edildi ({volatility_percentage:.2f}%), temel risk kullanılıyor: {dynamic_risk_per_trade:.2f}%")
        
        risk_per_trade_percent = dynamic_risk_per_trade
    # --- DİNAMİK RİSK HESAPLAMA SONU ---

    wallet_balance = 0.0
    if is_live:
        balance_result = get_wallet_balance()
        if balance_result.get("status") != "success":
            raise TradeException(f"Cüzdan bakiyesi alınamadı: {balance_result.get('message')}")
        wallet_balance = balance_result.get('balance', 0.0)
    else:
        wallet_balance = app_config.settings.get('VIRTUAL_BALANCE', 10000.0)
        logging.info(f"Simülasyon Modu: Sanal bakiye ({wallet_balance} USDT) kullanılıyor.")
    
    sl_distance = atr_value * app_config.settings['ATR_MULTIPLIER_SL']
    stop_loss_price = current_price - sl_distance if trade_side == "buy" else current_price + sl_distance
    risk_amount_usd = wallet_balance * (risk_per_trade_percent / 100) # Değişkeni burada kullan
    sl_price_diff = abs(current_price - stop_loss_price)

    if sl_price_diff <= 1e-9:
        raise TradeException("Geçersiz stop-loss mesafesi hesaplandı (fark ~ 0).")

    trade_amount = risk_amount_usd / sl_price_diff

    if is_live:
        notional_value = trade_amount * current_price
        required_margin = notional_value / app_config.settings['LEVERAGE']
        logging.info(f"Dinamik Pozisyon Hesabı: Bakiye={wallet_balance:.2f} USDT, Risk={risk_amount_usd:.2f} USDT (Risk %{risk_per_trade_percent:.2f}), Pozisyon Büyüklüğü={notional_value:.2f} USDT, Gerekli Marjin={required_margin:.2f} USDT")
        if required_margin > wallet_balance:
            raise TradeException(f"Gerekli marjin ({required_margin:.2f} USDT) mevcut bakiyeden ({wallet_balance:.2f} USDT) fazla.")

    tp_distance = sl_distance * app_config.settings['RISK_REWARD_RATIO_TP']
    take_profit_price = current_price + tp_distance if trade_side == "buy" else current_price - tp_distance

    position_to_open = {
        "symbol": symbol, "side": trade_side, "amount": trade_amount,
        "stop_loss": stop_loss_price, "take_profit": take_profit_price, "leverage": app_config.settings['LEVERAGE'],
        "price": current_price if app_config.settings['DEFAULT_ORDER_TYPE'] == 'LIMIT' else None
    }

    result = execute_trade_order(**position_to_open)

    if result.get("status") == "success":
        final_entry_price = result.get('fill_price', current_price)
        managed_position_details = {
            "symbol": symbol, "side": trade_side, "amount": trade_amount,
            "entry_price": final_entry_price,
            "timeframe": timeframe, "leverage": app_config.settings['LEVERAGE'],
            "stop_loss": stop_loss_price, "take_profit": take_profit_price,
            "reason": reason
        }
        database.add_position(managed_position_details)
        log_message = f"Yeni pozisyon açıldı: {trade_side.upper()} {symbol} @ {final_entry_price:.4f}"
        if not is_live:
            log_message = "[SİMÜLASYON] " + log_message
        database.log_event("SUCCESS", "Trade", log_message)
        message = format_open_position_message(managed_position_details, is_simulation=not is_live)
        send_telegram_message(message)
        logging.info(f"Pozisyon başarıyla açıldı ve kaydedildi: {symbol} @ {final_entry_price}")
        return {"status": "success", "message": "Pozisyon başarıyla açıldı.", "details": managed_position_details}
    else:
        error_msg = f"Borsada işlem emri gönderimi başarısız oldu: {result.get('message')}"
        database.log_event("ERROR", "Trade", f"{symbol} için pozisyon açma denemesi başarısız. Hata: {result.get('message')}")
        raise TradeException(error_msg)


# ... (close_existing_trade fonksiyonu aynı kalabilir) ...
def close_existing_trade(symbol: str, close_reason: str = "MANUAL"):
    is_live = app_config.settings.get('LIVE_TRADING', False)
    log_prefix = "" if is_live else "[SİMÜLASYON] "
    logging.info(f"{log_prefix}Ticaret mantığı başlatıldı: {symbol} pozisyonu '{close_reason}' nedeniyle kapatılıyor.")
    
    position_to_close = database.get_position_by_symbol(symbol) 
    if not position_to_close:
        raise TradeException(f"Veritabanında yönetilen '{symbol}' pozisyonu bulunamadı.")
    
    if is_live:
        cancel_all_open_orders(symbol)
    
    close_side = 'sell' if position_to_close['side'] == 'buy' else 'buy'
    
    result = execute_trade_order(
        symbol=symbol, 
        side=close_side, 
        amount=position_to_close['amount'],
        is_closing_order=True
    )
    
    if result.get("status") == "success":
        closed_pos = database.remove_position(symbol)
        if closed_pos:
            close_price = result.get('fill_price')
            
            if close_price is None:
                logging.warning(f"{log_prefix}{symbol} için kapanış fiyatı alınamadı, PNL hesaplanamıyor.")
                pnl = 0
            else:
                 pnl = (close_price - closed_pos['entry_price']) * closed_pos.get('initial_amount', closed_pos['amount']) if closed_pos['side'] == 'buy' else (closed_pos['entry_price'] - close_price) * closed_pos.get('initial_amount', closed_pos['amount'])

            log_pos = {**closed_pos, 'close_price': close_price or 0}
            database.log_trade_to_history(closed_pos, close_price or 0, close_reason)
            database.log_event("INFO", "Trade", f"{log_prefix}Pozisyon kapatıldı: {symbol}. Sebep: {close_reason}. PNL: {pnl:+.2f} USDT")
            
            message = format_close_position_message(log_pos, pnl, close_reason, is_simulation=not is_live)
            send_telegram_message(message)
            
            logging.info(f"{log_prefix}Pozisyon başarıyla kapatıldı ve geçmişe kaydedildi: {symbol} @ {close_price}")
            return {"status": "success", "message": f"Pozisyon '{symbol}' başarıyla kapatıldı."}
        else:
            raise TradeException(f"Pozisyon borsada kapatıldı ancak veritabanından silinemedi: {symbol}")
    else:
        error_msg = f"Pozisyon kapatılamadı. Borsa yanıtı: {result.get('message')}"
        database.log_event("ERROR", "Trade", f"{symbol} pozisyonu kapatılamadı. Hata: {result.get('message')}")
        raise TradeException(error_msg)