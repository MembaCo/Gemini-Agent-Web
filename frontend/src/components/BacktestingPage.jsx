import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { History, PlayCircle, Loader2, SlidersHorizontal, Save, Trash2, FolderDown } from 'lucide-react';

// Bu bileşenler, okunabilirlik için DashboardPage'den kopyalanmıştır.
// Büyük projelerde, bu ortak bileşenler /components/common gibi bir klasöre taşınabilir.
const StatCard = ({ title, value, isLoading, valueClassName = '' }) => ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700"> <h2 className="text-gray-400 text-sm font-medium">{title}</h2> {isLoading ? <div className="animate-pulse bg-gray-700 h-8 w-3/4 mt-2 rounded-md"></div> : <p className={`text-2xl font-semibold mt-1 ${valueClassName}`} dangerouslySetInnerHTML={{ __html: value }}></p>} </div> );
const TradeHistory = ({ history, isLoading }) => ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 mt-8"><h2 className="text-lg font-semibold text-white mb-4">İşlem Geçmişi</h2><div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-xs text-gray-400 uppercase bg-gray-700/50"><tr><th scope="col" className="px-4 py-3">Sembol</th><th scope="col" className="px-4 py-3">Yön</th><th scope="col" className="px-4 py-3">Giriş</th><th scope="col" className="px-4 py-3">Çıkış</th><th scope="col" className="px-4 py-3">P&L (USDT)</th><th scope="col" className="px-4 py-3">Durum</th><th scope="col" className="px-4 py-3">Kapanış Zamanı</th></tr></thead><tbody> {isLoading ? <tr><td colSpan="7" className="text-center p-8 text-gray-400">Yükleniyor...</td></tr> : history && history.length > 0 ? history.map(trade => ( <tr key={trade.id} className="border-b border-gray-700 hover:bg-gray-900/30"><td className="px-4 py-3 font-medium text-white">{trade.symbol}</td><td className="px-4 py-3">{trade.side.toUpperCase()}</td><td className="px-4 py-3">{trade.entry_price.toFixed(4)}</td><td className="px-4 py-3">{trade.close_price.toFixed(4)}</td><td className={`px-4 py-3 font-semibold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>{trade.pnl.toFixed(2)}</td><td className="px-4 py-3">{trade.status}</td><td className="px-4 py-3 text-gray-400">{new Date(trade.closed_at).toLocaleString('tr-TR')}</td></tr>)) : <tr><td colSpan="7" className="text-center p-8 text-gray-400">Testi çalıştırmak için yukarıdaki formu kullanın.</td></tr>}</tbody></table></div></div> );




export const BacktestingPage = () => {
    const { runBacktest, showToast, fetchSettings, fetchPresets, savePreset, deletePreset } = useAuth();
    
    // Test parametreleri
    const [params, setParams] = useState({
        symbol: 'BTC/USDT', timeframe: '4h', start_date: '2024-01-01', end_date: '2024-06-01', initial_balance: 1000
    });
    const [strategyParams, setStrategyParams] = useState({
        RISK_PER_TRADE_PERCENT: 5.0, ATR_MULTIPLIER_SL: 2.0, RISK_REWARD_RATIO_TP: 1.5,
    });
    
    // Ön ayar yönetimi
    const [presets, setPresets] = useState([]);
    const [selectedPreset, setSelectedPreset] = useState("");
    const [newPresetName, setNewPresetName] = useState("");

    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState(null);

    // Mevcut ayarları ve kayıtlı ön ayarları çek
    const loadInitialData = useCallback(() => {
        fetchSettings().then(settings => {
            if (settings) {
                setStrategyParams({
                    RISK_PER_TRADE_PERCENT: settings.RISK_PER_TRADE_PERCENT,
                    ATR_MULTIPLIER_SL: settings.ATR_MULTIPLIER_SL,
                    RISK_REWARD_RATIO_TP: settings.RISK_REWARD_RATIO_TP,
                });
            }
        }).catch(err => showToast("Varsayılan bot ayarları alınamadı.", "warning"));

        fetchPresets().then(setPresets).catch(err => showToast("Kayıtlı ön ayarlar alınamadı.", "error"));
    }, [fetchSettings, fetchPresets, showToast]);

    useEffect(() => {
        loadInitialData();
    }, [loadInitialData]);

    const handleChange = (e) => setParams(prev => ({ ...prev, [e.target.name]: e.target.value }));
    const handleStrategyChange = (e) => setStrategyParams(prev => ({ ...prev, [e.target.name]: parseFloat(e.target.value) || 0 }));

    const handleSavePreset = async () => {
        if (!newPresetName.trim()) {
            showToast("Ön ayar için bir isim girmelisiniz.", "warning");
            return;
        }
        try {
            const presetPayload = { name: newPresetName, settings: { ...params, ...strategyParams } };
            await savePreset(presetPayload);
            showToast(`'${newPresetName}' ön ayarı başarıyla kaydedildi.`, 'success');
            setNewPresetName("");
            loadInitialData(); // Listeyi yenile
        } catch (error) {
            showToast(error.message, 'error');
        }
    };

    const handleLoadPreset = () => {
        if (!selectedPreset) return;
        const presetToLoad = presets.find(p => p.id === parseInt(selectedPreset));
        if (presetToLoad) {
            const { settings } = presetToLoad;
            setParams({
                symbol: settings.symbol,
                timeframe: settings.timeframe,
                start_date: settings.start_date,
                end_date: settings.end_date,
                initial_balance: settings.initial_balance,
            });
            setStrategyParams({
                RISK_PER_TRADE_PERCENT: settings.RISK_PER_TRADE_PERCENT,
                ATR_MULTIPLIER_SL: settings.ATR_MULTIPLIER_SL,
                RISK_REWARD_RATIO_TP: settings.RISK_REWARD_RATIO_TP,
            });
            showToast(`'${presetToLoad.name}' ön ayarı yüklendi.`, 'info');
        }
    };
    
    const handleDeletePreset = async () => {
        if (!selectedPreset) return;
        if (!window.confirm("Bu ön ayarı silmek istediğinizden emin misiniz?")) return;
        try {
            await deletePreset(selectedPreset);
            showToast("Ön ayar başarıyla silindi.", "success");
            setSelectedPreset("");
            loadInitialData(); // Listeyi yenile
        } catch(error) {
            showToast(error.message, "error");
        }
    };

    const handleRunTest = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setResults(null);
        showToast('Backtest başlatılıyor... Bu işlem uzun sürebilir.', 'info');
        try {
            const payload = { ...params, strategy_settings: strategyParams };
            const data = await runBacktest(payload);
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
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                    <History size={24} /> Strateji Geriye Dönük Test Motoru
                </h2>
                
                {/* Ön Ayar Yönetimi */}
                <div className="bg-gray-900/50 p-4 rounded-lg mb-6">
                    <h3 className="text-md font-semibold text-white mb-3">Strateji Ön Ayarları</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="md:col-span-2 flex gap-2">
                             <select value={selectedPreset} onChange={(e) => setSelectedPreset(e.target.value)} className="flex-grow bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white">
                                <option value="">Kayıtlı bir ayar seçin...</option>
                                {presets.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                            </select>
                            <button type="button" onClick={handleLoadPreset} disabled={!selectedPreset} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold p-2 rounded-md disabled:bg-gray-600"><FolderDown size={20}/></button>
                            <button type="button" onClick={handleDeletePreset} disabled={!selectedPreset} className="bg-red-600 hover:bg-red-700 text-white font-semibold p-2 rounded-md disabled:bg-gray-600"><Trash2 size={20}/></button>
                        </div>
                        <div className="flex gap-2">
                            <input type="text" value={newPresetName} onChange={e => setNewPresetName(e.target.value)} placeholder="Yeni ön ayar adı..." className="flex-grow bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white" />
                            <button type="button" onClick={handleSavePreset} disabled={!newPresetName.trim()} className="bg-green-600 hover:bg-green-700 text-white font-semibold p-2 rounded-md disabled:bg-gray-600"><Save size={20}/></button>
                        </div>
                    </div>
                </div>

                {/* Test Parametreleri Formu */}
                <form onSubmit={handleRunTest}>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-end">
                        <div><label className="text-xs text-gray-400">Sembol</label><input type="text" name="symbol" value={params.symbol} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                        <div><label className="text-xs text-gray-400">Zaman Aralığı</label><select name="timeframe" value={params.timeframe} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1"><option value="15m">15 Dakika</option><option value="1h">1 Saat</option><option value="4h">4 Saat</option><option value="1d">1 Gün</option></select></div>
                        <div><label className="text-xs text-gray-400">Başlangıç Tarihi</label><input type="date" name="start_date" value={params.start_date} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                        <div><label className="text-xs text-gray-400">Bitiş Tarihi</label><input type="date" name="end_date" value={params.end_date} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                        <div><label className="text-xs text-gray-400">Başlangıç Bakiyesi ($)</label><input type="number" name="initial_balance" value={params.initial_balance} onChange={handleChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                    </div>
                    <div className="mt-6">
                        <h3 className="text-md font-semibold text-white mb-3 flex items-center gap-2"><SlidersHorizontal size={18} /> Test Edilecek Strateji Ayarları</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div><label className="text-xs text-gray-400">İşlem Başına Risk (%)</label><input type="number" step="0.1" name="RISK_PER_TRADE_PERCENT" value={strategyParams.RISK_PER_TRADE_PERCENT} onChange={handleStrategyChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Stop-Loss ATR Çarpanı</label><input type="number" step="0.1" name="ATR_MULTIPLIER_SL" value={strategyParams.ATR_MULTIPLIER_SL} onChange={handleStrategyChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                            <div><label className="text-xs text-gray-400">Risk/Kazanç Oranı (TP)</label><input type="number" step="0.1" name="RISK_REWARD_RATIO_TP" value={strategyParams.RISK_REWARD_RATIO_TP} onChange={handleStrategyChange} className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white mt-1" /></div>
                        </div>
                    </div>
                    <div className="mt-8 flex justify-center">
                        <button type="submit" disabled={isLoading} className="w-full md:w-1/2 lg:w-1/3 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-md flex justify-center items-center gap-2 text-lg transition-colors disabled:bg-gray-600">
                            {isLoading ? <Loader2 className="animate-spin" size={24} /> : <PlayCircle size={24} />}
                            Stratejiyi Test Et
                        </button>
                    </div>
                </form>
            </div>
            
            {/* Sonuç Alanı */}
            {isLoading && !results && (<div className="text-center py-12"><Loader2 className="animate-spin text-white mx-auto" size={48} /><p className="mt-4 text-gray-400">Geçmiş veriler analiz ediliyor, lütfen bekleyin...</p></div>)}
            {results && (<div className="animate-fade-in-up mt-12"><h3 className="text-xl font-bold text-white mb-4 text-center">Backtest Sonuçları</h3><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"><StatCard title="Net P&L" isLoading={isLoading} value={`${(results.stats.total_pnl || 0).toFixed(2)} USDT`} valueClassName={(results.stats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'} /><StatCard title="Kazanma Oranı" isLoading={isLoading} value={`${(results.stats.win_rate || 0).toFixed(2)}%`} /><StatCard title="Kazanan / Kaybeden" isLoading={isLoading} value={`<span class="text-green-400">${results.stats.winning_trades || 0}</span> / <span class="text-red-400">${results.stats.losing_trades || 0}</span>`} /><StatCard title="Toplam İşlem" isLoading={isLoading} value={results.stats.total_trades || 0} /></div><TradeHistory history={results.trade_history} isLoading={isLoading} /></div>)}
        </div>
    );
};
