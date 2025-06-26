# ==============================================================================
# File: backend/core/position_manager.py
# @author: Memba Co.
#
# --- Nihai Sürüm (v2.1) ---
# Bu sürüm, başlangıçta pozisyonları senkronize ederken borsadan gelen verideki
# sayısal alanların (leverage, entryPrice vb.) 'None' (boş) olabileceği
# durumları ele alacak şekilde daha dayanıklı hale getirilmiştir. Bu, TypeError
# hatasını önler ve pozisyonların sorunsuz içe aktarılmasını sağlar.
# ==============================================================================
import logging
import database
from core import app_config
# Gerekli importlar
from tools import (
    _fetch_price_natively, update_stop_loss_order, execute_trade_order, 
    get_open_positions_from_exchange, get_atr_value, _get_unified_symbol
)
from core.trader import close_existing_trade, TradeException
from notifications import send_telegram_message, format_partial_tp_message

def sync_positions_on_startup():
    """
    Uygulama başlangıcında çalışarak borsadaki açık pozisyonlarla yerel
    veritabanını senkronize eder. Yönetilmeyen pozisyonları içe aktarır.
    """
    logging.info(">>> Başlangıçta Pozisyon Senkronizasyonu Başlatılıyor...")
    try:
        exchange_positions_raw = get_open_positions_from_exchange()
        db_positions_raw = database.get_all_positions()

        if not exchange_positions_raw and not db_positions_raw:
            logging.info("Borsada ve veritabanında yönetilecek pozisyon bulunamadı. Senkronizasyon tamamlandı.")
            return

        # Karşılaştırma için sembol listelerini ve tam pozisyon verilerini hazırla
        exchange_positions = {p['info']['symbol'].replace('USDT', ''): p for p in exchange_positions_raw}
        db_symbols = {p['symbol'].replace('/USDT', '') for p in db_positions_raw}

        # 1. Veritabanında olan ama borsada olmayanları bul (Hayalet Pozisyonlar)
        ghost_symbols = db_symbols - set(exchange_positions.keys())
        for symbol_base in ghost_symbols:
            symbol_unified = f"{symbol_base}/USDT"
            logging.warning(f"Hayalet Pozisyon Bulundu: '{symbol_unified}' veritabanında var ama borsada yok. Veritabanından kaldırılıyor...")
            database.remove_position(symbol_unified)
            send_telegram_message(f"⚠️ **Senkronizasyon Uyarısı** ⚠️\n`{symbol_unified}` pozisyonu veritabanında bulunuyordu ancak borsada kapalıydı. Veritabanı temizlendi.")

        # 2. Borsada olan ama veritabanında olmayanları bul ve İÇE AKTAR
        unmanaged_symbols = set(exchange_positions.keys()) - db_symbols
        for symbol_base in unmanaged_symbols:
            pos_data = exchange_positions[symbol_base]
            symbol_unified = _get_unified_symbol(pos_data['info']['symbol'])
            
            try:
                # Güvenli veri dönüşümü: Değerlerin 'None' gelme ihtimaline karşı kontrol
                entry_price_raw = pos_data.get('entryPrice')
                amount_raw = pos_data.get('contracts')
                leverage_raw = pos_data.get('leverage')

                # Değer None ise, varsayılan bir değer ata; değilse float'a çevir.
                entry_price = float(entry_price_raw) if entry_price_raw is not None else 0.0
                amount = float(amount_raw) if amount_raw is not None else 0.0
                leverage = float(leverage_raw) if leverage_raw is not None else 1.0

                # Eğer temel bilgiler (giriş fiyatı veya miktar) alınamazsa bu pozisyonu atla
                if entry_price == 0.0 or amount == 0.0:
                    logging.error(f"'{symbol_unified}' pozisyonu için giriş fiyatı veya miktar alınamadı, içe aktarılamıyor.")
                    continue
                
                logging.info(f"Yönetilmeyen Pozisyon Bulundu: '{symbol_unified}'. Sisteme entegre ediliyor...")

                side = 'buy' if pos_data.get('side') == 'long' else 'sell'
                
                # Zaman aralığı bilinmediği için varsayılan bir değer kullanıyoruz
                timeframe = '15m'
                # get_atr_value.invoke() olarak değiştirildi
                atr_result = get_atr_value.invoke({"symbol_and_timeframe": f"{symbol_unified},{timeframe}"})
                if atr_result.get("status") != "success":
                    logging.error(f"'{symbol_unified}' için ATR alınamadı, içe aktarılamıyor. Mesaj: {atr_result.get('message')}")
                    continue
                
                atr_value = atr_result['value']
                sl_distance = atr_value * app_config.settings['ATR_MULTIPLIER_SL']
                tp_distance = sl_distance * app_config.settings['RISK_REWARD_RATIO_TP']
                
                stop_loss_price = entry_price - sl_distance if side == "buy" else entry_price + sl_distance
                take_profit_price = entry_price + tp_distance if side == "buy" else entry_price - tp_distance

                # Veritabanına eklenecek pozisyon objesini oluştur
                position_to_add = {
                    "symbol": symbol_unified,
                    "side": side,
                    "amount": amount,
                    "entry_price": entry_price,
                    "timeframe": timeframe,
                    "leverage": leverage,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                }
                
                database.add_position(position_to_add)
                logging.info(f"✅ BAŞARILI: '{symbol_unified}' pozisyonu içe aktarıldı ve yönetime alındı.")
                send_telegram_message(f"✅ **Pozisyon İçe Aktarıldı** ✅\n`{symbol_unified}` pozisyonu borsada açık bulunduğu için yönetime alındı.")

            except Exception as import_e:
                logging.error(f"'{symbol_unified}' pozisyonu içe aktarılırken hata: {import_e}", exc_info=True)

        total_synced = len(ghost_symbols) + len(unmanaged_symbols)
        if total_synced > 0:
            logging.info(f"<<< Pozisyon senkronizasyonu tamamlandı. {len(ghost_symbols)} hayalet pozisyon temizlendi, {len(unmanaged_symbols)} pozisyon içe aktarıldı/denendi.")
        else:
            logging.info("<<< Tüm pozisyonlar senkronize. Herhangi bir tutarsızlık bulunamadı.")

    except Exception as e:
        logging.error(f"Başlangıçta pozisyon senkronizasyonu sırasında kritik hata: {e}", exc_info=True)

async def check_all_managed_positions():
    """
    Tüm yönetilen pozisyonları periyodik olarak kontrol eder.
    PNL durumunu hesaplar ve SL/TP, Trailing SL gibi stratejileri uygular.
    """
    app_config.load_config()
    logging.info("Aktif pozisyonlar kontrol ediliyor...")
    
    active_positions = database.get_all_positions()
    
    for position in active_positions:
        try:
            await refresh_single_position_pnl(position['symbol'])
            updated_position = database.get_position_by_symbol(position['symbol'])
            if not updated_position: continue

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
        database.update_position_pnl(position['symbol'], 0, 0)
        return

    pnl, pnl_percentage = 0, 0
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
    
    if not (initial_sl and entry_price): return

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
    
    if not (initial_sl and entry_price and current_sl_price): return

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