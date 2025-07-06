# backend/core/position_manager.py
# @author: Memba Co.

import logging
import asyncio
import time # Tenacity için eklendi
import database
from core import app_config
from tools import (
    get_price_with_cache, update_stop_loss_order, execute_trade_order, 
    get_open_positions_from_exchange, get_atr_value, _get_unified_symbol,
    fetch_open_orders, cancel_all_open_orders
)
from tools import exchange as exchange_tools
from core.trader import close_existing_trade, TradeException
from notifications import send_telegram_message, format_partial_tp_message
from tenacity import retry, stop_after_attempt, wait_fixed

from core import agent
from tools import get_technical_indicators


def _ensure_exchange_is_available():
    """Yardımcı fonksiyon: Borsa bağlantısının varlığını kontrol eder."""
    if not exchange_tools.exchange:
        logging.warning("İşlem yapılamadı: Borsa bağlantısı (exchange) mevcut değil.")
        return False
    return True

# --- YENİ: Tekrarlı deneme mantığı eklendi ---
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
async def _get_positions_with_retry():
    """Borsadan pozisyonları 3 kez deneme ile çeker."""
    logging.info("Borsadan açık pozisyonlar çekiliyor (deneniyor)...")
    return await asyncio.to_thread(get_open_positions_from_exchange)

async def sync_positions_with_exchange():
    """
    Uygulama başlangıcında ve periyodik olarak çalışarak borsadaki açık pozisyonlarla yerel
    veritabanını senkronize eder. Hatalara karşı daha dayanıklı hale getirildi.
    """
    def _blocking_sync():
        if not _ensure_exchange_is_available():
            logging.error("Periyodik senkronizasyon atlanıyor: Borsa bağlantısı yok.")
            return
        
        logging.info(">>> Pozisyon Senkronizasyonu Başlatılıyor...")
        try:
            # DÜZELTME: Pozisyonları anlık ağ hatalarına karşı 3 kez deneyerek al
            exchange_positions_raw = asyncio.run(_get_positions_with_retry())
            
            db_positions = database.get_all_positions()
            exchange_positions_map = {_get_unified_symbol(p['symbol']): p for p in exchange_positions_raw}
            db_symbols_set = {p['symbol'] for p in db_positions}

            # Veritabanında var, borsada yok (Hayalet Pozisyon)
            ghost_symbols = db_symbols_set - set(exchange_positions_map.keys())
            for symbol in ghost_symbols:
                # DÜZELTME: Bu logu daha kritik bir seviyeye taşıdık
                logging.critical(f"KRİTİK SENKRONİZASYON SORUNU: '{symbol}' pozisyonu veritabanında var ama borsada yok. Pozisyon veritabanından temizleniyor. Lütfen durumu manuel kontrol edin.")
                database.remove_position(symbol)
                database.log_event("CRITICAL", "Sync", f"Hayalet pozisyon bulundu ve silindi: '{symbol}' veritabanında vardı ama borsada yoktu. Bu durum, anlık API hatasından kaynaklanmış olabilir.")
                send_telegram_message(f"‼️ **Kritik Senkronizasyon Sorunu** ‼️\n`{symbol}` pozisyonu veritabanında bulunuyordu ancak borsada kapalı görünüyordu. Veritabanı temizlendi, lütfen borsadaki pozisyonlarınızı manuel olarak kontrol edin.")

            # Borsada var, veritabanında yok (Yönetilmeyen Pozisyon)
            unmanaged_symbols = set(exchange_positions_map.keys()) - db_symbols_set
            for symbol_unified in unmanaged_symbols:
                pos_data = exchange_positions_map[symbol_unified]
                try:
                    entry_price_raw = pos_data.get('entryPrice')
                    amount_raw = pos_data.get('contracts')
                    leverage_raw = pos_data.get('leverage')
                    entry_price = float(entry_price_raw) if entry_price_raw is not None else 0.0
                    amount = float(amount_raw) if amount_raw is not None else 0.0
                    leverage = float(leverage_raw) if leverage_raw is not None else 1.0

                    if entry_price == 0.0 or amount == 0.0:
                        logging.error(f"'{symbol_unified}' pozisyonu için giriş fiyatı veya miktar alınamadı, içe aktarılamıyor.")
                        continue
                    
                    logging.info(f"Yönetilmeyen Pozisyon Bulundu: '{symbol_unified}'. Sisteme entegre ediliyor...")
                    side = 'buy' if pos_data.get('side') == 'long' else 'sell'
                    timeframe = '15m' # Varsayılan olarak
                    atr_result = get_atr_value(f"{symbol_unified},{timeframe}")
                    if atr_result.get("status") != "success":
                        logging.error(f"'{symbol_unified}' için ATR alınamadı, içe aktarılamıyor. Mesaj: {atr_result.get('message')}")
                        continue
                    
                    atr_value = atr_result['value']
                    sl_distance = atr_value * app_config.settings['ATR_MULTIPLIER_SL']
                    tp_distance = sl_distance * app_config.settings['RISK_REWARD_RATIO_TP']
                    stop_loss_price = entry_price - sl_distance if side == "buy" else entry_price + sl_distance
                    take_profit_price = entry_price + tp_distance if side == "buy" else entry_price - tp_distance

                    position_to_add = {"symbol": symbol_unified, "side": side, "amount": amount, "entry_price": entry_price, "timeframe": timeframe, "leverage": leverage, "stop_loss": stop_loss_price, "take_profit": take_profit_price}
                    database.add_position(position_to_add)
                    database.log_event("INFO", "Sync", f"Yönetilmeyen pozisyon '{symbol_unified}' sisteme aktarıldı.")
                    logging.info(f"✅ BAŞARILI: '{symbol_unified}' pozisyonu içe aktarıldı ve yönetime alındı.")
                    send_telegram_message(f"✅ **Pozisyon İçe Aktarıldı** ✅\n`{symbol_unified}` pozisyonu borsada açık bulunduğu için yönetime alındı.")
                except Exception as import_e:
                    logging.error(f"'{symbol_unified}' pozisyonu içe aktarılırken hata: {import_e}", exc_info=True)

            if not ghost_symbols and not unmanaged_symbols:
                logging.info("<<< Pozisyonlar senkronize. Herhangi bir tutarsızlık bulunamadı.")
            
        except Exception as e:
            logging.error(f"Pozisyon senkronizasyonu sırasında kritik hata: {e}", exc_info=True)

    await asyncio.to_thread(_blocking_sync)

def handle_bailout_exit(position: dict, current_price: float, pnl_percentage: float):
    """Yapay Zeka Onaylı Akıllı Zarar Azaltma (Bailout Exit) stratejisini yönetir."""
    side = position.get("side")
    bailout_armed = position.get('bailout_armed', False)
    bailout_analysis_triggered = position.get('bailout_analysis_triggered', False)
    extremum_price = position.get('extremum_price', 0)
    
    # Eğer pozisyon kâra geçtiyse, bailout durumunu sıfırla
    if pnl_percentage > 0 and bailout_armed:
        database.reset_bailout_status(position['symbol'])
        return False

    # 1. Stratejiyi Devreye Sokma (Arming)
    if not bailout_armed and pnl_percentage < app_config.settings.get('BAILOUT_ARM_LOSS_PERCENT', -2.0):
        database.arm_bailout_for_position(position['symbol'], current_price)
        log_msg = f"BAILOUT ARMED: {position['symbol']} pozisyonu {pnl_percentage:.2f}% zararda. Kurtarma çıkışı için bekleniyor."
        logging.info(log_msg)
        database.log_event("INFO", "Strategy", log_msg)
        return False

    # 2. Devrede olan stratejiyi izleme
    if bailout_armed:
        if (side == 'buy' and current_price < extremum_price) or \
           (side == 'sell' and current_price > extremum_price):
            database.update_extremum_price_for_position(position['symbol'], current_price)
            extremum_price = current_price

        recovery_perc = app_config.settings.get('BAILOUT_RECOVERY_PERCENT', 1.0) / 100.0
        recovery_target_price = extremum_price * (1 + recovery_perc) if side == 'buy' else extremum_price * (1 - recovery_perc)
        
        recovery_triggered = (side == 'buy' and current_price >= recovery_target_price) or \
                             (side == 'sell' and current_price <= recovery_target_price)

        # 3. AI Onayını Tetikleme
        if recovery_triggered and not bailout_analysis_triggered:
            # AI'a sormadan önce analiz yapıldığını veritabanına işle
            database.set_bailout_analysis_triggered(position['symbol'])

            # AI onayı istenmiyorsa, direkt kapat
            if not app_config.settings.get('USE_AI_BAILOUT_CONFIRMATION', True):
                log_msg = f"BAILOUT TRIGGERED (No AI): {position['symbol']} pozisyonu dipten toparlandı. Direkt kapatılıyor."
                logging.info(log_msg)
                database.log_event("SUCCESS", "Strategy", log_msg)
                close_existing_trade(position['symbol'], close_reason="BAILOUT_EXIT")
                return True

            # AI onayı isteniyorsa, analiz yap
            try:
                logging.info(f"AI BAILOUT CONFIRMATION: {position['symbol']} için AI onayı isteniyor...")
                indicators = get_technical_indicators(f"{position['symbol']},{position['timeframe']}")
                if indicators.get('status') != 'success':
                    logging.warning(f"Bailout AI onayı için {position['symbol']} indikatörleri alınamadı.")
                    return False
                
                prompt = agent.create_bailout_reanalysis_prompt(position, current_price, pnl_percentage, indicators['data'])
                result = agent.llm_invoke_with_fallback(prompt)
                parsed_data = agent.parse_agent_response(result.content)

                if parsed_data and parsed_data.get('recommendation') == 'KAPAT':
                    log_msg = f"AI CONFIRMED BAILOUT: AI, {position['symbol']} pozisyonunun kapatılmasını onayladı. Gerekçe: {parsed_data.get('reason')}"
                    logging.info(log_msg)
                    database.log_event("SUCCESS", "Strategy", log_msg)
                    close_existing_trade(position['symbol'], close_reason="AI_BAILOUT_EXIT")
                    return True
                else:
                    log_msg = f"AI REJECTED BAILOUT: AI, {position['symbol']} pozisyonunun TUTULMASINI tavsiye etti. Gerekçe: {parsed_data.get('reason', 'N/A')}"
                    logging.info(log_msg)
                    database.log_event("INFO", "Strategy", log_msg)

            except Exception as e:
                logging.error(f"Bailout AI onayı sırasında hata ({position['symbol']}): {e}", exc_info=True)

    return False

async def check_all_managed_positions():
    """
    Tüm yönetilen pozisyonları periyodik olarak kontrol eder. Bloklamayı önlemek için
    ana mantık bir thread içinde çalıştırılır.
    """
    def _blocking_check():
        if not _ensure_exchange_is_available(): return

        app_config.load_config()
        logging.info("Aktif pozisyonlar kontrol ediliyor...")
        active_positions = database.get_all_positions()
        
        for position in active_positions:
            try:
                current_price = get_price_with_cache(position["symbol"])
                if current_price is None:
                    logging.warning(f"Fiyat alınamadığı için {position['symbol']} pozisyonu kontrol edilemedi.")
                    continue

                # PNL hesaplaması ve veritabanı güncellemesi
                pnl, pnl_percentage = 0, 0
                entry_price = position.get('entry_price', 0); amount = position.get('amount', 0); leverage = position.get('leverage', 1)
                if entry_price > 0 and amount > 0:
                    pnl = (current_price - entry_price) * amount if position['side'] == 'buy' else (entry_price - current_price) * amount
                    margin = (entry_price * amount) / leverage if leverage > 0 else 0
                    pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
                database.update_position_pnl(position['symbol'], pnl, pnl_percentage)
                
                # SL/TP kontrolü
                side = position.get("side"); sl_price = position.get("stop_loss", 0.0); tp_price = position.get("take_profit", 0.0)
                close_reason = None
                if sl_price > 0 and ((side == "buy" and current_price <= sl_price) or (side == "sell" and current_price >= sl_price)): close_reason = "SL"
                elif tp_price > 0 and ((side == "buy" and current_price >= tp_price) or (side == "sell" and current_price <= tp_price)): close_reason = "TP"
                
                if close_reason:
                    logging.info(f"[AUTO-CLOSE] Pozisyon hedefe ulaştı ({close_reason}): {position['symbol']} @ {current_price}")
                    close_existing_trade(position['symbol'], close_reason=close_reason)
                    continue

                # Gelişmiş stratejiler
                if app_config.settings.get('USE_BAILOUT_EXIT'):
                    if handle_bailout_exit(dict(position), current_price, pnl_percentage):
                        continue
                if app_config.settings.get('USE_PARTIAL_TP') and not position.get('partial_tp_executed'):
                    handle_partial_tp(position, current_price)
                if app_config.settings.get('USE_TRAILING_STOP_LOSS'):
                    handle_trailing_stop_loss(position, current_price)
            except TradeException as te:
                logging.error(f"Pozisyon yönetimi sırasında bilinen hata ({position['symbol']}): {te}")
            except Exception as e:
                logging.error(f"Pozisyon yönetimi sırasında beklenmedik hata ({position['symbol']}): {e}", exc_info=True)

    await asyncio.to_thread(_blocking_check)

async def check_for_orphaned_orders():
    """
    Borsadaki açık emirleri kontrol eder ve pozisyonu olmayanları iptal eder.
    Bloklamayı önlemek için ana mantık bir thread içinde çalıştırılır.
    """
    def _blocking_check():
        if not _ensure_exchange_is_available(): return
        if not app_config.settings.get('LIVE_TRADING') or exchange_tools.exchange.options.get('defaultType') != 'future':
            return

        logging.info("Yetim Emir Kontrolü (Orphan Order Check) başlatılıyor...")
        try:
            open_orders = fetch_open_orders()
            if not open_orders:
                logging.info("Yetim Emir Kontrolü: Kontrol edilecek açık emir bulunamadı.")
                return

            exchange_positions = get_open_positions_from_exchange()
            active_position_symbols = {_get_unified_symbol(p['symbol']) for p in exchange_positions}
            orphaned_orders_found = 0
            for order in open_orders:
                order_symbol = _get_unified_symbol(order['symbol'])
                if order_symbol not in active_position_symbols:
                    logging.warning(f"Yetim Emir Tespit Edildi: {order_symbol} sembolünde pozisyon kapalı ama {order['id']} ID'li emir açık. Emir iptal ediliyor.")
                    try:
                        exchange_tools.exchange.cancel_order(order['id'], order['symbol'])
                        database.log_event("INFO", "Sync", f"Yetim emir temizlendi: {order_symbol} pozisyonu kapalı olmasına rağmen açık bir emir bulundu ve iptal edildi.")
                        send_telegram_message(f"🧹 **Otomatik Temizlik** 🧹\n`{order_symbol}` için pozisyon kapalı olmasına rağmen açık `{order['type']}` emri bulundu ve iptal edildi.")
                        orphaned_orders_found += 1
                    except Exception as e:
                        logging.error(f"Yetim emir {order['id']} ({order_symbol}) iptal edilirken hata: {e}")
            
            if orphaned_orders_found > 0:
                logging.info(f"Yetim Emir Kontrolü tamamlandı. {orphaned_orders_found} adet yetim emir temizlendi.")
            else:
                 logging.info("Yetim Emir Kontrolü tamamlandı. Herhangi bir yetim emir bulunamadı.")
        except Exception as e:
            logging.error(f"Yetim emir kontrolü sırasında kritik hata: {e}", exc_info=True)

    await asyncio.to_thread(_blocking_check)


async def refresh_single_position_pnl(symbol: str):
    # Bu fonksiyon genellikle UI'dan tetiklenir ve zaten asenkron bir endpoint içindedir.
    # Bu nedenle _blocking_check gibi bir patterne şu an için gerek yoktur.
    if not _ensure_exchange_is_available(): return
    position = database.get_position_by_symbol(symbol)
    if not position: return
    current_price = get_price_with_cache(position["symbol"])
    if current_price is None:
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


def handle_partial_tp(position: dict, current_price: float):
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
                new_sl_price = entry_price
                update_stop_loss_order(symbol=position['symbol'], side=side, amount=remaining_amount, new_stop_price=new_sl_price)
                database.update_position_after_partial_tp(position['symbol'], remaining_amount, new_sl_price)
                send_telegram_message(format_partial_tp_message(position['symbol'], amount_to_close, remaining_amount, entry_price))
                log_message = f"Kısmi kâr alındı: {position['symbol']} pozisyonunda SL giriş seviyesine çekildi."
                database.log_event("SUCCESS", "Strategy", log_message)
            else:
                log_message = f"Kısmi TP emri gönderilemedi: {position['symbol']} - {result.get('message')}"
                logging.error(f"Kısmi kâr alma sırasında pozisyon kapatılamadı: {result.get('message')}")
                database.log_event("ERROR", "Trade", log_message)

def handle_trailing_stop_loss(position: dict, current_price: float):
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
            if "Başarılı" in str(result) or "Simülasyon" in str(result):
                database.update_position_sl(position['symbol'], new_sl)
                log_message = f"İz Süren SL güncellendi: {position['symbol']} için yeni SL: {new_sl:.4f} USDT."
                database.log_event("INFO", "Strategy", log_message)