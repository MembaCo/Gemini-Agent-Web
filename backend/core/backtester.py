# ==============================================================================
# File: backend/core/backtester.py
# @author: Memba Co.
# ==============================================================================
import logging
import pandas as pd
from datetime import datetime, timedelta

from tools import exchange as exchange_tools, get_technical_indicators
from core import agent as core_agent
# DEĞİŞTİRİLDİ: 'settings' nesnesini doğrudan import etmek yerine, tüm modülü import ediyoruz.
# Bu, her zaman en güncel ayarlara erişmemizi sağlar.
from core import app_config

class Backtester:
    """
    Bir ticaret stratejisini geçmiş veriler üzerinde simüle eder ve performans
    raporu oluşturur.
    """
    def __init__(self, symbol: str, timeframe: str, start_date: str, end_date: str, initial_balance: float, strategy_settings: dict):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        
        # DEĞİŞTİRİLDİ: Strateji ayarlarını alırken, doğrudan app_config.settings'e başvuruyoruz.
        # Bu, uygulama başladığında yüklenen dolu sözlüğe erişmemizi garanti eder.
        self.strategy = strategy_settings if strategy_settings is not None else app_config.settings

        # Simülasyon durumu
        self.balance = initial_balance
        self.position = None  # Sadece tek pozisyon yönetir
        self.history = []
        
        # HATA DÜZELTME: Strateji sözlüğünün dolu olduğundan emin olduktan sonra loglama yapılıyor.
        if 'RISK_PER_TRADE_PERCENT' not in self.strategy:
             raise ValueError("Strateji ayarları yüklenemedi veya 'RISK_PER_TRADE_PERCENT' anahtarı eksik.")
        
        logging.info(f"Backtester başlatıldı: {symbol} ({timeframe}) / Strateji: {self.strategy['RISK_PER_TRADE_PERCENT']}% Risk")

    def _get_historical_data(self):
        """CCXT kullanarak geçmiş OHLCV verilerini çeker."""
        logging.info(f"{self.symbol} için {self.start_date} - {self.end_date} arası geçmiş veriler çekiliyor...")
        start_ts = int(datetime.strptime(self.start_date, '%Y-%m-%d').timestamp() * 1000)
        end_date_dt = datetime.strptime(self.end_date, '%Y-%m-%d') + timedelta(days=1)
        
        all_bars = []
        limit = 1000 
        
        while start_ts < int(end_date_dt.timestamp() * 1000):
            try:
                bars = exchange_tools.exchange.fetch_ohlcv(self.symbol, self.timeframe, since=start_ts, limit=limit)
                if not bars:
                    break
                all_bars.extend(bars)
                start_ts = bars[-1][0] + 1
            except Exception as e:
                logging.error(f"Geçmiş veri çekilirken hata: {e}")
                break
        
        if not all_bars:
            raise ValueError("Belirtilen tarih aralığı için veri bulunamadı.")

        df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df[df.index <= end_date_dt]
        return df

    def _calculate_indicators(self, df: pd.DataFrame):
        """Verilen DataFrame'e strateji için gerekli indikatörleri ekler."""
        df.ta.rsi(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.atr(length=14, append=True)
        return df.dropna()

    def run(self):
        """Backtest simülasyonunu başlatır ve çalıştırır."""
        historical_data = self._get_historical_data()
        data_with_indicators = self._calculate_indicators(historical_data)
        
        logging.info(f"{len(data_with_indicators)} mum çubuğu üzerinde simülasyon başlatılıyor...")

        for index, row in data_with_indicators.iterrows():
            current_price = row['close']
            
            if self.position:
                close_reason = None
                if self.position['side'] == 'buy':
                    if row['low'] <= self.position['stop_loss']: close_reason = "SL"
                    elif row['high'] >= self.position['take_profit']: close_reason = "TP"
                elif self.position['side'] == 'sell':
                    if row['high'] >= self.position['stop_loss']: close_reason = "SL"
                    elif row['low'] <= self.position['take_profit']: close_reason = "TP"
                
                if close_reason:
                    self._close_position(close_reason, row)
                    
            if not self.position:
                if row['ADX_14'] > 20:
                    if row['RSI_14'] < 35 and row['MACD_12_26_9'] > row['MACDs_12_26_9']:
                        self._open_position('buy', row)
                    elif row['RSI_14'] > 65 and row['MACD_12_26_9'] < row['MACDs_12_26_9']:
                         self._open_position('sell', row)

        return self._generate_report()

    def _open_position(self, side: str, candle_data: pd.Series):
        """Sanal bir pozisyon açar."""
        entry_price = candle_data['close']
        atr_value = candle_data['ATRr_14']
        
        sl_distance = atr_value * self.strategy['ATR_MULTIPLIER_SL']
        tp_distance = sl_distance * self.strategy['RISK_REWARD_RATIO_TP']
        
        if side == 'buy':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else: # sell
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
            
        risk_per_trade = self.balance * (self.strategy['RISK_PER_TRADE_PERCENT'] / 100)
        amount = risk_per_trade / sl_distance
        
        self.position = {
            "symbol": self.symbol,
            "side": side,
            "amount": amount,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "opened_at": candle_data.name
        }
        logging.info(f"SANAL POZİSYON AÇILDI: {side} {self.symbol} @ {entry_price:.4f} | Tarih: {candle_data.name.date()}")

    def _close_position(self, reason: str, candle_data: pd.Series):
        """Sanal pozisyonu kapatır ve geçmişe kaydeder."""
        close_price = self.position['stop_loss'] if reason == 'SL' else self.position['take_profit']
        
        pnl = 0
        if self.position['side'] == 'buy':
            pnl = (close_price - self.position['entry_price']) * self.position['amount']
        else:
            pnl = (self.position['entry_price'] - close_price) * self.position['amount']
        
        self.balance += pnl
        
        trade_log = {
            "symbol": self.symbol,
            "side": self.position['side'],
            "entry_price": self.position['entry_price'],
            "close_price": close_price,
            "pnl": pnl,
            "status": reason,
            "opened_at": self.position['opened_at'].strftime('%Y-%m-%d %H:%M:%S'),
            "closed_at": candle_data.name.strftime('%Y-%m-%d %H:%M:%S'),
            "id": len(self.history) + 1
        }
        self.history.append(trade_log)
        logging.info(f"SANAL POZİSYON KAPANDI: {reason} | PNL: {pnl:+.2f} USDT | Yeni Bakiye: {self.balance:.2f} USDT")
        self.position = None

    def _generate_report(self):
        """Simülasyon sonunda performans raporu oluşturur."""
        total_pnl = self.balance - self.initial_balance
        total_trades = len(self.history)
        winning_trades = sum(1 for t in self.history if t['pnl'] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        cumulative_pnl = 0
        chart_points = [{'x': self.start_date, 'y': 0}]
        for trade in sorted(self.history, key=lambda x: x['closed_at']):
            cumulative_pnl += trade['pnl']
            chart_points.append({'x': trade['closed_at'].split(' ')[0], 'y': round(cumulative_pnl, 2)})

        return {
            "stats": {
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades
            },
            "chart_data": {"points": chart_points},
            "trade_history": self.history
        }
