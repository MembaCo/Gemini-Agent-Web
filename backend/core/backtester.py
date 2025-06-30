# backend/core/backtester.py

import pandas as pd
import numpy as np
import logging
import time
import pandas_ta as ta # pandas-ta kütüphanesi eklendi
from tools import exchange as exchange_tools

class Backtester:
    def __init__(self, initial_balance: float, preset: dict):
        self.preset = preset
        self.exchange = exchange_tools.exchange
        self.initial_balance = initial_balance
        self.position_size_percent = self.preset.get('RISK_PER_TRADE_PERCENT', 1.0)
        self.trading_fee_percent = self.preset.get('trading_fee_percent', 0.1)
        
        if not self.exchange:
            raise ConnectionError("Backtester başlatılamadı: Borsa bağlantısı mevcut değil. Sunucu başlangıç loglarını kontrol edin.")

    def _fetch_historical_data(self, symbol, interval, start_date, end_date):
        """Tüm tarih aralığını kapsayacak şekilde geçmiş OHLCV verilerini bir döngü içinde çeker."""
        try:
            since = self.exchange.parse8601(f"{start_date}T00:00:00Z")
            end_ts = self.exchange.parse8601(f"{end_date}T23:59:59Z")
            all_bars = []
            
            logging.info(f"{symbol} için {start_date} ve {end_date} arası geçmiş veriler çekiliyor...")
            
            while since < end_ts:
                bars = self.exchange.fetch_ohlcv(symbol, timeframe=interval, since=since, limit=500)
                if not bars:
                    break
                all_bars.extend(bars)
                since = bars[-1][0] + 1 
                time.sleep(self.exchange.rateLimit / 1000)

            if not all_bars:
                return None
                
            df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date).replace(hour=23, minute=59, second=59)
            df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)].set_index('timestamp')
            
            logging.info(f"{len(df)} adet mum verisi başarıyla çekildi ve işlendi.")
            return df
        except Exception as e:
            logging.error(f"{symbol} için geçmiş veri çekilirken hata: {e}", exc_info=True)
            return None

    def run(self, symbol, interval, start_date, end_date):
        logging.info(f"Backtest başlatılıyor: {symbol}, {start_date} - {end_date}")

        df = self._fetch_historical_data(symbol, interval, start_date, end_date)
        if df is None or df.empty:
            logging.warning(f"{symbol} için belirtilen periyotta veri bulunamadı.")
            return {"message": f"{symbol} için belirtilen periyotta veri bulunamadı."}

        signals = self._generate_signals(df)
        df['signal'] = signals

        results = self._simulate_trades(df, symbol)
        final_results = self._calculate_performance_metrics(results, symbol, start_date, end_date, interval)

        logging.info(f"Backtest tamamlandı. Son Bakiye: {final_results.get('stats', {}).get('final_balance', 0):.2f}")
        return final_results

    def _generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Tüm DataFrame için vektörel olarak sinyal üretir.
        NOT: Bu fonksiyon, scanner'daki tekil sinyal üreten fonksiyonlardan farklıdır.
        """
        signals = pd.Series('NEUTRAL', index=df.index, name="signals")

        # Hareketli Ortalama Kesişim Stratejisi
        if self.preset.get('ma_short') and self.preset.get('ma_long'):
            short_window = self.preset['ma_short']
            long_window = self.preset['ma_long']
            
            ma_short = df.ta.sma(length=short_window)
            ma_long = df.ta.sma(length=long_window)
            
            # Golden Cross (Al Sinyali)
            buy_signals = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
            signals.loc[buy_signals] = 'BUY'
            
            # Death Cross (Sat Sinyali)
            sell_signals = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
            signals.loc[sell_signals] = 'SELL'

        # RSI Stratejisi (MA sinyallerinin üzerine yazabilir)
        if self.preset.get('rsi_period'):
            rsi_period = self.preset['rsi_period']
            rsi_overbought = self.preset.get('rsi_overbought', 70)
            rsi_oversold = self.preset.get('rsi_oversold', 30)

            rsi = df.ta.rsi(length=rsi_period)
            if rsi is not None:
                # RSI Aşırı Satım (Al Sinyali)
                signals.loc[rsi < rsi_oversold] = 'BUY'
                # RSI Aşırı Alım (Sat Sinyali)
                signals.loc[rsi > rsi_overbought] = 'SELL'

        # İleriye dönük bakma hatasını (lookahead bias) önlemek için sinyalleri bir bar kaydır.
        return signals.shift(1).fillna('NEUTRAL')


    def _simulate_trades(self, df: pd.DataFrame, symbol: str) -> dict:
        balance = self.initial_balance
        position = 0
        trades = []
        balance_history = []

        for timestamp, row in df.iterrows():
            current_price = row['open']

            if position == 0 and row['signal'] == 'BUY':
                investment_amount = balance * (self.position_size_percent / 100.0)
                fee = investment_amount * (self.trading_fee_percent / 100.0)
                position = (investment_amount - fee) / current_price
                balance -= investment_amount
                trades.append({'symbol': symbol, 'type': 'BUY', 'price': current_price, 'amount': position, 'timestamp': timestamp.isoformat()})
            elif position > 0 and row['signal'] == 'SELL':
                revenue = position * current_price
                fee = revenue * (self.trading_fee_percent / 100.0)
                balance += (revenue - fee)
                trades.append({'symbol': symbol, 'type': 'SELL', 'price': current_price, 'amount': position, 'timestamp': timestamp.isoformat()})
                position = 0

            portfolio_value = balance + (position * current_price)
            balance_history.append({'timestamp': timestamp, 'value': portfolio_value})
        
        return {'trades': trades, 'balance_history': pd.DataFrame(balance_history).set_index('timestamp')}

    def _calculate_performance_metrics(self, sim_results: dict, symbol, start_date, end_date, interval: str) -> dict:
        trades = sim_results['trades']
        balance_history = sim_results['balance_history']['value']
        
        if not trades:
            return {'message': 'Test süresince hiç işlem yapılmadı.'}

        final_balance = balance_history.iloc[-1]
        total_pnl = final_balance - self.initial_balance
        total_pnl_percent = (total_pnl / self.initial_balance) * 100
        
        trade_pairs = []
        for i in range(0, len(trades) - 1, 2):
            if trades[i]['type'] == 'BUY' and trades[i+1]['type'] == 'SELL':
                entry_trade = trades[i]
                exit_trade = trades[i+1]
                pnl = (exit_trade['price'] - entry_trade['price']) * entry_trade['amount']
                trade_pairs.append({'entry': entry_trade, 'exit': exit_trade, 'pnl': pnl})
        
        total_trades = len(trade_pairs)
        winning_trades = len([p for p in trade_pairs if p['pnl'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        peak = balance_history.expanding(min_periods=1).max()
        drawdown = (balance_history - peak) / peak
        max_drawdown = drawdown.min() * 100 if not drawdown.empty else 0

        daily_returns = balance_history.resample('D').last().pct_change().dropna()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() > 0 else 0

        trade_history_list = [{
            "id": p['entry']['timestamp'], "symbol": symbol, "side": "buy",
            "amount": p['entry']['amount'], "entry_price": p['entry']['price'],
            "close_price": p['exit']['price'], "pnl": p.get('pnl', 0),
            "status": "CLOSED", "opened_at": p['entry']['timestamp'],
            "closed_at": p['exit']['timestamp'], "timeframe": interval
        } for p in trade_pairs]

        return {
            'stats': {
                'total_pnl': total_pnl,
                'total_pnl_percent': total_pnl_percent,
                'win_rate': win_rate, 
                'winning_trades': winning_trades,
                'losing_trades': losing_trades, 
                'total_trades': total_trades,
                'profit_factor': (sum(p['pnl'] for p in trade_pairs if p['pnl'] > 0) / abs(sum(p['pnl'] for p in trade_pairs if p['pnl'] < 0))) if losing_trades > 0 and sum(p['pnl'] for p in trade_pairs if p['pnl'] < 0) != 0 else float('inf'),
                'max_drawdown_percent': max_drawdown, 
                'sharpe_ratio': sharpe_ratio,
                'final_balance': final_balance
            },
            'trade_history': trade_history_list,
            'balance_history': balance_history.to_dict()
        }