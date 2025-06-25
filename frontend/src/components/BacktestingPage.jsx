import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { History, PlayCircle, Loader2 } from 'lucide-react';

// Dashboard'dan yeniden kullanılabilir bileşenleri import edelim
// NOT: Bu bileşenleri ayrı dosyalara taşıyıp oradan import etmek daha temiz bir yöntemdir.
// Şimdilik, App.jsx'ten kopyalayıp buraya yapıştırabilir veya direkt App.jsx'i referans alabilirsiniz.
// Biz burada onları yeniden tanımlayacağız.
const StatCard = ({ title, value, isLoading, valueClassName = '' }) => ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700"> <h2 className="text-gray-400 text-sm font-medium">{title}</h2> {isLoading ? <div className="animate-pulse bg-gray-700 h-8 w-3/4 mt-2 rounded-md"></div> : <p className={`text-2xl font-semibold mt-1 ${valueClassName}`} dangerouslySetInnerHTML={{ __html: value }}></p>} </div> );
const TradeHistory = ({ history, isLoading }) => ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 mt-8"><h2 className="text-lg font-semibold text-white mb-4">İşlem Geçmişi</h2><div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-xs text-gray-400 uppercase bg-gray-700/50"><tr><th scope="col" className="px-4 py-3">Sembol</th><th scope="col" className="px-4 py-3">Yön</th><th scope="col" className="px-4 py-3">Giriş</th><th scope="col" className="px-4 py-3">Kapanış</th><th scope="col" className="px-4 py-3">P&L (USDT)</th><th scope="col" className="px-4 py-3">Durum</th><th scope="col" className="px-4 py-3">Kapanış Zamanı</th></tr></thead><tbody> {isLoading ? <tr><td colSpan="7" className="text-center p-8 text-gray-400">Yükleniyor...</td></tr> : history.length > 0 ? history.map(trade => ( <tr key={trade.id} className="border-b border-gray-700 hover:bg-gray-900/30"><td className="px-4 py-3 font-medium text-white">{trade.symbol}</td><td className="px-4 py-3">{trade.side.toUpperCase()}</td><td className="px-4 py-3">{trade.entry_price.toFixed(4)}</td><td className="px-4 py-3">{trade.close_price.toFixed(4)}</td><td className={`px-4 py-3 font-semibold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>{trade.pnl.toFixed(2)}</td><td className="px-4 py-3">{trade.status}</td><td className="px-4 py-3 text-gray-400">{new Date(trade.closed_at).toLocaleString('tr-TR')}</td></tr>)) : <tr><td colSpan="7" className="text-center p-8 text-gray-400">Testi çalıştırın veya sonuç bekleyin.</td></tr>}</tbody></table></div></div> );


export const BacktestingPage = () => {
    const { runBacktest, showToast } = useAuth();
    const [params, setParams] = useState({
        symbol: 'BTC/USDT',
        timeframe: '4h',
        start_date: '2024-01-01',
        end_date: '2024-06-01',
        initial_balance: 1000
    });
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState(null);

    const handleChange = (e) => {
        setParams(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setResults(null);
        showToast('Backtest başlatılıyor... Bu işlem uzun sürebilir.', 'info');
        try {
            const data = await runBacktest(params);
            setResults(data);
            showToast('Backtest başarıyla tamamlandı!', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-8">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                    <History size={24} /> Strateji Geriye Dönük Test Motoru
                </h2>
                <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
                    <div>
                        <label className="text-xs text-gray-400">Sembol</label>
                        <input type="text" name="symbol" value={params.symbol} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" />
                    </div>
                     <div>
                        <label className="text-xs text-gray-400">Zaman Aralığı</label>
                        <select name="timeframe" value={params.timeframe} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1">
                            <option value="15m">15 Dakika</option>
                            <option value="1h">1 Saat</option>
                            <option value="4h">4 Saat</option>
                            <option value="1d">1 Gün</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs text-gray-400">Başlangıç Tarihi</label>
                        <input type="date" name="start_date" value={params.start_date} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" />
                    </div>
                    <div>
                        <label className="text-xs text-gray-400">Bitiş Tarihi</label>
                        <input type="date" name="end_date" value={params.end_date} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" />
                    </div>
                    <button type="submit" disabled={isLoading} className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-md flex justify-center items-center gap-2">
                        {isLoading ? <Loader2 className="animate-spin" size={20} /> : <PlayCircle size={20} />}
                        Testi Başlat
                    </button>
                </form>
            </div>

            {/* Sonuçları Gösterme Alanı */}
            {results && (
                <div className="animate-fade-in-up">
                    <h3 className="text-xl font-bold text-white mb-4">Backtest Sonuçları</h3>
                     <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        <StatCard title="Toplam P&L" isLoading={isLoading} value={`${(results.stats.total_pnl || 0).toFixed(2)} USDT`} valueClassName={(results.stats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'} />
                        <StatCard title="Kazanma Oranı" isLoading={isLoading} value={`${(results.stats.win_rate || 0).toFixed(2)}%`} />
                        <StatCard title="Kazanan / Kaybeden" isLoading={isLoading} value={`<span class="text-green-400">${results.stats.winning_trades || 0}</span> / <span class="text-red-400">${results.stats.losing_trades || 0}</span>`} />
                        <StatCard title="Toplam İşlem" isLoading={isLoading} value={results.stats.total_trades || 0} />
                    </div>
                    <TradeHistory history={results.trade_history} isLoading={isLoading} />
                </div>
            )}
        </div>
    );
};