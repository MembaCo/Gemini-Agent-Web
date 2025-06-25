# backend/core/backtester.py

import pandas as pd
import numpy as np
from tools.exchange import Exchange
from tools.utils import get_config, log
# Scanner sınıfı yerine, doğrudan modüler hale getirdiğimiz analiz fonksiyonlarını import ediyoruz.
from .scanner import calculate_ma_signal, calculate_rsi_signal

class Backtester:
    def __init__(self):
        self.config = get_config()
        self.exchange_name = self.config['exchange']['name']
        self.exchange = Exchange(self.exchange_name)
        # Yapılandırmadan backtest'e özel ayarları alıyoruz.
        self.backtest_config = self.config['backtester']
        self.initial_balance = self.backtest_config['initial_balance']
        # Pozisyon büyüklüğü ve işlem komisyonu gibi daha gerçekçi parametreler ekliyoruz.
        self.position_size_percent = self.backtest_config.get('position_size_percent', 1.0) # Kasanın %100'ü varsayılan
        self.trading_fee_percent = self.backtest_config.get('trading_fee_percent', 0.1) # %0.1 komisyon varsayılan

    def run(self, symbol, interval, start_date, end_date, preset):
        log(f"Starting backtest for {symbol} from {start_date} to {end_date}")

        # 1. Veri Hazırlama ve Sinyal Üretimi (Vektörel Yaklaşım)
        df = self.exchange.get_ohlcv(symbol, interval, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            log("No data found for the given period.", level='error')
            return None

        # Tüm periyot için sinyalleri tek seferde, döngü olmadan hesaplıyoruz.
        # Bu, performansı binlerce kat artırır ve lookahead bias riskini ortadan kaldırır.
        signals = self._generate_signals(df, preset)
        df['signal'] = signals

        # 2. İşlem Simülasyonu
        results = self._simulate_trades(df, symbol)

        # 3. Performans Metriklerini Hesaplama
        final_results = self._calculate_performance_metrics(results, symbol, start_date, end_date)

        log(f"Backtest finished. Final Balance: {final_results['final_balance']:.2f}, Total PnL: {final_results['total_pnl_percent']:.2%}")
        return final_results

    def _generate_signals(self, df: pd.DataFrame, preset: dict) -> pd.Series:
        """Tüm veri çerçevesi için al/sat sinyallerini vektörel olarak üretir."""
        final_signals = pd.Series('NEUTRAL', index=df.index)
        
        # Stratejileri birleştirme mantığı. Şimdilik ilk geçerli sinyali alıyoruz.
        # Bu kısım daha karmaşık stratejiler için geliştirilebilir.
        if 'ma_short' in preset and 'ma_long' in preset:
            ma_signals = pd.Series(calculate_ma_signal(df['close'], preset['ma_short'], preset['ma_long']), index=df.index)
            final_signals[ma_signals != 'NEUTRAL'] = ma_signals

        if 'rsi_period' in preset:
            rsi_signals = pd.Series(calculate_rsi_signal(df['close'], preset['rsi_period'], preset['rsi_overbought'], preset['rsi_oversold']), index=df.index)
            final_signals[rsi_signals != 'NEUTRAL'] = rsi_signals

        # Sinyallerin bir sonraki mumda işleme girmesi için bir periyot kaydırıyoruz (önemli!).
        # Bu, sinyalin geldiği mumun kapanış fiyatından işlem yapmayı garantiler.
        return final_signals.shift(1).fillna('NEUTRAL')

    def _simulate_trades(self, df: pd.DataFrame, symbol: str) -> dict:
        """Hesaplanmış sinyallere göre işlemleri simüle eder."""
        balance = self.initial_balance
        position = 0  # Tutulan base currency miktarı
        trades = []
        balance_history = []

        for timestamp, row in df.iterrows():
            current_price = row['open'] # Bir sonraki mumun açılış fiyatından işlem yapıyoruz

            # Pozisyonda değilsek ve AL sinyali geldiyse
            if position == 0 and row['signal'] == 'BUY':
                investment_amount = balance * (self.position_size_percent / 100.0)
                fee = investment_amount * (self.trading_fee_percent / 100.0)
                position = (investment_amount - fee) / current_price
                balance -= investment_amount
                trades.append({'symbol': symbol, 'type': 'BUY', 'price': current_price, 'amount': position, 'timestamp': timestamp.isoformat()})

            # Pozisyondaysak ve SAT sinyali geldiyse
            elif position > 0 and row['signal'] == 'SELL':
                revenue = position * current_price
                fee = revenue * (self.trading_fee_percent / 100.0)
                balance += (revenue - fee)
                trades.append({'symbol': symbol, 'type': 'SELL', 'price': current_price, 'amount': position, 'timestamp': timestamp.isoformat()})
                position = 0

            # Her günün sonunda portföy değerini kaydet
            portfolio_value = balance + (position * current_price)
            balance_history.append({'timestamp': timestamp, 'value': portfolio_value})
        
        return {'trades': trades, 'balance_history': pd.DataFrame(balance_history).set_index('timestamp')}

    def _calculate_performance_metrics(self, sim_results: dict, symbol, start_date, end_date) -> dict:
        """Simülasyon sonuçlarından detaylı performans metrikleri hesaplar."""
        trades = sim_results['trades']
        balance_history = sim_results['balance_history']['value']
        
        if not trades:
            return {'message': 'No trades were executed.'}

        final_balance = balance_history.iloc[-1]
        total_pnl_percent = ((final_balance / self.initial_balance) - 1) * 100
        
        trade_pairs = []
        for i in range(0, len(trades), 2):
            if i + 1 < len(trades) and trades[i]['type'] == 'BUY' and trades[i+1]['type'] == 'SELL':
                entry_trade = trades[i]
                exit_trade = trades[i+1]
                pnl = ((exit_trade['price'] / entry_trade['price']) - 1) * 100
                trade_pairs.append({'entry': entry_trade, 'exit': exit_trade, 'pnl': pnl})
        
        total_trades = len(trade_pairs)
        winning_trades = len([p for p in trade_pairs if p['pnl'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # Max Drawdown Hesaplaması
        peak = balance_history.expanding(min_periods=1).max()
        drawdown = (balance_history - peak) / peak
        max_drawdown = drawdown.min() * 100

        # Sharpe Oranı Hesaplaması (Yıllık bazda, risksiz faiz oranı 0 varsayılarak)
        daily_returns = balance_history.pct_change().dropna()
        # Günlük getirilerin oynaklığı çok yüksek olabileceğinden, periyoda göre ayarlama yapmak gerekebilir.
        # Basitlik adına günlük bazda hesaplıyoruz.
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365) if daily_returns.std() != 0 else 0


        return {
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_pnl_percent': total_pnl_percent,
            'max_drawdown_percent': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'trades': trades,
            'balance_history': balance_history.to_dict()
        }