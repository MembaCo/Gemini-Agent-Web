import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { History, PlayCircle, Loader2, SlidersHorizontal, Save, Trash2, FolderDown, BrainCircuit } from 'lucide-react';
import TradeHistory from './TradeHistory';

const StatCard = ({ title, value, isLoading, valueClassName = '' }) => (
    <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
        <h2 className="text-gray-400 text-sm font-medium">{title}</h2>
        {isLoading ? (
            <div className="animate-pulse bg-gray-700 h-8 w-3/4 mt-2 rounded-md"></div>
        ) : (
            <p className={`text-2xl font-semibold mt-1 ${valueClassName}`} dangerouslySetInnerHTML={{ __html: value }}></p>
        )}
    </div>
);

// BİRLEŞTİRİLMİŞ PARAMETRELER İÇİN BAŞLANGIÇ DURUMU
const getInitialParams = () => ({
    symbol: 'BTC/USDT',
    timeframe: '4h',
    start_date: '2024-01-01',
    end_date: '2024-06-01',
    initial_balance: 1000,
    // Strateji ve Risk Parametreleri
    RISK_PER_TRADE_PERCENT: 1.0,
    ma_short: 20,
    ma_long: 50,
    rsi_period: 14,
    rsi_overbought: 70,
    rsi_oversold: 30,
});

export const BacktestingPage = () => {
    const { runBacktest, showToast, fetchPresets, savePreset, deletePreset } = useAuth();
    
    const [params, setParams] = useState(getInitialParams());
    const [presets, setPresets] = useState([]);
    const [selectedPreset, setSelectedPreset] = useState("");
    const [newPresetName, setNewPresetName] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState(null);

    const loadPresets = useCallback(() => {
        fetchPresets().then(setPresets).catch(err => showToast("Kayıtlı ön ayarlar alınamadı.", "error"));
    }, [fetchPresets, showToast]);

    useEffect(() => {
        loadPresets();
    }, [loadPresets]);

    const handleChange = (e) => {
        const { name, value, type } = e.target;
        setParams(prev => ({ ...prev, [name]: type === 'number' ? parseFloat(value) || 0 : value }));
    };

    const handleSavePreset = async () => {
        if (!newPresetName.trim()) {
            showToast("Ön ayar için bir isim girmelisiniz.", "warning"); return;
        }
        try {
            // Preset'e sadece strateji ve risk parametrelerini kaydet
            const { symbol, timeframe, start_date, end_date, initial_balance, ...strategySettings } = params;
            const presetPayload = { name: newPresetName, settings: strategySettings };
            await savePreset(presetPayload);
            showToast(`'${newPresetName}' ön ayarı başarıyla kaydedildi.`, 'success');
            setNewPresetName("");
            loadPresets();
        } catch (error) { showToast(error.message, 'error'); }
    };
    
    const handleLoadPreset = () => {
        if (!selectedPreset) return;
        const presetToLoad = presets.find(p => p.id === parseInt(selectedPreset));
        if (presetToLoad) {
            setParams(prev => ({ ...prev, ...presetToLoad.settings }));
            showToast(`'${presetToLoad.name}' ön ayarı yüklendi.`, 'info');
        }
    };
    
    const handleDeletePreset = async () => {
        if (!selectedPreset || !window.confirm("Bu ön ayarı silmek istediğinizden emin misiniz?")) return;
        try {
            await deletePreset(selectedPreset);
            showToast("Ön ayar başarıyla silindi.", "success");
            setSelectedPreset("");
            loadPresets();
        } catch(error) { showToast(error.message, "error"); }
    };

    const handleRunTest = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setResults(null);
        showToast('Backtest başlatılıyor... Bu işlem uzun sürebilir.', 'info');
        
        const { symbol, timeframe, start_date, end_date, initial_balance, ...strategySettings } = params;

        const payload = {
            symbol,
            interval: timeframe,
            start_date,
            end_date,
            initial_balance,
            preset: {
                name: "Dynamic Backtest Run",
                ...strategySettings
            }
        };

        try {
            const data = await runBacktest(payload);
            if (data.message) {
                 showToast(data.message, 'warning');
                 setResults(null);
            } else {
                 setResults(data);
                 showToast('Backtest başarıyla tamamlandı!', 'success');
            }
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-8">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3"><History size={24} /> Strateji Geriye Dönük Test Motoru</h2>
                
                <form onSubmit={handleRunTest} className="space-y-6">
                    {/* Test Ayarları */}
                    <div>
                         <h3 className="text-md font-semibold text-white mb-3">Test Ayarları</h3>
                         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                            <div><label className="text-xs text-gray-400">Sembol</label><input type="text" name="symbol" value={params.symbol} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Zaman Aralığı</label><select name="timeframe" value={params.timeframe} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1"><option value="15m">15 Dakika</option><option value="1h">1 Saat</option><option value="4h">4 Saat</option><option value="1d">1 Gün</option></select></div>
                            <div><label className="text-xs text-gray-400">Başlangıç Tarihi</label><input type="date" name="start_date" value={params.start_date} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Bitiş Tarihi</label><input type="date" name="end_date" value={params.end_date} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Başlangıç Bakiyesi ($)</label><input type="number" name="initial_balance" value={params.initial_balance} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                        </div>
                    </div>
                    
                    {/* Strateji Ayarları */}
                    <div>
                        <h3 className="text-md font-semibold text-white mb-3 flex items-center gap-2"><BrainCircuit size={18} /> MA & RSI Strateji Ayarları</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                            <div><label className="text-xs text-gray-400">Risk/İşlem (%)</label><input type="number" step="0.1" name="RISK_PER_TRADE_PERCENT" value={params.RISK_PER_TRADE_PERCENT} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Kısa MA Periyodu</label><input type="number" name="ma_short" value={params.ma_short} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Uzun MA Periyodu</label><input type="number" name="ma_long" value={params.ma_long} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">RSI Periyodu</label><input type="number" name="rsi_period" value={params.rsi_period} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">RSI Aşırı Alım</label><input type="number" name="rsi_overbought" value={params.rsi_overbought} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">RSI Aşırı Satım</label><input type="number" name="rsi_oversold" value={params.rsi_oversold} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                        </div>
                    </div>
                    
                    {/* Ön Ayarlar ve Çalıştırma Butonu */}
                    <div className="border-t border-gray-700 pt-6 space-y-4">
                        <div className="flex flex-col md:flex-row gap-4">
                             <div className="flex-grow flex gap-2">
                                 <select value={selectedPreset} onChange={(e) => setSelectedPreset(e.target.value)} className="flex-grow bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white">
                                    <option value="">Strateji ayarlarını yükle...</option>
                                    {presets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                </select>
                                <button type="button" onClick={handleLoadPreset} disabled={!selectedPreset} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold p-2 rounded-md disabled:bg-gray-600"><FolderDown size={20}/></button>
                                <button type="button" onClick={handleDeletePreset} disabled={!selectedPreset} className="bg-red-600 hover:bg-red-700 text-white font-semibold p-2 rounded-md disabled:bg-gray-600"><Trash2 size={20}/></button>
                            </div>
                            <div className="flex-grow flex gap-2">
                                <input type="text" value={newPresetName} onChange={e => setNewPresetName(e.target.value)} placeholder="Mevcut strateji ayarlarını kaydet..." className="flex-grow bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white placeholder-gray-500" />
                                <button type="button" onClick={handleSavePreset} disabled={!newPresetName.trim()} className="bg-green-600 hover:bg-green-700 text-white font-semibold p-2 rounded-md disabled:bg-gray-600"><Save size={20}/></button>
                            </div>
                        </div>
                         <div className="flex justify-center pt-4">
                            <button type="submit" disabled={isLoading} className="w-full md:w-1/2 lg:w-1/3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-md flex justify-center items-center gap-2 text-lg transition-colors disabled:bg-gray-600">
                                {isLoading ? <Loader2 className="animate-spin" size={24} /> : <PlayCircle size={24} />}
                                Stratejiyi Test Et
                            </button>
                        </div>
                    </div>
                </form>
            </div>
            
            {isLoading && !results && (<div className="text-center py-12"><Loader2 className="animate-spin text-white mx-auto" size={48} /><p className="mt-4 text-gray-400">Geçmiş veriler analiz ediliyor, lütfen bekleyin...</p></div>)}
            
            {results && !results.message && (
                <div className="animate-fade-in-up mt-12">
                    <h3 className="text-xl font-bold text-white mb-4 text-center">Backtest Sonuçları</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-6">
                        <StatCard title="Son Bakiye" isLoading={isLoading} value={`${(results.final_balance || 0).toFixed(2)} USDT`} valueClassName={(results.total_pnl_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400'} />
                        <StatCard title="Toplam P&L (%)" isLoading={isLoading} value={`${(results.total_pnl_percent || 0).toFixed(2)}%`} valueClassName={(results.total_pnl_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400'} />
                        <StatCard title="Maks. Düşüş (%)" isLoading={isLoading} value={`${(results.max_drawdown_percent || 0).toFixed(2)}%`} valueClassName="text-yellow-400" />
                        <StatCard title="Sharpe Oranı" isLoading={isLoading} value={`${(results.sharpe_ratio || 0).toFixed(3)}`} />
                        <StatCard title="Kazanma Oranı" isLoading={isLoading} value={`${(results.win_rate || 0).toFixed(2)}%`} />
                        <StatCard title="Kazanan / Kaybeden" isLoading={isLoading} value={`<span class="text-green-400">${results.winning_trades || 0}</span> / <span class="text-red-400">${results.losing_trades || 0}</span>`} />
                        <StatCard title="Toplam İşlem" isLoading={isLoading} value={results.total_trades || 0} />
                    </div>
                     {results.trades && (
                        <div className="mt-8 bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
                           <h2 className="text-lg font-semibold text-white mb-4">İşlem Listesi</h2>
                           <TradeHistory history={results.trades.map(t => ({...t, entry_price: t.price, close_price: 0, pnl: 0, status: t.type, closed_at: t.timestamp}))} isLoading={isLoading} />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};