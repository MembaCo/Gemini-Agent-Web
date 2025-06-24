# ==============================================================================
# File: backend/core/scanner.py
# @author: Memba Co.
# ==============================================================================
import logging
import time
import database
from core import app_config
from tools import get_top_gainers_losers, _get_unified_symbol, _fetch_price_natively, get_technical_indicators
from core import agent as core_agent
from core.trader import open_new_trade, TradeException
from notifications import send_telegram_message
from google.api_core import exceptions as google_exceptions

BLACKLISTED_SYMBOLS = {}

def execute_single_scan_cycle():
    """
    Proaktif tarayıcının tek bir tam döngüsünü çalıştırır ve sonuçları
    bir sözlük olarak döndürür.
    """
    # DÜZELTME: Her döngü başladığında en güncel ayarları yükle.
    app_config.load_config()
    logging.info("--- 🚀 Yeni Proaktif Tarama Döngüsü Başlatılıyor 🚀 ---")
    
    scan_results = { "summary": { "total_scanned": 0, "opportunities_found": 0, "data_errors": 0 }, "details": [] }

    if len(database.get_all_positions()) >= app_config.settings.get('MAX_CONCURRENT_TRADES', 5):
        msg = "Maksimum pozisyon limitine ulaşıldı. Tarama atlanıyor."
        logging.warning(msg)
        scan_results["details"].append({"type": "warning", "symbol": "SYSTEM", "message": msg})
        return scan_results

    open_symbols = {p['symbol'] for p in database.get_all_positions()}

    now = time.time()
    for symbol, expiry in list(BLACKLISTED_SYMBOLS.items()):
        if now > expiry:
            del BLACKLISTED_SYMBOLS[symbol]
            logging.info(f"{symbol} dinamik kara listeden çıkarıldı.")

    symbols_to_scan = []
    
    whitelist_symbols = [_get_unified_symbol(s) for s in app_config.settings.get('PROACTIVE_SCAN_WHITELIST', [])]
    symbols_to_scan.extend(whitelist_symbols)
    logging.info(f"Beyaz listeden eklendi: {', '.join(whitelist_symbols) or 'Yok'}")

    if app_config.settings.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
        try:
            logging.info("En çok yükselen/düşenler listesi çekiliyor...")
            gainer_loser_list = get_top_gainers_losers(
                top_n=app_config.settings.get('PROACTIVE_SCAN_TOP_N', 10),
                min_volume_usdt=app_config.settings.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
            )
            symbols_to_scan.extend([item['symbol'] for item in gainer_loser_list])
            logging.info(f"Yükselen/Düşenler listesinden eklendi ({len(gainer_loser_list)} adet)")
        except Exception as e:
            logging.error(f"Yükselen/Düşenler listesi alınamadı: {e}")
            scan_results["details"].append({"type": "critical", "symbol": "SYSTEM", "message": "Yükselen/Düşenler listesi alınamadı."})

    final_scan_list = []
    seen = set()
    static_blacklist = {_get_unified_symbol(s) for s in app_config.settings.get('PROACTIVE_SCAN_BLACKLIST', [])}

    for symbol in symbols_to_scan:
        if (symbol not in seen and symbol not in open_symbols and symbol not in static_blacklist and symbol not in BLACKLISTED_SYMBOLS):
            final_scan_list.append(symbol)
            seen.add(symbol)
    
    if not final_scan_list:
        msg = "Analiz edilecek yeni ve uygun sembol bulunamadı."
        logging.info(msg)
        scan_results["details"].append({"type": "info", "symbol": "SYSTEM", "message": msg})
        return scan_results

    scan_results["summary"]["total_scanned"] = len(final_scan_list)
    logging.info(f"Filtrelenmiş Nihai Tarama Listesi ({len(final_scan_list)} sembol): {', '.join(final_scan_list)}")

    for symbol in final_scan_list:
        if len(database.get_all_positions()) >= app_config.settings.get('MAX_CONCURRENT_TRADES', 5):
            logging.warning("Tarama sırasında maksimum pozisyon limitine ulaşıldı. Döngü sonlandırılıyor."); break
        
        try:
            logging.info(f"🔍 Analiz ediliyor: {symbol}")
            current_price = _fetch_price_natively(symbol)
            if not current_price: logging.warning(f"{symbol} için fiyat alınamadı, atlanıyor."); continue
            entry_tf = app_config.settings.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
            entry_indicators_result = get_technical_indicators(f"{symbol},{entry_tf}")
            if entry_indicators_result.get("status") != "success":
                msg = f"({entry_tf}) için teknik veri alınamadı: {entry_indicators_result.get('message')}"
                logging.error(f"{symbol} {msg}"); scan_results["summary"]["data_errors"] += 1
                scan_results["details"].append({"type": "error", "symbol": symbol, "message": msg})
                if 'NaN' in entry_indicators_result.get('message', ''):
                    BLACKLISTED_SYMBOLS[symbol] = time.time() + 3600
                    logging.warning(f"{symbol} sürekli 'NaN' hatası veriyor, 1 saatliğine dinamik kara listeye alındı.")
                continue
            
            final_prompt = ""
            if app_config.settings.get('PROACTIVE_SCAN_MTA_ENABLED', True):
                trend_tf = app_config.settings.get('PROACTIVE_SCAN_TREND_TIMEFRAME', '4h')
                trend_indicators_result = get_technical_indicators(f"{symbol},{trend_tf}")
                if trend_indicators_result.get("status") != "success":
                    msg = f"({trend_tf}) için trend verisi alınamadı: {trend_indicators_result.get('message')}"
                    logging.error(f"{symbol} {msg}"); scan_results["summary"]["data_errors"] += 1
                    scan_results["details"].append({"type": "error", "symbol": symbol, "message": msg}); continue
                final_prompt = core_agent.create_mta_analysis_prompt(symbol, current_price, entry_tf, entry_indicators_result["data"], trend_tf, trend_indicators_result["data"])
            else:
                final_prompt = core_agent.create_final_analysis_prompt(symbol, entry_tf, current_price, entry_indicators_result["data"])
            
            try:
                result = core_agent.llm.invoke(final_prompt)
            except google_exceptions.ResourceExhausted as e:
                msg = "Google AI API kullanım kotası aşıldı. Tarama bu döngü için durduruluyor."
                logging.error(msg); scan_results["details"].append({"type": "critical", "symbol": "API_QUOTA", "message": msg}); break
            
            parsed_data = core_agent.parse_agent_response(result.content)
            if not parsed_data:
                msg = f"Yapay zekadan {symbol} için geçerli yanıt alınamadı."; logging.error(msg + f" Yanıt: {result.content}")
                scan_results["summary"]["data_errors"] += 1; scan_results["details"].append({"type": "error", "symbol": symbol, "message": "Yapay zekadan geçerli yanıt alınamadı."}); continue

            recommendation = parsed_data.get("recommendation")
            if recommendation in ["AL", "SAT"]:
                scan_results["summary"]["opportunities_found"] += 1
                if app_config.settings.get('PROACTIVE_SCAN_AUTO_CONFIRM'):
                    msg = f"FIRSAT BULUNDU ve OTOMATİK ONAYLANDI: '{recommendation}' tavsiyesi. İşlem açılıyor..."
                    logging.info(f"{symbol} için {msg}"); scan_results["details"].append({"type": "success", "symbol": symbol, "message": msg})
                    open_new_trade(symbol=symbol, recommendation=recommendation, timeframe=entry_tf, current_price=current_price)
                else:
                    msg = f"FIRSAT BULUNDU (Manuel Onay Bekliyor): '{recommendation}' tavsiyesi."
                    logging.info(f"{symbol} için {msg}"); scan_results["details"].append({"type": "opportunity", "symbol": symbol, "message": msg, "data": parsed_data})
                    send_telegram_message(f"🔔 *Fırsat Bulundu (Onay Bekliyor)*\n`{symbol}` için `{recommendation}` tavsiyesi verildi.\nLütfen arayüzden kontrol edin.")
            else:
                msg = f"Net bir al/sat sinyali bulunamadı ('{recommendation}')."
                logging.info(f"{symbol} için {msg}"); scan_results["details"].append({"type": "info", "symbol": symbol, "message": msg})
        except TradeException as te:
            logging.error(f"İşlem açılamadı ({symbol}): {te}"); scan_results["summary"]["data_errors"] += 1
            scan_results["details"].append({"type": "critical", "symbol": symbol, "message": f"İşlem Açılamadı: {te}"})
        except Exception as e:
            logging.critical(f"Tarama döngüsünde {symbol} işlenirken KRİTİK HATA: {e}", exc_info=True); scan_results["summary"]["data_errors"] += 1
            scan_results["details"].append({"type": "critical", "symbol": symbol, "message": f"Kritik Hata: {str(e)}"})
            BLACKLISTED_SYMBOLS[symbol] = time.time() + 1800; logging.warning(f"{symbol} kritik hata nedeniyle 30 dakikalığına dinamik kara listeye alındı.")
        time.sleep(2)
    logging.info("--- ✅ Proaktif Tarama Döngüsü Tamamlandı ✅ ---")
    return scan_results