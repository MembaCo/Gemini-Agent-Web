# main.py
# @author: Memba Co.

import os
import json
import time
import threading
import logging
import subprocess
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from telegram_bot import run_telegram_bot
import tools

from tools import (
    get_market_price, get_technical_indicators, execute_trade_order,
    initialize_exchange, get_open_positions_from_exchange, get_atr_value,
    _get_unified_symbol, get_top_gainers_losers, _fetch_price_natively,
    str_to_bool, get_wallet_balance,
    cancel_all_open_orders, get_funding_rate, get_order_book_depth, calculate_pnl,
    get_latest_news # 'exchange' buradan kaldırıldı
)
import config
import database
from notifications import send_telegram_message, format_open_position_message, format_close_position_message, format_partial_tp_message

# --- Ortam Değişkenleri ve Loglama Ayarları ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "Gemini Trading Agent")

BLACKLISTED_SYMBOLS = {}

# --- Yapay Zeka Ajanının Başlatılması ---
try:
    llm = ChatGoogleGenerativeAI(model=config.GEMINI_MODEL, temperature=0.1)
    agent_tools = [get_market_price, get_technical_indicators, get_funding_rate, get_order_book_depth, get_latest_news]
    prompt_template = hub.pull("hwchase17/react")
    agent = create_react_agent(llm=llm, tools=agent_tools, prompt=prompt_template)
    agent_executor = AgentExecutor(
        agent=agent, tools=agent_tools, verbose=str_to_bool(os.getenv("AGENT_VERBOSE", "True")),
        handle_parsing_errors="Lütfen JSON formatında geçerli bir yanıt ver.",
        max_iterations=8
    )
except Exception as e:
    logging.critical(f"LLM veya Agent başlatılırken hata oluştu: {e}")
    sys.exit(1)

# --- Prompt Oluşturma Fonksiyonları ---

def create_mta_analysis_prompt(symbol: str, price: float, entry_timeframe: str, entry_indicators: dict, trend_timeframe: str, trend_indicators: dict, market_sentiment: dict, news_data: str) -> str:
    entry_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in entry_indicators.items()])
    trend_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in trend_indicators.items()])
    
    sentiment_text = (
        f"- Fonlama Oranı: {market_sentiment.get('funding_rate', 'N/A'):.4f}\n"
        f"- Alış/Satış Oranı: {market_sentiment.get('bid_ask_ratio', 'N/A')}"
    )

    news_section = f"""
### Temel Analiz (Son Haberler)
{news_data}""" if config.USE_NEWS_ANALYSIS else ""

    return f"""
Sen, teknik, temel (haber) ve duyarlılık analizini birleştiren, piyasanın usta analistisin.
Görevin, sana sunulan tüm verileri, aşağıda belirtilen kurallara göre sentezleyerek kapsamlı bir analiz yapmak ve net bir ticaret kararı ('AL', 'SAT' veya 'BEKLE') vermektir.

## ANALİZ KURALLARI (ÖNCELİK SIRASINA GÖRE):
1.  **Haberleri Kontrol Et (En Yüksek Öncelik):** Eğer haber verisi sunulduysa ve piyasayı olumsuz etkileyebilecek (FUD, hack, regülasyon vb.) net bir haber varsa, diğer tüm göstergeler olumlu olsa bile kararını 'BEKLE' olarak ver.
2.  **Piyasa Duyarlılığını Değerlendir:**
    - **Fonlama Oranı Kuralı:** Negatif değerler (-0.01 ve altı) aşırı short pozisyonları, pozitif değerler (+0.01 ve üstü) aşırı long pozisyonları gösterir. Yüksek mutlak değerler, potansiyel bir sıkışma (squeeze) ve tersine dönüş sinyali olabilir.
    - **Emir Defteri Kuralı:** 'Alış/Satış Oranı' değerini yorumla. 1.2'den büyükse net alım baskısı, 0.8'den küçükse net satış baskısı demektir. 0.8 ile 1.2 arasındaki değerler nötr kabul edilir.
3.  **Ana Trendi Belirle:** '{trend_timeframe}' zaman aralığındaki verilere bakarak ana trendin yönünü belirle. Ana trend ile duyarlılık verileri arasında bir çelişki varsa temkinli ol.
4.  **Sinyali Teyit Et:** '{entry_timeframe}' zaman aralığındaki giriş sinyalini, önceki adımlardaki tüm verilerle teyit et. Veriler arasında çelişki varsa 'BEKLE'.
5.  **Gerekçeni Açıkla:** Kararının arkasındaki mantığı, tüm veri setlerinden ve kurallardan bahsederek kısaca açıkla.

## SAĞLANAN VERİLER:
- Sembol: {symbol}
- Anlık Fiyat: {price}
{news_section}
### Piyasa Duyarlılığı Verileri
{sentiment_text}
### Ana Trend Verileri ({trend_timeframe})
{trend_indicator_text}
### Giriş Sinyali Verileri ({entry_timeframe})
{entry_indicator_text}

## İSTENEN JSON ÇIKTI FORMATI:
```json
{{
  "symbol": "{symbol}",
  "timeframe": "{entry_timeframe}",
  "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
  "reason": "Tüm analizlere ve SANA VERİLEN KURALLARA dayanarak yazdığın kısa ve net gerekçen.",
  "analysis_type": "MTA_Sentiment_News_V2",
  "trend_timeframe": "{trend_timeframe}",
  "data": {{
    "price": {price},
    "sentiment": {json.dumps(market_sentiment)}
  }}
}}
```
"""

def create_final_analysis_prompt(symbol: str, timeframe: str, price: float, indicators: dict, market_sentiment: dict, news_data: str) -> str:
    indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in indicators.items()])
    sentiment_text = (
        f"- Fonlama Oranı: {market_sentiment.get('funding_rate', 'N/A'):.4f}\n"
        f"- Alış/Satış Oranı: {market_sentiment.get('bid_ask_ratio', 'N/A')}"
    )
    news_section = f"""### Temel Analiz (Son Haberler)\n{news_data}""" if config.USE_NEWS_ANALYSIS else ""

    return f"""
Sen, uzman bir trading analistisin. Analiz yaparken sana verilen kurallara uymak zorundasın.

## ANALİZ KURALLARI:
1.  **Haber Kontrolü:** Olumsuz bir haber varsa, diğer verilere bakmadan 'BEKLE' de.
2.  **Duyarlılık Analizi:** Fonlama Oranı (-0.01'den küçük veya +0.01'den büyükse) ve Alış/Satış Oranı (0.8'den küçük veya 1.2'den büyükse) piyasa yönü hakkında güçlü ipuçları verir.
3.  **Teknik Analiz:** Teknik göstergeler arasındaki uyuma bak. RSI veya Stokastik aşırı alım/satım bölgelerindeyse bu bir tersine dönüş sinyali olabilir.
4.  **Sentez:** Tüm verileri birleştirerek net bir 'AL', 'SAT' veya 'BEKLE' kararı ver ve gerekçeni açıkla.

## SAĞLANAN VERİLER:
- Sembol: {symbol}, Zaman Aralığı: {timeframe}, Anlık Fiyat: {price}
{news_section}
### Piyasa Duyarlılığı
{sentiment_text}
### Teknik Göstergeler
{indicator_text}

## İSTENEN JSON ÇIKTI FORMATI:
```json
{{
  "symbol": "{symbol}",
  "timeframe": "{timeframe}",
  "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
  "reason": "Kurallara ve verilere dayanarak oluşturduğun kısa ve net gerekçen.",
  "analysis_type": "Single_Sentiment_News_V2",
  "data": {{
    "price": {price},
    "sentiment": {json.dumps(market_sentiment)}
  }}
}}
```
"""

def create_reanalysis_prompt(position: dict) -> str:
    symbol = position.get("symbol")
    timeframe = position.get("timeframe")
    side = position.get("side", "").upper()
    entry_price = position.get("entry_price")
    
    return f"""
Sen, tecrübeli bir pozisyon yöneticisisin ve görev odaklı bir ajansın.
## Mevcut Pozisyon Bilgileri:
- Sembol: {symbol}
- Yön: {side}
- Giriş Fiyatı: {entry_price}
- Analiz Zaman Aralığı: {timeframe}

## Görevin:
Sırasıyla aşağıdaki araçları kullanarak bu pozisyonun mevcut durumunu yeniden değerlendir:
1. `get_market_price`: Anlık fiyatı al. Fiyatın giriş fiyatına göre durumunu (kâr/zarar) not et.
2. `get_technical_indicators`: `{timeframe}` için teknik verileri al ve mevcut trendi yorumla.
3. `get_funding_rate`: Piyasadaki long/short baskısını anla.
4. `get_order_book_depth`: Anlık alım/satım baskısını ölç.
5. `get_latest_news`: Piyasayı etkileyebilecek kritik bir haber olup olmadığını kontrol et.

Tüm bu verileri sentezleyerek, pozisyon için 'TUT' (Hold) veya 'KAPAT' (Close) şeklinde net bir tavsiye ver.
Unutma, olumsuz bir haber varsa veya birden fazla gösterge pozisyonun aleyhine dönmüşse, riski azaltmak için 'KAPAT' demek en güvenli yoldur.

## Nihai Rapor Formatı:
Kararını ve tüm adımlardan elde ettiğin bulguları içeren gerekçeni bir JSON nesnesi olarak döndür.
Örnek: {{"recommendation": "KAPAT", "reason": "Fiyat giriş seviyesinin altına düştü. Emir defterinde satış baskısı arttı (oran < 1.0) ve olumsuz bir regülasyon haberi çıktı. Riski ortadan kaldırmak için pozisyon kapatılmalı."}}
"""

def parse_agent_response(response: str) -> dict | None:
    if not response or not isinstance(response, str): return None
    try:
        if "```json" in response: response = response.split("```json")[1].split("```")[0]
        elif "```" in response: response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
    except (json.JSONDecodeError, IndexError):
        logging.error(f"JSON ayrıştırma hatası. Gelen Yanıt: {response}")
        return None

# --- Ana İşlevsel Mantık ---

def check_and_manage_positions():
    """Tüm açık pozisyonları tek bir API çağrısıyla çeker ve yönetir."""
    exchange_positions_raw = get_open_positions_from_exchange.invoke({})
    if not isinstance(exchange_positions_raw, list):
        logging.error(f"Borsadan pozisyonlar alınamadı, dönen veri: {exchange_positions_raw}"); return
        
    exchange_positions_map = {_get_unified_symbol(p.get('symbol')): p for p in exchange_positions_raw}
    db_positions = database.get_all_positions()
    db_positions_map = {p['symbol']: p for p in db_positions}

    for symbol, db_pos in list(db_positions_map.items()):
        exchange_pos = exchange_positions_map.get(symbol)

        if not exchange_pos:
            logging.warning(f"Pozisyon '{symbol}' veritabanında var ama borsada yok. Veritabanından siliniyor.")
            database.remove_position(symbol)
            continue

        try:
            current_price = float(exchange_pos.get('markPrice'))
            side, sl_price, tp_price = db_pos.get("side"), db_pos.get("stop_loss", 0.0), db_pos.get("take_profit", 0.0)
            
            close_reason = None
            if sl_price > 0 and ( (side == "buy" and current_price <= sl_price) or (side == "sell" and current_price >= sl_price) ):
                close_reason = "SL"
            elif tp_price > 0 and ( (side == "buy" and current_price >= tp_price) or (side == "sell" and current_price <= tp_price) ):
                close_reason = "TP"
            
            if close_reason:
                logging.info(f"\n[AUTO] POZİSYON HEDEFE ULAŞTI ({close_reason}): {symbol} @ {current_price}")
                db_pos['close_price'] = current_price
                handle_manual_close(db_pos, from_auto=True, close_reason=close_reason)
                continue

            if config.USE_PARTIAL_TP and not db_pos.get('partial_tp_executed'):
                initial_sl, entry_price = db_pos.get('initial_stop_loss'), db_pos.get('entry_price')
                if initial_sl and entry_price:
                    risk_distance = abs(entry_price - initial_sl)
                    partial_tp_price = entry_price + (risk_distance * config.PARTIAL_TP_TARGET_RR) if side == 'buy' else entry_price - (risk_distance * config.PARTIAL_TP_TARGET_RR)
                    
                    if (side == 'buy' and current_price >= partial_tp_price) or (side == 'sell' and current_price <= partial_tp_price):
                        logging.info(f"\n[PARTIAL-TP] {symbol} için kısmi kâr alma hedefi {partial_tp_price:.4f} ulaşıldı.")
                        
                        initial_amount = db_pos.get('initial_amount') or db_pos.get('amount')
                        amount_to_close = initial_amount * (config.PARTIAL_TP_CLOSE_PERCENT / 100)
                        
                        # --- YENİ EKLENEN KONTROL ---
                        # Borsanın bu sembol için izin verdiği minimum işlem miktarını al
                        market_info = tools.exchange.markets.get(symbol)
                        min_amount = market_info['limits']['amount']['min'] if market_info else 0.001 # Güvenlik için varsayılan
                        
                        if amount_to_close < min_amount:
                            logging.warning(f"[PARTIAL-TP-SKIP] {symbol} için kapatılacak miktar ({amount_to_close:.8f}) minimum limitten ({min_amount}) düşük. İşlem atlanıyor.")
                            continue # Bu döngüyü atla ve bir sonraki pozisyona geç
                        # --- KONTROL SONU ---

                        remaining_amount = db_pos['amount'] - amount_to_close
                        
                        if remaining_amount > 0:
                            partial_pnl = calculate_pnl(side, entry_price, partial_tp_price, amount_to_close)
                            # Kapatma emrini, borsanın hassasiyetine göre formatlanmış miktar ile gönder
                            result_str = execute_trade_order.invoke({"symbol": symbol, "side": ('sell' if side == 'buy' else 'buy'), "amount": amount_to_close})
                            
                            if "başarı" in result_str.lower() or "simülasyon" in result_str.lower():
                                logging.info(f"Kısmi kâr alma başarılı: {amount_to_close:.4f} {symbol} kapatıldı. Realize edilen PNL: {partial_pnl:.2f} USDT")
                                
                                logging.info(f"Kısmi TP sonrası eski emirler temizleniyor: {symbol}")
                                cancel_all_open_orders.invoke(symbol)
                                time.sleep(1) 

                                new_sl_price = entry_price
                                try:
                                    if config.LIVE_TRADING:
                                        # --- DÜZELTME BAŞLANGICI ---
                                        # Pozisyonun ters yönünü burada tanımla
                                        opposite_side = 'sell' if side == 'buy' else 'buy'
                                        # Kalan pozisyonun miktarını kullan
                                        remaining_amount_formatted = tools.exchange.amount_to_precision(symbol, remaining_amount)
                                        # Yeni SL emrini oluştur
                                        tools.exchange.create_order(symbol, 'STOP_MARKET', opposite_side, remaining_amount_formatted, None, {'stopPrice': new_sl_price, 'reduceOnly': True})
                                        # --- DÜZELTME SONU ---
                                    logging.info(f"Başarılı: Kalan pozisyon için yeni SL emri {new_sl_price} olarak oluşturuldu.")
                                except Exception as e:
                                    logging.error(f"Kısmi TP sonrası yeni SL emri oluşturulurken HATA: {e}", exc_info=True)

                                total_realized_pnl = db_pos.get('realized_pnl', 0.0) + partial_pnl
                                database.update_position_after_partial_tp(symbol, remaining_amount, new_sl_price, total_realized_pnl)
                                
                                message = format_partial_tp_message(symbol, amount_to_close, remaining_amount, entry_price)
                                send_telegram_message(message)
                                continue
                            else:
                                logging.error(f"Kısmi kâr alma sırasında pozisyon kapatılamadı: {result_str}")

            if config.USE_TRAILING_STOP_LOSS:
                entry_price, initial_sl = db_pos.get("entry_price", 0.0), db_pos.get('initial_stop_loss')
                if not initial_sl: continue
                profit_perc = ((current_price - entry_price) / entry_price) * 100 * (1 if side == 'buy' else -1)
                
                if profit_perc > config.TRAILING_STOP_ACTIVATION_PERCENT:
                    original_sl_distance = abs(entry_price - initial_sl)
                    new_sl_candidate = current_price - original_sl_distance if side == 'buy' else current_price + original_sl_distance
                    if (side == 'buy' and new_sl_candidate > sl_price) or (side == 'sell' and new_sl_candidate < sl_price):
                        logging.info(f"[TRAIL-SL] {symbol} için yeni SL tetiklendi: {sl_price:.4f} -> {new_sl_candidate:.4f}")
                        opposite_side = 'sell' if side == 'buy' else 'buy'
                        try:
                            cancel_all_open_orders.invoke(symbol)
                            time.sleep(1)
                            if config.LIVE_TRADING:
                                 tools.exchange.create_order(symbol, 'STOP_MARKET', opposite_side, db_pos['amount'], None, {'stopPrice': new_sl_candidate, 'reduceOnly': True})
                            database.update_position_sl(symbol, new_sl_candidate)
                        except Exception as e:
                            logging.error(f"Trailing SL güncellenirken hata: {e}")
        except Exception as e:
            logging.error(f"Pozisyon kontrolü sırasında hata: {e} - Pozisyon: {db_pos}", exc_info=True)

def background_position_checker():
    logging.info("--- Arka plan pozisyon kontrolcüsü başlatıldı. ---")
    while True:
        try:
            check_and_manage_positions()
        except Exception as e:
            logging.critical(f"Arka plan kontrolcüsünde KRİTİK HATA: {e}", exc_info=True)
        time.sleep(config.POSITION_CHECK_INTERVAL_SECONDS)

def handle_trade_confirmation(recommendation, trade_symbol, current_price, timeframe, auto_confirm=False):
    if not isinstance(current_price, (int, float)) or current_price <= 0:
        logging.error("Geçersiz fiyat bilgisi, işlem iptal edildi.")
        return

    prompt_message = f">>> [FIRSAT] {trade_symbol} @ {current_price:.4f} için '{recommendation}' tavsiyesi verildi. İşlem açılsın mı? (e/h): "
    user_onay = "e" if auto_confirm else input(prompt_message).lower()
    
    if user_onay == "e":
        if auto_confirm: logging.info(f"İşlem otomatik olarak onaylandı: {trade_symbol}")
        try:
            active_positions = database.get_all_positions()
            if len(active_positions) >= config.MAX_CONCURRENT_TRADES:
                print("\n### UYARI: Maksimum pozisyon limitine ulaşıldı. ###"); return

            trade_side = "buy" if "AL" in recommendation else "sell"
            
            atr_result = get_atr_value.invoke({"symbol_and_timeframe": f"{trade_symbol},{timeframe}"})
            if atr_result.get("status") != "success":
                print(f"### HATA: ATR değeri alınamadı: {atr_result.get('message')} ###"); return
            atr_value = atr_result['value']

            sl_distance = atr_value * config.ATR_MULTIPLIER_SL
            stop_loss_price = current_price - sl_distance if trade_side == "buy" else current_price + sl_distance

            balance_result = get_wallet_balance.invoke({})
            if balance_result.get("status") != "success":
                print(f"### HATA: Cüzdan bakiyesi alınamadı: {balance_result.get('message')} ###"); return
            wallet_balance = balance_result.get('balance', 0.0)

            risk_amount_usd = wallet_balance * (config.RISK_PER_TRADE_PERCENT / 100)
            sl_price_diff = abs(current_price - stop_loss_price)
            if sl_price_diff <= 0:
                print(f"HATA: Stop-loss mesafesi geçersiz ({sl_price_diff}), pozisyon açılamıyor."); return
            
            trade_amount = risk_amount_usd / sl_price_diff
            notional_value = trade_amount * current_price
            required_margin = notional_value / config.LEVERAGE

            logging.info(f"Dinamik Pozisyon Hesabı: Bakiye={wallet_balance:.2f} USDT, Risk={risk_amount_usd:.2f} USDT, Pozisyon Büyüklüğü={notional_value:.2f} USDT, Gerekli Marjin={required_margin:.2f} USDT")

            if required_margin > wallet_balance:
                print(f"### UYARI: Gerekli marjin ({required_margin:.2f} USDT) mevcut bakiyeden ({wallet_balance:.2f} USDT) fazla. İşlem iptal edildi."); return

            tp_distance = sl_distance * config.RISK_REWARD_RATIO_TP
            take_profit_price = current_price + tp_distance if trade_side == "buy" else current_price - tp_distance
            
            position_to_open = {
                "symbol": trade_symbol, "side": trade_side, "amount": trade_amount, 
                "stop_loss": stop_loss_price, "take_profit": take_profit_price, "leverage": config.LEVERAGE,
                "price": current_price if config.DEFAULT_ORDER_TYPE == 'LIMIT' else None
            }
            
            result_str = execute_trade_order.invoke(position_to_open)
            print(f"İşlem Sonucu: {result_str}")

            if "başarı" in result_str.lower() or "simülasyon" in result_str.lower():
                final_entry_price = position_to_open.get('price') or current_price
                managed_position_details = {
                    "symbol": trade_symbol, "side": trade_side, "amount": trade_amount, 
                    "entry_price": final_entry_price, "timeframe": timeframe, "leverage": config.LEVERAGE,
                    "stop_loss": stop_loss_price, "take_profit": take_profit_price
                }
                database.add_position(managed_position_details)
                print("\n+++ YENİ POZİSYON AÇILDI VE VERİTABANINA KAYDEDİLDİ +++")
                print(json.dumps(managed_position_details, indent=2))
                message = format_open_position_message(managed_position_details)
                send_telegram_message(message)
            else:
                print(f"\n--- İŞLEM BAŞARISIZ OLDU. Dönen Mesaj: {result_str} ---")
        except Exception as e:
            logging.error(f"İşlem hazırlığı sırasında bir hata oluştu: {e}", exc_info=True)

def sync_and_display_positions():
    """Borsa ile veritabanını senkronize eder ve pozisyonları listeler."""
    print("\n--- Pozisyonlar Görüntüleniyor... ---")
    
    if not config.LIVE_TRADING:
        active_positions_db = database.get_all_positions()
        print("--- SİMÜLASYON MODU AKTİF ---")
        if not active_positions_db:
            print("Bot tarafından yönetilen simüle edilmiş pozisyon bulunmuyor.")
        else:
            print(f"--- Bot Veritabanındaki Simüle Pozisyonlar: {len(active_positions_db)} ---")
            for pos in active_positions_db:
                pnl_info = "| PNL Hesaplanamadı"
                current_price = _fetch_price_natively(pos['symbol'])
                if current_price is not None:
                    entry_price, amount, side = pos.get('entry_price', 0), pos.get('amount', 0), pos.get('side', 'buy')
                    pnl = calculate_pnl(side, entry_price, current_price, amount)
                    margin = (entry_price * amount) / pos.get('leverage', 1) if pos.get('leverage', 1) > 0 else 0
                    pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
                    pnl_status = "⬆️ KAR" if pnl >= 0 else "⬇️ ZARAR"
                    pnl_info = f"| PNL (Tahmini): {pnl:+.2f} USDT ({pnl_percentage:+.2f}%) {pnl_status}"
                print(f"  - {pos['symbol']} ({pos['side'].upper()}) | Giriş: {pos.get('entry_price', 0):.4f} | Miktar: {pos.get('amount', 0):.4f} {pnl_info}")
        print("--- Simülasyon gösterimi tamamlandı. ---")
        return

    print("--- CANLI MOD: Borsa ile Senkronize Ediliyor... ---")
    try:
        active_positions_db = database.get_all_positions()
        managed_positions_map = {p['symbol']: p for p in active_positions_db}

        exchange_positions_raw = get_open_positions_from_exchange.invoke({})
        if not isinstance(exchange_positions_raw, list):
            logging.error(f"Borsadan pozisyonlar alınamadı, dönen veri: {exchange_positions_raw}"); return
        exchange_positions_map = {_get_unified_symbol(p.get('symbol')): p for p in exchange_positions_raw}

        for symbol, ex_pos in exchange_positions_map.items():
            if symbol not in managed_positions_map:
                print(f"  - {symbol} borsada açık ama bot tarafından yönetilmiyor.")
                add_to_bot = input(f"      >>> Yönetime eklensin mi? (evet/hayır): ").lower()
                if add_to_bot == 'evet':
                    timeframe = input(f"      >>> Orijinal zaman aralığını girin (örn: 1h, 15m): ").lower().strip() or "1h"
                    leverage = float(ex_pos.get('leverage') or config.LEVERAGE)
                    entry_price = float(ex_pos.get('entryPrice', 0.0) or 0.0)
                    sl_input = input(f"      >>> Stop-Loss fiyatını girin (boş bırakmak için enter): ")
                    tp_input = input(f"      >>> Take-Profit fiyatını girin (boş bırakmak için enter): ")
                    new_pos = { "symbol": symbol, "side": 'buy' if ex_pos.get('side') == 'long' else 'sell', "amount": float(ex_pos.get('contracts', 0.0)), "entry_price": entry_price, "timeframe": timeframe, "leverage": leverage, "stop_loss": float(sl_input) if sl_input else 0.0, "take_profit": float(tp_input) if tp_input else 0.0 }
                    database.add_position(new_pos)
                    print(f"      +++ {symbol} pozisyonu bot yönetimine eklendi.")

        for symbol in list(managed_positions_map.keys()):
            if symbol not in exchange_positions_map:
                logging.warning(f"Pozisyon '{symbol}' veritabanında var ama borsada yok. Veritabanından siliniyor.")
                database.remove_position(symbol)
        
        final_managed_positions = database.get_all_positions()
        final_managed_symbols = {p['symbol'] for p in final_managed_positions}

        if not exchange_positions_map:
             print("Borsada açık pozisyon bulunmuyor.")
        else:
             print(f"--- Borsada Bulunan Açık Pozisyonlar: {len(exchange_positions_map)} ---")
             for symbol, pos_data in exchange_positions_map.items():
                side = 'buy' if pos_data.get('side', 'long') == 'long' else 'sell'
                notional = float(pos_data.get('notional', 0.0) or 0.0)
                pnl = float(pos_data.get('unrealizedPnl', 0.0) or 0.0)
                margin = float(pos_data.get('initialMargin', 0.0) or 0.0)
                pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
                pnl_status = "⬆️ KAR" if pnl >= 0 else "⬇️ ZARAR"
                is_managed = "✅ Yönetiliyor" if symbol in final_managed_symbols else "❌ Yönetilmiyor"
                print(f"  - {symbol} ({side.upper()}) | Büyüklük: {notional:.2f} USDT | PNL: {pnl:+.2f} USDT ({pnl_percentage:+.2f}%) [{pnl_status}] | {is_managed}")

        print("--- Senkronizasyon tamamlandı. ---")
    except Exception as e:
        logging.error(f"Senkronizasyon sırasında hata oluştu: {e}", exc_info=True)

def get_status_as_string() -> str:
    """Pozisyonları düz metin yerine Telegram'a uygun bir string olarak döndürür."""
    try:
        exchange_positions_raw = get_open_positions_from_exchange.invoke({})
        if not isinstance(exchange_positions_raw, list) or not exchange_positions_raw:
            return "Borsada açık pozisyon bulunmuyor."

        db_positions = database.get_all_positions()
        managed_symbols = {p['symbol'] for p in db_positions}
        output_lines = [f"<b>Borsada Bulunan Açık Pozisyonlar: {len(exchange_positions_raw)}</b>\n"]

        for pos_data in exchange_positions_raw:
            symbol = _get_unified_symbol(pos_data.get('symbol'))
            side = 'BUY' if pos_data.get('side', 'long') == 'long' else 'SELL'
            notional = float(pos_data.get('notional', 0.0) or 0.0)
            entry_price = float(pos_data.get('entryPrice', 0.0) or 0.0)
            pnl = float(pos_data.get('unrealizedPnl', 0.0) or 0.0)
            margin = float(pos_data.get('initialMargin', 0.0) or 0.0)
            pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
            pnl_emoji = "⬆️" if pnl >= 0 else "⬇️"
            managed_emoji = "✅" if symbol in managed_symbols else "❌"

            line = (
                f"\n<b>{managed_emoji} {symbol} ({side})</b>\n"
                f"  Büyüklük: {notional:.2f} USDT\n"
                f"  Giriş: {entry_price:.4f}\n"
                f"  PNL: {pnl:+.2f} USDT ({pnl_percentage:+.2f}%) {pnl_emoji}"
            )
            output_lines.append(line)
        return "\n".join(output_lines)
    except Exception as e:
        logging.error(f"Telegram status alınırken hata oluştu: {e}", exc_info=True)
        return f"Pozisyon durumu alınırken bir hata oluştu: {e}"

def _perform_analysis(symbol: str, entry_tf: str, use_mta: bool, trend_tf: str = None) -> dict | None:
    unified_symbol = _get_unified_symbol(symbol)
    logging.info(f"Analiz başlatılıyor: {unified_symbol} ({'MTA' if use_mta else 'Single'})")
    
    try:
        current_price = _fetch_price_natively(unified_symbol)
        if not current_price:
            logging.error(f"Fiyat alınamadı: {unified_symbol}"); return None

        entry_indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{unified_symbol},{entry_tf}"})
        if entry_indicators_result.get("status") != "success":
            logging.error(f"{unified_symbol} ({entry_tf}) için teknik veri alınamadı: {entry_indicators_result.get('message')}"); return None
        entry_indicators_data = entry_indicators_result["data"]
        
        market_sentiment_data = {}
        if config.DEFAULT_MARKET_TYPE == 'future':
            funding_rate_result = get_funding_rate.invoke(unified_symbol)
            if funding_rate_result.get("status") == "success":
                market_sentiment_data['funding_rate'] = funding_rate_result.get('funding_rate')
            
            order_book_result = get_order_book_depth.invoke(unified_symbol)
            if order_book_result.get("status") == "success":
                market_sentiment_data['bid_ask_ratio'] = order_book_result.get('bid_ask_ratio')

        news_data_str = "Haber analizi kapalı."
        if config.USE_NEWS_ANALYSIS:
            logging.info(f"{unified_symbol} için son haberler çekiliyor...")
            news_data_str = get_latest_news.invoke(unified_symbol)
        
        final_prompt = ""
        if use_mta and trend_tf:
            trend_indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{unified_symbol},{trend_tf}"})
            if trend_indicators_result.get("status") != "success":
                logging.error(f"{unified_symbol} ({trend_tf}) için trend verisi alınamadı: {trend_indicators_result.get('message')}"); return None
            trend_indicators_data = trend_indicators_result["data"]
            final_prompt = create_mta_analysis_prompt(unified_symbol, current_price, entry_tf, entry_indicators_data, trend_tf, trend_indicators_data, market_sentiment_data, news_data_str)
        else:
            final_prompt = create_final_analysis_prompt(unified_symbol, entry_tf, current_price, entry_indicators_data, market_sentiment_data, news_data_str)

        logging.info(f"Yapay zeka analizi için {unified_symbol} gönderiliyor...")
        result = llm.invoke(final_prompt)
        parsed_data = parse_agent_response(result.content)

        if not parsed_data:
            logging.error(f"Yapay zekadan {unified_symbol} için geçerli yanıt alınamadı. Yanıt: {result.content}"); return None
        
        parsed_data['current_price'] = current_price
        return parsed_data

    except Exception as e:
        logging.critical(f"Analiz sırasında kritik hata ({unified_symbol}): {e}", exc_info=True)
        return None

def _execute_single_scan_cycle():
    logging.info("--- 🚀 Yeni Proaktif Tarama Döngüsü Başlatılıyor 🚀 ---")
    active_positions = database.get_all_positions()
    if len(active_positions) >= config.MAX_CONCURRENT_TRADES:
        logging.warning(f"Maksimum pozisyon limitine ({config.MAX_CONCURRENT_TRADES}) ulaşıldı. Tarama atlanıyor.")
        return
    open_symbols = {p['symbol'] for p in active_positions}

    now = time.time()
    for symbol, expiry in list(BLACKLISTED_SYMBOLS.items()):
        if now > expiry:
            del BLACKLISTED_SYMBOLS[symbol]
            logging.info(f"{symbol} dinamik kara listeden çıkarıldı.")

    symbols_to_scan = []
    whitelist_symbols = [_get_unified_symbol(s) for s in config.PROACTIVE_SCAN_WHITELIST]
    symbols_to_scan.extend(whitelist_symbols)
    logging.info(f"Beyaz listeden eklendi: {', '.join(whitelist_symbols) or 'Yok'}")

    if config.PROACTIVE_SCAN_USE_GAINERS_LOSERS:
        try:
            logging.info("En çok yükselen/düşenler listesi çekiliyor...")
            gainer_loser_list = get_top_gainers_losers(config.PROACTIVE_SCAN_TOP_N, config.PROACTIVE_SCAN_MIN_VOLUME_USDT)
            gainer_loser_symbols = [item['symbol'] for item in gainer_loser_list]
            symbols_to_scan.extend(gainer_loser_symbols)
            logging.info(f"Yükselen/Düşenler listesinden eklendi ({len(gainer_loser_symbols)} adet)")
        except Exception as e:
            logging.error(f"Yükselen/Düşenler listesi alınamadı: {e}")

    final_scan_list = []
    seen = set()
    static_blacklist = {_get_unified_symbol(s) for s in config.PROACTIVE_SCAN_BLACKLIST}

    for symbol in symbols_to_scan:
        if (symbol not in seen and 
            symbol not in open_symbols and
            symbol not in static_blacklist and
            symbol not in BLACKLISTED_SYMBOLS):
            final_scan_list.append(symbol)
            seen.add(symbol)
    
    if not final_scan_list:
        logging.info("Analiz edilecek yeni ve uygun sembol bulunamadı.")
        return

    logging.info(f"Filtrelenmiş Nihai Tarama Listesi ({len(final_scan_list)} sembol): {', '.join(final_scan_list)}")

    for symbol in final_scan_list:
        if len(database.get_all_positions()) >= config.MAX_CONCURRENT_TRADES:
            logging.warning("Tarama sırasında maksimum pozisyon limitine ulaşıldı. Döngü sonlandırılıyor.")
            break
        
        print("-" * 50)
        logging.info(f"🔍 Analiz ediliyor: {symbol}")
        
        analysis_result = _perform_analysis(
            symbol=symbol,
            entry_tf=config.PROACTIVE_SCAN_ENTRY_TIMEFRAME,
            use_mta=config.PROACTIVE_SCAN_MTA_ENABLED,
            trend_tf=config.PROACTIVE_SCAN_TREND_TIMEFRAME
        )

        if not analysis_result:
            logging.warning(f"{symbol} için analiz tamamlanamadı, bir sonraki sembole geçiliyor.")
            continue
        
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        
        recommendation = analysis_result.get("recommendation")
        if recommendation in ["AL", "SAT"]:
            handle_trade_confirmation(
                recommendation,
                analysis_result.get('symbol'),
                analysis_result.get('current_price'),
                config.PROACTIVE_SCAN_ENTRY_TIMEFRAME,
                auto_confirm=config.PROACTIVE_SCAN_AUTO_CONFIRM
            )
        else:
            logging.info(f"{symbol} için net bir al/sat sinyali bulunamadı ('{recommendation}').")
        
        time.sleep(5)

    logging.info("--- ✅ Proaktif Tarama Döngüsü Tamamlandı ✅ ---")

def run_proactive_scanner():
    logging.info("🚀 PROAKTİF TARAMA MODU BAŞLATILDI 🚀")
    if config.PROACTIVE_SCAN_IN_LOOP:
        while True:
            _execute_single_scan_cycle()
            logging.info(f"Döngüsel tarama aktif. Sonraki tarama için {config.PROACTIVE_SCAN_INTERVAL_SECONDS} saniye bekleniyor...")
            time.sleep(config.PROACTIVE_SCAN_INTERVAL_SECONDS)
    else:
        _execute_single_scan_cycle()
        print("Tek seferlik tarama tamamlandı. Ana menüye dönülüyor.")

def handle_new_analysis():
    active_positions = database.get_all_positions()
    if len(active_positions) >= config.MAX_CONCURRENT_TRADES:
        print("\n### UYARI: Maksimum pozisyon limitine ulaşıldı. ###"); return

    entry_timeframe = input(f"Giriş için zaman aralığı seçin (örn: 15m, 1h) [varsayılan: 15m]: ").lower().strip() or "15m"
    user_input = input(f"Analiz edilecek kripto parayı girin (örn: BTC): ")
    if not user_input: return
    
    analysis_result = _perform_analysis(
        symbol=user_input,
        entry_tf=entry_timeframe,
        use_mta=config.USE_MTA_ANALYSIS,
        trend_tf=config.MTA_TREND_TIMEFRAME
    )

    if not analysis_result:
        print("\n--- HATA: Analiz gerçekleştirilemedi. Detaylar için logları kontrol edin. ---")
        return

    print("\n--- Analiz Raporu ---")
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False))

    recommendation = analysis_result.get("recommendation")
    if recommendation in ["AL", "SAT"]:
        handle_trade_confirmation(
            recommendation, 
            analysis_result.get('symbol'), 
            analysis_result.get('current_price'), 
            entry_timeframe
        )
    else:
        print("\n--- Bir işlem tavsiyesi ('AL' veya 'SAT') bulunamadı. ---")

def handle_manage_position():
    active_positions = database.get_all_positions()
    if not active_positions:
        print("Yönetilecek açık pozisyon bulunmuyor."); return
    print("\n--- Yönetilen Açık Pozisyonlar ---")
    for i, pos in enumerate(active_positions):
        print(f"  [{i+1}] {pos['symbol']} ({pos['side'].upper()}) | Giriş: {pos.get('entry_price', 'N/A')}")
    try:
        choice_str = input("Yönetmek istediğiniz pozisyonun numarasını girin (çıkmak için 'q'): ")
        if choice_str.lower() == 'q': return
        pos_index = int(choice_str) - 1
        if not 0 <= pos_index < len(active_positions):
            print("Geçersiz numara."); return
        
        position_to_manage = active_positions[pos_index]
        while True:
            print(f"\n--- {position_to_manage['symbol']} Pozisyonu Yönetiliyor ---")
            print("1. Manuel Kapat")
            print("2. Pozisyonu Yeniden Analiz Et")
            print("3. Ana Menüye Dön")
            action_choice = input("Seçiminiz: ")
            if action_choice == '1':
                close_result = handle_manual_close(position_to_manage)
                print(close_result)
                break 
            elif action_choice == '2':
                handle_reanalyze_position(position_to_manage); break
            elif action_choice == '3': break
            else: print("Geçersiz seçim.")
    except (ValueError, IndexError):
        print("Geçersiz giriş.")

def handle_manual_close(position: dict, from_auto: bool = False, close_reason: str = "MANUAL", send_notification: bool = True) -> str:
    """Bir pozisyonu manuel veya otomatik olarak kapatır ve bir sonuç mesajı döndürür."""
    if not from_auto:
        print(f"UYARI: {position['symbol']} pozisyonunu manuel olarak kapatacaksınız.")
        onay = input("Emin misiniz? (evet/hayır): ").lower()
        if onay != 'evet':
            return "İşlem iptal edildi."
    
    symbol = position['symbol']
    logging.info(f"Kapatılacak pozisyon ({symbol}) için mevcut emirler iptal ediliyor...")
    cancel_all_open_orders.invoke(symbol)
    time.sleep(1) 

    close_side = 'sell' if position['side'] == 'buy' else 'buy'
    result = execute_trade_order.invoke({
        "symbol": symbol, "side": close_side, "amount": position['amount']
    })
    
    if "başarı" in result.lower() or "simülasyon" in result.lower():
        closed_pos = database.remove_position(symbol)
        if closed_pos:
            current_price = position.get('close_price') or _fetch_price_natively(closed_pos['symbol']) or closed_pos['entry_price']
            
            pnl = calculate_pnl(side=closed_pos.get('side'), entry_price=closed_pos.get('entry_price'), close_price=current_price, amount=closed_pos.get('amount'))
            closed_pos['close_price'] = current_price

            database.log_trade_to_history(closed_pos, current_price, close_reason)
            if send_notification:
                message = format_close_position_message(closed_pos, pnl, close_reason)
                send_telegram_message(message)
        
        logging.info(f"POZİSYON BAŞARIYLA KAPATILDI: {symbol}")
        return f"✅ `{symbol}` pozisyonu `{close_reason}` nedeniyle başarıyla kapatıldı."
    else:
        logging.error(f"Pozisyon kapatılamadı: {symbol}. Sonuç: {result}")
        return f"❌ `{symbol}` pozisyonu kapatılamadı. Sonuç: {result}"

def _get_reanalysis_report(position: dict) -> str:
    """Bir pozisyon için yeniden analiz yapar ve sonucu metin olarak döndürür."""
    reanalysis_prompt = create_reanalysis_prompt(position)
    try:
        result = agent_executor.invoke({"input": reanalysis_prompt})
        parsed_data = parse_agent_response(result.get("output", ""))

        if not parsed_data or "recommendation" not in parsed_data:
            return f"❌ HATA: Ajan, `{position['symbol']}` için yeniden analiz sırasında geçerli bir tavsiye üretemedi."

        recommendation = parsed_data.get('recommendation')
        reason = parsed_data.get('reason', 'Gerekçe belirtilmedi.')
        
        report = (
            f"<b>📊 Yeniden Analiz Raporu [{position['symbol']}]</b>\n\n"
            f"<b>Tavsiye:</b> {recommendation}\n"
            f"<b>Gerekçe:</b> {reason}"
        )
        if recommendation == 'KAPAT':
            report += "\n\n⚠️ AJAN 'KAPAT' TAVSİYESİ VERDİ!"
        
        # Ajanın tavsiyesini de içeren tam veriyi döndürelim
        return json.dumps({
            "report_text": report,
            "recommendation": recommendation,
            "position": position
        })

    except Exception as e:
        logging.error(f"handle_reanalyze_position hatası: {e}", exc_info=True)
        return json.dumps({
            "report_text": f"❌ KRİTİK HATA: `{position['symbol']}` yeniden analiz edilirken bir sorun oluştu: {e}",
            "recommendation": "HATA"
        })
    
def handle_reanalyze_position(position):
    print(f"\n--- {position['symbol']} Pozisyonu Yeniden Analiz Ediliyor... ---")
    
    report_json_str = _get_reanalysis_report(position)
    report_data = json.loads(report_json_str)

    # HTML'i temizleyerek konsolda göster
    report_text_for_console = report_data.get('report_text', '').replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
    print(report_text_for_console)
    
    recommendation = report_data.get('recommendation')
    if recommendation == 'KAPAT':
        print("\nAJAN 'KAPAT' TAVSİYESİ VERDİ. POZİSYON KAPATILIYOR...")
        close_result = handle_manual_close(position, from_auto=True, close_reason="AGENT_CLOSE") 
        print(close_result)
    elif recommendation != "HATA":
        print("\nAJAN 'TUT' TAVSİYESİ VERDİ. POZİSYON AÇIK KALIYOR.")
            
def launch_dashboard():
    """Web arayüzü sunucusunu ayrı bir işlem olarak başlatır."""
    dashboard_script = os.path.join('dashboard', 'app.py')
    if not os.path.exists(dashboard_script):
        print("HATA: 'dashboard/app.py' dosyası bulunamadı. Lütfen proje yapısını kontrol edin.")
        return

    print("\n--- 📈 Web Arayüzü Başlatılıyor... ---")
    try:
        subprocess.Popen([sys.executable, dashboard_script])
        print("✅ Sunucu başlatıldı. [http://127.0.0.1:5001](http://127.0.0.1:5001) adresini tarayıcıda açın.")
    except Exception as e:
        print(f"❌ Web arayüzü başlatılamadı: {e}")

def main():
    database.init_db()
    initialize_exchange(config.DEFAULT_MARKET_TYPE)

    print("\n" + "="*50)
    print(f"           GEMINI TRADING AGENT BAŞLATILDI")
    print(f"                 Versiyon: {config.APP_VERSION}")
    print("="*50)
    print(f"UYARI: CANLI İŞLEM MODU {'✅ AKTİF ✅' if config.LIVE_TRADING else '❌ KAPALI (Simülasyon Modu) ❌'}.")
    if config.LIVE_TRADING:
        print("DİKKAT: Bot, Binance hesabınızda gerçek para ile işlem yapacaktır!")
    print(f"BİLDİRİMLER: Telegram {'✅ AKTİF ✅' if config.TELEGRAM_ENABLED else '❌ KAPALI ❌'}.")
    print("="*50 + "\n")

    checker_thread = threading.Thread(target=background_position_checker, daemon=True)
    checker_thread.start()

    if config.TELEGRAM_ENABLED:
        bot_actions = {
            'analyze': _perform_analysis,
            'scan': _execute_single_scan_cycle,
            'reanalyze': _get_reanalysis_report,
            'close': handle_manual_close,
            'get_status': get_status_as_string
        }
        telegram_thread = threading.Thread(target=run_telegram_bot, args=(bot_actions,), daemon=True)
        telegram_thread.start()
    
    menu_options = {
        "1": ("Pozisyonları Göster ve Senkronize Et", sync_and_display_positions),
        "2": ("Yeni Analiz Yap ve Pozisyon Aç", handle_new_analysis),
        "3": ("Açık Pozisyonu Yönet", handle_manage_position),
        "p": ("PROAKTİF TARAMAYI BAŞLAT (Fırsat Avcısı)", run_proactive_scanner),
        "d": ("WEB ARAYÜZÜNÜ BAŞLAT (Dashboard)", launch_dashboard),
        "q": ("Çıkış", lambda: print("Bot kapatılıyor..."))
    }
    
    while True:
        print("\n" + "="*50 + "\n           GEMINI TRADING AGENT MENU\n" + "="*50)
        
        for key, (text, func) in menu_options.items():
            if key == 'p' and not config.PROACTIVE_SCAN_ENABLED:
                continue
            print(f"{key}. {text}")

        choice = input("Seçiminiz: ").lower().strip()
        
        if choice == "q":
            menu_options[choice][1]()
            break

        action = menu_options.get(choice)
        if action:
            if choice == 'p' and not config.PROACTIVE_SCAN_ENABLED:
                 print("Geçersiz seçim. Lütfen menüden bir seçenek girin.")
            else:
                action[1]()
        else:
            print("Geçersiz seçim. Lütfen menüden bir seçenek girin.")

if __name__ == "__main__":
    main()
