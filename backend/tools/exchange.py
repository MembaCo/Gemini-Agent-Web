# backend/tools/exchange.py
# @author: Memba Co.

import os
import ccxt
import time
import pandas as pd
import pandas_ta as ta
import logging
from dotenv import load_dotenv
from langchain.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

from .utils import _get_unified_symbol, _parse_symbol_timeframe_input, str_to_bool

load_dotenv()
exchange = None
indicator_cache = {}
CACHE_TTL_SECONDS = 180

@retry(wait=wait_exponential(multiplier=2, min=4, max=30), stop=stop_after_attempt(3))
def _load_markets_with_retry(exchange_instance):
    logging.info("Borsa piyasa verileri yükleniyor (deneniyor)...")
    return exchange_instance.load_markets()

def initialize_exchange(market_type: str):
    """Borsa bağlantısını başlatır."""
    global exchange
    if exchange:
        return
    use_testnet = str_to_bool(os.getenv("USE_TESTNET", "False"))
    api_key = os.getenv("BINANCE_API_KEY")
    secret_key = os.getenv("BINANCE_SECRET_KEY")
    if not api_key or not secret_key:
        raise ValueError("API anahtarları .env dosyasında bulunamadı!")
    
    config_data = {
        "apiKey": api_key, "secret": secret_key,
        "options": {"defaultType": market_type.lower()},
        "enableRateLimit": True, 'timeout': 30000,
    }

    exchange = ccxt.binance(config_data)
    
    if use_testnet and market_type.lower() == 'future':
        exchange.set_sandbox_mode(True)

    try:
        _load_markets_with_retry(exchange)
        logging.info(f"--- Piyasalar, '{market_type.upper()}' pazarı için başarıyla yüklendi. ---")
    except Exception as e:
        logging.critical(f"'{market_type.upper()}' piyasaları yüklenirken kritik hata: {e}", exc_info=True)
        exchange = None
        raise e

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def _fetch_price_natively(symbol: str) -> float | None:
    """Borsadan anlık fiyatı çeker (yeniden deneme mekanizması ile)."""
    if not exchange: return None
    try:
        request_symbol = symbol
        if exchange.id == 'binance' and exchange.options.get('defaultType') == 'future':
            request_symbol = symbol.replace('/', '')
        ticker = exchange.fetch_ticker(request_symbol)
        return float(ticker["last"]) if ticker and ticker.get("last") is not None else None
    except Exception as e:
        logging.warning(f"{symbol} için fiyat çekilirken yeniden denenecek hata: {e}")
        raise

def get_wallet_balance(quote_currency: str = "USDT") -> dict:
    """Cüzdan bakiyesini alır."""
    from core import app_config
    if not exchange or app_config.settings.get('DEFAULT_MARKET_TYPE') != 'future':
        return {"status": "error", "message": "Bu fonksiyon sadece vadeli işlem modunda çalışır."}
    try:
        balance_data = exchange.fetch_balance()
        total_balance = balance_data.get(quote_currency, {}).get('total', 0.0)
        return {"status": "success", "balance": float(total_balance or 0.0)}
    except Exception as e:
        logging.error(f"Bakiye alınırken hata: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@tool
def get_market_price(symbol: str) -> str:
    """Belirtilen kripto para biriminin anlık piyasa fiyatını alır."""
    if not exchange: return "HATA: Borsa bağlantısı başlatılmamış."
    try:
        price = _fetch_price_natively(_get_unified_symbol(symbol))
        return f"{symbol} için anlık piyasa fiyatı: {price}" if price is not None else f"HATA: {symbol} için fiyat bilgisi alınamadı."
    except Exception as e:
        return f"HATA: Fiyat alınamadı. Sembol: '{symbol}'. Hata: {e}"

@tool
def get_technical_indicators(symbol_and_timeframe: str) -> dict:
    """
    Belirtilen sembol ve zaman aralığı için teknik göstergeleri hesaplar.
    """
    now = time.time()
    if symbol_and_timeframe in indicator_cache:
        cached_result, timestamp = indicator_cache[symbol_and_timeframe]
        if (now - timestamp) < CACHE_TTL_SECONDS:
            return cached_result

    if not exchange:
        return {"status": "error", "message": "Borsa bağlantısı başlatılmamış."}
    
    symbol, timeframe = _parse_symbol_timeframe_input(symbol_and_timeframe)
    
    request_symbol = symbol
    if exchange.id == 'binance' and exchange.options.get('defaultType') == 'future':
        request_symbol = symbol.replace('/', '')

    try:
        bars = exchange.fetch_ohlcv(request_symbol, timeframe=timeframe, limit=500)
        if not bars:
            return {"status": "error", "message": f"Geçmiş veri bulunamadı: {symbol}."}
        
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        required_data_points = 100 
        if len(df) < required_data_points:
            return {"status": "error", "message": f"Teknik analiz için yetersiz veri: {len(df)}/{required_data_points} mum çubuğu bulundu."}
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True)
        
        if len(df) < required_data_points:
            return {"status": "error", "message": f"Veri temizliğinden sonra yetersiz veri: {len(df)}/{required_data_points} mum çubuğu kaldı."}

        df.ta.rsi(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df.dropna(inplace=True)

        if df.empty:
            logging.warning(f"İndikatör hesaplaması sonrası tüm veriler NaN içerdiği için atıldı. Sembol: {symbol}, Zaman Aralığı: {timeframe}")
            return {"status": "error", "message": f"Hesaplama sonrası geçerli veri kalmadı. Sembol: {symbol}"}

        last = df.iloc[-1]
        rsi_val = last.get('RSI_14')
        adx_val = last.get('ADX_14')

        if rsi_val is None or pd.isna(rsi_val) or adx_val is None or pd.isna(adx_val):
            logging.warning(f"İndikatör hesaplaması sonrası geçersiz değerler. RSI: {rsi_val}, ADX: {adx_val}. Sembol: {symbol}")
            return {"status": "error", "message": f"Hesaplama sonrası geçersiz gösterge değeri. Sembol: {symbol}"}

        indicators = {"RSI": float(rsi_val), "ADX": float(adx_val)}
        result = {"status": "success", "data": indicators}
        indicator_cache[symbol_and_timeframe] = (result, now)
        return result
        
    except Exception as e:
        logging.error(f"Teknik gösterge alınırken genel hata ({symbol}): {e}", exc_info=True)
        return {"status": "error", "message": f"Beklenmedik bir hata oluştu: {str(e)}"}

def execute_trade_order(symbol: str, side: str, amount: float, price: float = None, stop_loss: float = None, take_profit: float = None, leverage: float = None) -> dict:
    """İşlem emri gönderir."""
    from core import app_config
    if not exchange: 
        return {"status": "error", "message": "Borsa bağlantısı başlatılmamış."}
    
    unified_symbol = _get_unified_symbol(symbol)
    request_symbol = unified_symbol.replace('/', '') if exchange.id == 'binance' and exchange.options.get('defaultType') == 'future' else unified_symbol

    try:
        formatted_amount = exchange.amount_to_precision(request_symbol, amount)
        formatted_price = exchange.price_to_precision(request_symbol, price) if price is not None else None
        
        if not app_config.settings.get('LIVE_TRADING'):
            sim_price = price or _fetch_price_natively(unified_symbol)
            return {"status": "success", "message": f"Simülasyon emri başarılı: {side} {formatted_amount} {unified_symbol}", "fill_price": sim_price}

        is_futures_market = exchange.options.get('defaultType') == 'future'
        
        if leverage and is_futures_market:
            logging.info(f"{request_symbol} için kaldıraç ayarlanıyor: {leverage}x")
            exchange.set_leverage(int(leverage), request_symbol)
        elif leverage:
            logging.warning(f"Kaldıraç ayarlama atlandı. Piyasa tipi 'future' değil, mevcut tip: {exchange.options.get('defaultType')}")
        
        order_type = app_config.settings.get('DEFAULT_ORDER_TYPE', 'LIMIT').lower()
        order = None
        
        if order_type == 'limit' and formatted_price:
            order = exchange.create_limit_order(request_symbol, side, float(formatted_amount), float(formatted_price))
        else:
            order = exchange.create_market_order(request_symbol, side, float(formatted_amount))
            
        fill_price = order.get('average') or order.get('price')
        if not fill_price:
            time.sleep(1)
            trades = exchange.fetch_my_trades(request_symbol, limit=1)
            fill_price = trades[0]['price'] if trades else _fetch_price_natively(unified_symbol)
            
        if stop_loss and take_profit and is_futures_market:
            opposite = 'sell' if side == 'buy' else 'buy'
            time.sleep(0.5)
            try: 
                exchange.create_order(request_symbol, 'STOP_MARKET', opposite, float(formatted_amount), None, {'stopPrice': stop_loss, 'reduceOnly': True})
            except Exception as sl_e: 
                logging.error(f"SL emri gönderilemedi ({request_symbol}): {sl_e}")
            try: 
                exchange.create_order(request_symbol, 'TAKE_PROFIT_MARKET', opposite, float(formatted_amount), None, {'stopPrice': take_profit, 'reduceOnly': True})
            except Exception as tp_e: 
                logging.error(f"TP emri gönderilemedi ({request_symbol}): {tp_e}")
            
        return {"status": "success", "message": f"İşlem emri ({side} {formatted_amount} {unified_symbol}) başarıyla gönderildi.", "fill_price": fill_price}
    except Exception as e:
        logging.error(f"İşlem sırasında hata ({unified_symbol}): {e}", exc_info=True)
        error_message = f"HATA ({unified_symbol}): {str(e)}"
        if isinstance(e, ccxt.NotSupported):
            error_message = f"HATA ({unified_symbol}): Borsa tarafından desteklenmeyen işlem. Piyasa tipini (Spot/Vadeli) kontrol edin."
        return {"status": "error", "message": error_message}

def get_symbols_from_exchange(exchange_instance, quote_currency: str) -> list:
    if not exchange_instance:
        logging.error("Borsa bağlantısı başlatılmadığı için semboller alınamıyor.")
        return []
    try:
        markets = exchange_instance.load_markets()
        symbols = []
        for market_id, market_info in markets.items():
            if market_info.get('active', False) and market_info.get('quote') == quote_currency.upper() and market_info.get('type') == exchange_instance.options.get('defaultType'):
                symbols.append(market_info['symbol'])
        logging.info(f"{quote_currency} cinsinden {len(symbols)} adet {exchange_instance.options.get('defaultType')} sembolü borsadan çekildi.")
        return symbols
    except Exception as e:
        logging.error(f"Borsadan semboller alınırken hata oluştu: {e}", exc_info=True)
        return []

def get_volume_spikes(timeframe: str, period: int, multiplier: float, min_volume_usdt: int) -> list:
    from core import app_config
    if not exchange or app_config.settings.get('DEFAULT_MARKET_TYPE') != 'future': return []
    logging.info(f"Hacim patlaması taraması başlatıldı: Zaman Aralığı={timeframe}, Periyot={period}, Çarpan={multiplier}")
    try:
        all_tickers = exchange.fapiPublicGetTicker24hr()
        filtered_tickers = [t for t in all_tickers if t.get('symbol', '').endswith('USDT') and float(t.get('quoteVolume', 0)) > min_volume_usdt]
        logging.info(f"Hacim analizi için {len(filtered_tickers)} adet sembol ön filtreden geçti.")
        volume_spikes = []
        for ticker in filtered_tickers:
            symbol = ticker['symbol']
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=period + 1)
                if len(bars) < period + 1: continue
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                df.dropna(subset=['volume'], inplace=True)
                if len(df) < period + 1: continue
                last_volume = df['volume'].iloc[-1]
                average_volume = df['volume'].iloc[-period-1:-1].mean()
                if pd.isna(last_volume) or pd.isna(average_volume) or average_volume == 0: continue
                if last_volume > average_volume * multiplier:
                    spike_info = {"symbol": _get_unified_symbol(symbol), "spike_ratio": last_volume / average_volume, "last_volume": last_volume, "average_volume": average_volume}
                    volume_spikes.append(spike_info)
                time.sleep(exchange.rateLimit / 1000)
            except Exception as e:
                logging.warning(f"{symbol} için hacim analizi sırasında hata: {e}")
                continue
        volume_spikes.sort(key=lambda x: x['spike_ratio'], reverse=True)
        return volume_spikes
    except Exception as e:
        logging.error(f"Hacim patlaması listesi alınırken genel hata: {e}", exc_info=True)
        return []

def get_atr_value(symbol_and_timeframe: str) -> dict:
    if not exchange: return {"status": "error", "message": "Borsa bağlantısı başlatılmamış."}
    try:
        symbol, timeframe = _parse_symbol_timeframe_input(symbol_and_timeframe)
        request_symbol = symbol.replace('/', '') if exchange.id == 'binance' and exchange.options.get('defaultType') == 'future' else symbol
        bars = exchange.fetch_ohlcv(request_symbol, timeframe=timeframe, limit=200)
        if not bars or len(bars) < 20: return {"status": "error", "message": "Yetersiz veri"}
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        atr = df.ta.atr()
        if atr is None or atr.empty: return {"status": "error", "message": "ATR hesaplanamadı."}
        last_atr = atr.iloc[-1]
        if pd.isna(last_atr): return {"status": "error", "message": "ATR değeri NaN"}
        return {"status": "success", "value": last_atr}
    except Exception as e:
        logging.error(f"ATR alınırken hata: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

def get_top_gainers_losers(top_n: int, min_volume_usdt: int) -> list:
    from core import app_config
    if not exchange or app_config.settings.get('DEFAULT_MARKET_TYPE') != 'future': return []
    try:
        tickers = exchange.fapiPublicGetTicker24hr()
        filtered = [t for t in tickers if t.get('symbol', '').endswith('USDT') and float(t.get('quoteVolume', 0)) > min_volume_usdt]
        filtered.sort(key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
        gainers = filtered[:top_n]
        losers = filtered[-top_n:]
        return [{**item, 'symbol': _get_unified_symbol(item['symbol'])} for item in (gainers + losers)]
    except Exception as e:
        logging.error(f"Gainer/Loser listesi alınırken hata: {e}", exc_info=True)
        return []

def get_open_positions_from_exchange() -> list:
    from core import app_config
    if not exchange or app_config.settings.get('DEFAULT_MARKET_TYPE') != 'future': return []
    try:
        positions = exchange.fetch_positions(params={'type': app_config.settings.get('DEFAULT_MARKET_TYPE')})
        return [p for p in positions if p.get('contracts') and float(p['contracts']) != 0]
    except Exception as e:
        logging.error(f"Borsadan pozisyonlar alınırken hata: {e}", exc_info=True)
        return []

def update_stop_loss_order(symbol: str, side: str, amount: float, new_stop_price: float) -> str:
    from core import app_config
    if not exchange: return "HATA: Borsa bağlantısı başlatılmamış."
    if not app_config.settings.get('LIVE_TRADING'):
        return f"Simülasyon: {symbol} için SL emri {new_stop_price} olarak güncellendi."
    if exchange.options.get('defaultType') != 'future':
        return f"Hata: SL güncelleme sadece vadeli piyasada desteklenir."
    
    unified_symbol = _get_unified_symbol(symbol)
    request_symbol = unified_symbol.replace('/', '') if exchange.id == 'binance' else unified_symbol

    try:
        open_orders = exchange.fetch_open_orders(request_symbol)
        stop_orders_to_cancel = [o for o in open_orders if 'stop' in o.get('type','').lower() and o.get('reduceOnly')]
        for order in stop_orders_to_cancel:
            exchange.cancel_order(order['id'], request_symbol)
        
        time.sleep(0.5)
        opposite_side = 'sell' if side == 'buy' else 'buy'
        
        if new_stop_price > 0:
            params_sl = {'stopPrice': new_stop_price, 'reduceOnly': True}
            exchange.create_order(request_symbol, 'STOP_MARKET', opposite_side, amount, None, params_sl)
            return f"Başarılı: {unified_symbol} için yeni SL emri {new_stop_price} olarak oluşturuldu."
        else:
            return "Hata: Geçersiz yeni stop-loss fiyatı."
    except Exception as e:
        logging.error(f"HATA: SL güncellenemedi. Detay: {e}", exc_info=True)
        return f"HATA: SL güncellenemedi. Detay: {e}"

def cancel_all_open_orders(symbol: str) -> str:
    from core import app_config
    if not exchange: return "HATA: Borsa bağlantısı başlatılmamış."
    if not app_config.settings.get('LIVE_TRADING'):
        return f"Simülasyon: {symbol} için tüm açık emirler iptal edildi."
    
    unified_symbol = _get_unified_symbol(symbol)
    request_symbol = unified_symbol.replace('/', '') if exchange.id == 'binance' and exchange.options.get('defaultType') == 'future' else unified_symbol

    try:
        exchange.cancel_all_orders(request_symbol)
        logging.info(f"İPTAL: {unified_symbol} için tüm açık emirler başarıyla iptal edildi.")
        return f"Başarılı: {unified_symbol} için tüm açık emirler iptal edildi."
    except Exception as e:
        logging.error(f"HATA: {unified_symbol} için açık emirler iptal edilemedi. Detay: {e}", exc_info=True)
        return f"HATA: {unified_symbol} için emirler iptal edilemedi."
