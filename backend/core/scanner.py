# backend/core/scanner.py

import pandas as pd
import logging
import asyncio
from datetime import datetime, timedelta
from core import app_config, agent
from core.trader import open_new_trade, TradeException
from tools.exchange import exchange as global_exchange_instance, get_symbols_from_exchange, get_top_gainers_losers, get_volume_spikes, get_technical_indicators
from tools.utils import _get_unified_symbol
from ccxt.base.errors import ExchangeError, NetworkError

# --- İndikatör Hesaplama Fonksiyonları ---

def calculate_ma_signal(close_prices: pd.Series, short_window: int, long_window: int) -> str:
    """
    Verilen kısa ve uzun vadeli periyotlara göre Hareketli Ortalama Kesişim sinyali üretir.
    
    Args:
        close_prices: Kapanış fiyatlarını içeren pandas Serisi.
        short_window: Kısa vadeli hareketli ortalama periyodu.
        long_window: Uzun vadeli hareketli ortalama periyodu.
        
    Returns:
        'BUY', 'SELL', veya 'NEUTRAL' sinyali.
    """
    if len(close_prices) < long_window:
        return 'NEUTRAL'
        
    ma_short = close_prices.rolling(window=short_window).mean()
    ma_long = close_prices.rolling(window=long_window).mean()
    
    # Son iki periyottaki kesişimi kontrol ediyoruz
    if ma_short.iloc[-1] > ma_long.iloc[-1] and ma_short.iloc[-2] <= ma_long.iloc[-2]:
        return 'BUY'
    elif ma_short.iloc[-1] < ma_long.iloc[-1] and ma_short.iloc[-2] >= ma_long.iloc[-2]:
        return 'SELL'
    else:
        return 'NEUTRAL'

def calculate_rsi_signal(close_prices: pd.Series, period: int, overbought_threshold: int, oversold_threshold: int) -> str:
    """
    Standart RSI (Wilder's Smoothing kullanarak) hesaplar ve sinyal üretir.
    
    Args:
        close_prices: Kapanış fiyatlarını içeren pandas Serisi.
        period: RSI periyodu.
        overbought_threshold: Aşırı alım seviyesi.
        oversold_threshold: Aşırı satım seviyesi.
        
    Returns:
        'BUY', 'SELL', veya 'NEUTRAL' sinyali.
    """
    if len(close_prices) < period + 1:
        return 'NEUTRAL'

    delta = close_prices.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Wilder's Smoothing (EMA'nın bir çeşidi) kullanarak daha doğru bir RSI hesaplaması
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    last_rsi = rsi.iloc[-1]
    
    if last_rsi > overbought_threshold:
        return 'SELL'
    elif last_rsi < oversold_threshold:
        return 'BUY'
    else:
        return 'NEUTRAL'


class Scanner:
    # __init__ metodu artık exchange_instance'ı parametre olarak alıyor
    def __init__(self, exchange_instance):
        self.config = app_config.settings 
        self.exchange = exchange_instance # Parametre olarak gelen exchange_instance kullanılıyor
        self.interval = self.config['PROACTIVE_SCAN_ENTRY_TIMEFRAME']
        self.quote_currency = "USDT" 
        self.symbols = get_symbols_from_exchange(self.exchange, self.quote_currency)

    def scan(self, preset):
        logging.info(f"Starting scan with preset: {preset['name']}")
        
        results = []
        for symbol in self.symbols:
            try:
                df = self.exchange.get_ohlcv(symbol, self.interval)
                
                if df is not None and not df.empty and len(df) > 1:
                    analysis = self.analyze(df, preset)
                    
                    if analysis['signal'] != 'NEUTRAL':
                        result = {
                            'symbol': symbol,
                            'signal': analysis['signal'],
                            'price': df['close'].iloc[-1],
                            'volume': df['volume'].iloc[-1],
                            'timestamp': df.index[-1].isoformat()
                        }
                        results.append(result)
            except (ExchangeError, NetworkError) as e:
                logging.error(f"Error scanning symbol {symbol} due to a network or exchange issue: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"An unexpected error occurred while scanning symbol {symbol}: {e}", exc_info=True)
        
        logging.info(f"Scan finished. Found {len(results)} signals.")
        return results

    def analyze(self, df: pd.DataFrame, preset: dict) -> dict:
        """
        Farklı indikatörlerden gelen sinyalleri birleştirerek nihai bir karar verir.
        Bu fonksiyon artık gelen DataFrame'i değiştirmez (yan etkisi yoktur).
        
        Args:
            df: OHLCV verilerini içeren pandas DataFrame.
            preset: Analiz için kullanılacak ayarları içeren dictionary.
            
        Returns:
            Nihai sinyali içeren bir dictionary.
        """
        signals = []

        # Hareketli Ortalama Sinyali
        if 'ma_short' in preset and 'ma_long' in preset:
            ma_signal = calculate_ma_signal(
                close_prices=df['close'],
                short_window=preset['ma_short'],
                long_window=preset['ma_long']
            )
            if ma_signal != 'NEUTRAL':
                signals.append(ma_signal)

        # RSI Sinyali
        if 'rsi_period' in preset and 'rsi_overbought' in preset and 'rsi_oversold' in preset:
            rsi_signal = calculate_rsi_signal(
                close_prices=df['close'],
                period=preset['rsi_period'],
                overbought_threshold=preset['rsi_overbought'],
                oversold_threshold=preset['rsi_oversold']
            )
            if rsi_signal != 'NEUTRAL':
                signals.append(rsi_signal)
        
        # Sinyalleri birleştirme mantığı
        # Eğer tüm sinyaller aynıysa (örn. hepsi 'BUY'), nihai sinyal odur.
        # Eğer çelişkili sinyaller varsa (örn. bir 'BUY', bir 'SELL'), 'NEUTRAL' döner.
        if not signals:
            final_signal = 'NEUTRAL'
        elif all(s == signals[0] for s in signals):
            final_signal = signals[0]
        else:
            final_signal = 'NEUTRAL' # Çelişkili sinyaller

        return {'signal': final_signal}

# Global scanner instance will now be set by main.py's lifespan
_scanner_instance = None # Bu, lifespan tarafından ayarlanana kadar None kalır

async def _get_scanner_instance():
    # Sadece önceden başlatılmış örneği döndür.
    # None kontrolü ve RuntimeError mantığı main.py'deki lifespan'a taşındı.
    if _scanner_instance is None:
        # Bu durum, lifespan başlatmayı düzgün yaparsa idealde gerçekleşmemelidir.
        # Ancak gerçekleşirse, API çağrısının lifespan tamamlanmadan önce yapıldığı anlamına gelir.
        logging.error("HATA: Tarayıcı örneği lifespan tarafından başlatılmamış. API çok mu erken çağrıldı?")
        raise RuntimeError("Tarayıcı örneği FastAPI başlatma yaşam döngüsü tarafından başlatılmadı.")
    return _scanner_instance

async def execute_single_scan_cycle():
    logging.info("PROAKTİF TARAMA: Tek bir döngü başlatılıyor...")
    
    scanner_obj = await _get_scanner_instance() # Bu çağrı artık başlatılmış bir örnek döndürmeli
    
    all_symbols = set()
    config = app_config.settings

    total_scanned_count = 0
    found_candidates = []
    
    # 1. Beyaz liste (Whitelist) her zaman dahil edilir
    whitelist = config.get('PROACTIVE_SCAN_WHITELIST', [])
    for symbol in whitelist:
        all_symbols.add(_get_unified_symbol(symbol))

    # 2. En Çok Yükselenler/Düşenler (Gainers/Losers)
    if config.get('PROACTIVE_SCAN_USE_GAINERS_LOSERS'):
        top_n = config.get('PROACTIVE_SCAN_TOP_N', 10)
        min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
        gainers_losers = get_top_gainers_losers(top_n, min_volume_usdt)
        for item in gainers_losers:
            all_symbols.add(item['symbol'])

    # 3. Hacim Patlaması (Volume Spike)
    if config.get('PROACTIVE_SCAN_USE_VOLUME_SPIKE'):
        volume_timeframe = config.get('PROACTIVE_SCAN_VOLUME_TIMEFRAME', '1h')
        volume_period = config.get('PROACTIVE_SCAN_VOLUME_PERIOD', 24)
        volume_multiplier = config.get('PROACTIVE_SCAN_VOLUME_MULTIPLIER', 5.0)
        min_volume_usdt = config.get('PROACTIVE_SCAN_MIN_VOLUME_USDT', 1000000)
        volume_spikes = get_volume_spikes(volume_timeframe, volume_period, volume_multiplier, min_volume_usdt)
        for item in volume_spikes:
            all_symbols.add(item['symbol'])

    # 4. Blacklist filtrelemesi
    blacklist = config.get('PROACTIVE_SCAN_BLACKLIST', [])
    # Kara liste filtreleme mantığı düzeltildi
    blacklist_upper = [item.upper() for item in blacklist]
    
    filtered_symbols = []
    for s in all_symbols:
        base_symbol = s.split('/')[0] # 'PEPE/USDT' -> 'PEPE'
        if base_symbol not in blacklist_upper:
            filtered_symbols.append(s)
    
    # Ensure a minimum set of symbols to scan if lists are empty
    if not filtered_symbols:
        logging.warning("Hiçbir sembol taranmayacak. Whitelist/Blacklist ayarlarınızı kontrol edin veya tarama kaynaklarını etkinleştirin.")
        filtered_symbols = ["BTC/USDT", "ETH/USDT"] # Fallback to default popular symbols
        logging.info(f"Varsayılan semboller kullanılıyor: {filtered_symbols}")

    logging.info(f"Tarama için son sembol listesi ({len(filtered_symbols)} adet): {', '.join(filtered_symbols)}")
    total_scanned_count = len(filtered_symbols)

    # 5. Her sembol için paralel olarak analiz yap
    analysis_tasks = []
    entry_timeframe = config.get('PROACTIVE_SCAN_ENTRY_TIMEFRAME', '15m')
    trend_timeframe = config.get('MTA_TREND_TIMEFRAME', '4h') # MTA_TREND_TIMEFRAME app_config'den alınır
    use_mta = config.get('PROACTIVE_SCAN_MTA_ENABLED', True)

    for symbol in filtered_symbols:
        async def analyze_single_symbol(s):
            try:
                # scanner_obj.exchange aracılığıyla OHLCV verisi çekilir
                df = scanner_obj.exchange.fetch_ohlcv(s, entry_timeframe, limit=500)
                if not df:
                    logging.warning(f"{s} için OHLCV verisi bulunamadı, analiz atlanıyor.")
                    return None
                
                df = pd.DataFrame(df, columns=["timestamp", "open", "high", "low", "close", "volume"])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True)
                
                if df.empty or len(df) < 100:
                    logging.warning(f"{s} için yetersiz temizlenmiş OHLCV verisi, analiz atlanıyor.")
                    return None

                # get_technical_indicators.invoke() aracılığıyla teknik göstergeler alınır
                entry_indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{s},{entry_timeframe}"})
                if entry_indicators_result.get("status") != "success":
                    logging.warning(f"{s} ({entry_timeframe}) için teknik veri alınamadı: {entry_indicators_result.get('message')}")
                    return None
                
                current_price = df['close'].iloc[-1]

                final_prompt = ""
                if use_mta:
                    trend_indicators_result = get_technical_indicators.invoke({"symbol_and_timeframe": f"{s},{trend_timeframe}"})
                    if trend_indicators_result.get("status") != "success":
                        logging.warning(f"{s} ({trend_timeframe}) için trend verisi alınamadı: {trend_indicators_result.get('message')}")
                        return None
                    
                    final_prompt = agent.create_mta_analysis_prompt(
                        s, current_price, entry_timeframe, entry_indicators_result["data"],
                        trend_timeframe, trend_indicators_result["data"]
                    )
                else:
                    final_prompt = agent.create_final_analysis_prompt(
                        s, entry_timeframe, current_price, entry_indicators_result["data"]
                    )
                
                # agent.llm.invoke() artık await ile çağrılmıyor
                llm_result = agent.llm.invoke(final_prompt)
                parsed_data = agent.parse_agent_response(llm_result.content)

                if parsed_data and (parsed_data.get('recommendation') == 'AL' or parsed_data.get('recommendation') == 'SAT'):
                    found_candidates.append({
                        "symbol": s,
                        "source": "Proaktif Tarayıcı",
                        "timeframe": entry_timeframe,
                        "indicators": entry_indicators_result["data"],
                        "last_updated": datetime.now().isoformat(),
                        "analysis_result": parsed_data
                    })
                return parsed_data
            except Exception as e:
                logging.error(f"Sembol {s} için tarama sırasında hata: {e}", exc_info=True)
                return None
        analysis_tasks.append(analyze_single_symbol(symbol))

    await asyncio.gather(*analysis_tasks)
    
    # 6. Otomatik işlem onayı
    if config.get('PROACTIVE_SCAN_AUTO_CONFIRM'):
        logging.info("Otomatik onay aktif. Bulunan fırsatlar otomatik olarak işleme alınıyor.")
        for candidate in found_candidates:
            if candidate["analysis_result"] and \
               (candidate["analysis_result"].get("recommendation") == "AL" or \
                candidate["analysis_result"].get("recommendation") == "SAT"):
                
                try:
                    trade_price = candidate["analysis_result"]["data"].get("price")
                    if trade_price:
                        trade_price_float = float(trade_price)
                        open_new_trade(
                            symbol=candidate["symbol"],
                            recommendation=candidate["analysis_result"]["recommendation"],
                            timeframe=candidate["timeframe"],
                            current_price=trade_price_float
                        )
                        logging.info(f"Otomatik işlem açıldı: {candidate['symbol']}")
                    else:
                        logging.warning(f"{candidate['symbol']} için fiyat bilgisi bulunamadı, otomatik işlem atlandı.")

                except TradeException as te:
                    logging.error(f"Otomatik işlem sırasında TradeException: {te}")
                except Exception as e:
                    logging.error(f"Otomatik işlem sırasında beklenmedik hata: {e}", exc_info=True)
            
    logging.info(f"PROAKTİF TARAMA DÖNGÜSÜ TAMAMLANDI. Toplam taranan: {total_scanned_count}, Bulunan fırsat: {len(found_candidates)}")
    
    return {"total_scanned": total_scanned_count, "found_candidates": found_candidates}