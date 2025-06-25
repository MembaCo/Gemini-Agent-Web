# backend/core/scanner.py

import pandas as pd
from tools.exchange import Exchange
from tools.utils import get_config, log, get_symbols_from_exchange
from datetime import datetime, timedelta
# ccxt kütüphanesinden olası hataları yakalamak için import edelim
from ccxt.base.errors import ExchangeError, NetworkError

# --- İndikatör Hesaplama Fonksiyonları ---
# Analiz mantığını daha modüler hale getirmek için indikatör hesaplamalarını
# kendi fonksiyonlarına ayırıyoruz.

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
    def __init__(self):
        self.config = get_config()
        self.exchange_name = self.config['exchange']['name']
        self.exchange = Exchange(self.exchange_name)
        self.interval = self.config['scanner']['interval']
        self.quote_currency = self.config['scanner']['quote_currency']
        self.symbols = get_symbols_from_exchange(self.exchange, self.quote_currency)

    def scan(self, preset):
        log(f"Starting scan with preset: {preset['name']}")
        
        results = []
        for symbol in self.symbols:
            try:
                # OHLCV verisini borsadan çekiyoruz
                df = self.exchange.get_ohlcv(symbol, self.interval)
                
                # Veri çerçevesinin boş veya yetersiz olmadığını kontrol ediyoruz
                if df is not None and not df.empty and len(df) > 1:
                    # Analiz fonksiyonunu çağırıyoruz
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
            # Daha spesifik hataları yakalayarak daha anlamlı loglar üretiyoruz
            except (ExchangeError, NetworkError) as e:
                log(f"Error scanning symbol {symbol} due to a network or exchange issue: {e}", level='error')
            except Exception as e:
                log(f"An unexpected error occurred while scanning symbol {symbol}: {e}", level='error')
        
        log(f"Scan finished. Found {len(results)} signals.")
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