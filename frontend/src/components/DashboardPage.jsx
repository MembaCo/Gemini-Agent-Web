import React, { useState, useEffect, useCallback } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Settings, X, Power, BrainCircuit, AlertTriangle, CheckCircle, Info, XCircle, Search, Play, Save, Zap, RefreshCw, Layers } from 'lucide-react';

import { useAuth } from '../context/AuthContext';

// Chart.js bileşenlerini kaydediyoruz
ChartJS.register( CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend );

// ==============================================================================
//  YARDIMCI VE TEKRAR KULLANILABİLİR BİLEŞENLER
//  Not: Bu bileşenler daha büyük projelerde kendi ayrı dosyalarına (örn: /common) taşınabilir.
// ==============================================================================

const Modal = ({ children, isVisible, onClose, maxWidth = 'max-w-md' }) => {
  if (!isVisible) return null;
  return (
    <div className="fixed inset-0 bg-black/70 flex justify-center items-center z-40" onClick={onClose}>
      <div className={`bg-gray-800 border border-gray-700 rounded-xl p-6 sm:p-8 w-full m-4 ${maxWidth}`} onClick={e => e.stopPropagation()}>{children}</div>
    </div>
  );
};

const Switch = ({ checked, onChange }) => (
    <button type="button" onClick={() => onChange(!checked)} className={`${checked ? 'bg-blue-600' : 'bg-gray-600'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}>
        <span className={`${checked ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
    </button>
);

// ==============================================================================
//  DASHBOARD'A ÖZGÜ BİLEŞENLER
// ==============================================================================

const Header = ({ appVersion, onSettingsClick, isLoading }) => (
  <header className="mb-8 flex justify-between items-center">
    <div>
      <h1 className="text-3xl md:text-4xl font-bold text-white">Gemini Trading Agent</h1>
      <p className="text-gray-400 mt-1">v{appVersion} - Canlı Performans Panosu</p>
    </div>
    <button onClick={onSettingsClick} disabled={isLoading} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
      <Settings size={24} />
    </button>
  </header>
);

const StatCard = ({ title, value, isLoading, valueClassName = '' }) => (
  <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 shadow-lg transition-transform hover:scale-105">
    <h2 className="text-gray-400 text-sm font-medium">{title}</h2>
    {isLoading ? <div className="animate-pulse bg-gray-700 h-8 w-3/4 mt-2 rounded-md"></div> : <p className={`text-2xl font-semibold mt-1 ${valueClassName}`} dangerouslySetInnerHTML={{ __html: value }}></p>}
  </div>
);

const PnlChart = ({ chartData, isLoading }) => {
  const options = { responsive: true, maintainAspectRatio: false, scales: { x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#9ca3af' } }, y: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#9ca3af', callback: (value) => `${value} $` } } }, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1f2937', titleFont: { size: 14 }, bodyFont: { size: 12 }, padding: 10, cornerRadius: 6 } } };
  const data = { labels: chartData.map(d => new Date(d.x).toLocaleDateString('tr-TR')), datasets: [{ label: 'Kümülatif P&L (USDT)', data: chartData.map(d => d.y), borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.2)', fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: '#38bdf8' }] };
  return ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 lg:col-span-2 h-96"><h2 className="text-lg font-semibold text-white mb-4">Kümülatif P&L Zaman Çizelgesi</h2><div className="relative h-72">{isLoading ? <div className="flex justify-center items-center h-full"><p className="text-gray-400">Grafik verileri yükleniyor...</p></div> : <Line options={options} data={data} />}</div></div> );
};

const ActivePositions = ({ positions, isLoading, onAttemptClose, onRefreshPnl, refreshingSymbol, onReanalyze, analyzingSymbol }) => (
    <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
        <h2 className="text-lg font-semibold text-white mb-4">Aktif Pozisyonlar</h2>
        <div className="space-y-4 max-h-[30rem] overflow-y-auto pr-2">{isLoading ? (<p className="text-gray-400">Yükleniyor...</p>) : 
            positions.length > 0 ? (
                positions.map(pos => {
                    const pnl = pos.pnl || 0;
                    const pnlPercentage = pos.pnl_percentage || 0;
                    const pnlColor = pnl >= 0 ? 'text-green-400' : 'text-red-400';
                    const isRefreshing = refreshingSymbol === pos.symbol;
                    const isAnalyzing = analyzingSymbol === pos.symbol;
                    
                    return (
                        <div key={pos.id} className="p-4 rounded-lg bg-gray-900/50 border border-gray-700 group">
                            <div className="flex justify-between items-center mb-2">
                                <span className="font-bold text-white">{pos.symbol}</span>
                                <span className={`px-2 py-1 text-xs font-semibold rounded ${pos.side === 'buy' ? 'bg-green-800 text-green-200' : 'bg-red-800 text-red-200'}`}>{pos.side.toUpperCase()}</span>
                            </div>
                            <div className="flex justify-between items-center mb-2 p-2 rounded-md">
                                <div className={`text-left ${pnl >= 0 ? 'bg-green-900/50' : 'bg-red-900/50'} p-2 rounded-md flex-grow`}>
                                    <p className={`text-lg font-bold ${pnlColor}`}>{pnl.toFixed(2)} USDT</p>
                                    <p className={`text-xs ${pnlColor}`}>({pnlPercentage.toFixed(2)}%)</p>
                                </div>
                                <button onClick={() => onRefreshPnl(pos.symbol)} disabled={isRefreshing} className="p-2 ml-3 text-gray-400 hover:text-white rounded-full hover:bg-gray-700 transition-colors disabled:cursor-not-allowed">
                                    <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
                                </button>
                            </div>
                            <div className="text-xs text-gray-400 grid grid-cols-2 gap-x-4">
                                <p>Giriş: <span className="text-gray-200">{pos.entry_price.toFixed(4)}</span></p><p>Miktar: <span className="text-gray-200">{pos.amount.toFixed(4)}</span></p>
                                <p>SL: <span className="text-red-400">{pos.stop_loss.toFixed(4)}</span></p><p>TP: <span className="text-green-400">{pos.take_profit.toFixed(4)}</span></p>
                            </div>
                            <div className="mt-3 w-full grid grid-cols-2 gap-2 text-xs font-semibold">
                                <button onClick={() => onReanalyze(pos.symbol)} disabled={isAnalyzing} className="flex items-center justify-center gap-2 bg-blue-600/80 hover:bg-blue-600 text-white py-1.5 rounded-md disabled:bg-gray-600">
                                    {isAnalyzing ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Layers size={14} />} Tekrar Analiz Et
                                </button>
                                <button onClick={() => onAttemptClose(pos.symbol)} className="flex items-center justify-center gap-2 bg-red-600/80 hover:bg-red-600 text-white py-1.5 rounded-md">
                                    <Power size={14} /> Kapat
                                </button>
                            </div>
                        </div>
                    );
                })
            ) : (<p className="text-gray-400">Aktif pozisyon bulunmuyor.</p>)}</div></div>
);

const TradeHistory = ({ history, isLoading }) => ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700"><h2 className="text-lg font-semibold text-white mb-4">İşlem Geçmişi</h2><div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-xs text-gray-400 uppercase bg-gray-700/50"><tr><th scope="col" className="px-4 py-3">Sembol</th><th scope="col" className="px-4 py-3">Yön</th><th scope="col" className="px-4 py-3">Giriş</th><th scope="col" className="px-4 py-3">Kapanış</th><th scope="col" className="px-4 py-3">P&L (USDT)</th><th scope="col" className="px-4 py-3">Durum</th><th scope="col" className="px-4 py-3">Kapanış Zamanı</th></tr></thead><tbody>
      {isLoading ? <tr><td colSpan="7" className="text-center p-8 text-gray-400">Yükleniyor...</td></tr> : history.length > 0 ? history.map(trade => ( <tr key={trade.id} className="border-b border-gray-700 hover:bg-gray-900/30"><td className="px-4 py-3 font-medium text-white">{trade.symbol}</td><td className="px-4 py-3">{trade.side.toUpperCase()}</td><td className="px-4 py-3">{trade.entry_price.toFixed(4)}</td><td className="px-4 py-3">{trade.close_price.toFixed(4)}</td><td className={`px-4 py-3 font-semibold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>{trade.pnl.toFixed(2)}</td><td className="px-4 py-3">{trade.status}</td><td className="px-4 py-3 text-gray-400">{new Date(trade.closed_at).toLocaleString('tr-TR')}</td></tr>)) : <tr><td colSpan="7" className="text-center p-8 text-gray-400">İşlem geçmişi bulunmuyor.</td></tr>}</tbody></table></div></div> );

const NewAnalysis = ({ onAnalysisStart, isAnalyzing }) => {
  const [symbol, setSymbol] = useState('');
  const [timeframe, setTimeframe] = useState('15m');
  const handleSubmit = (e) => { e.preventDefault(); if (symbol.trim()) { onAnalysisStart({ symbol, timeframe }); } };
  return ( <div className="bg-gray-800 p-6 rounded-xl border border-gray-700"><h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><BrainCircuit size={20} />Yeni Analiz Başlat</h2><form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4"><input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="Sembol Girin (örn: BTC)" className="flex-grow bg-gray-900 border border-gray-700 rounded-md px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500" /><select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"><option value="5m">5 Dakika</option><option value="15m">15 Dakika</option><option value="1h">1 Saat</option><option value="4h">4 Saat</option></select><button type="submit" disabled={isAnalyzing || !symbol.trim()} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2 rounded-md disabled:bg-gray-600 disabled:cursor-not-allowed flex justify-center items-center">{isAnalyzing ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : 'Analiz Et'}</button></form></div> );
};

const ProactiveScanner = ({ onRunScan, isScanning }) => ( <div className="bg-gray-800 p-6 rounded-xl border border-gray-700"><div className="flex justify-between items-center"><h2 className="text-lg font-semibold text-white flex items-center gap-2"><Search size={20}/>Proaktif Tarayıcı (Fırsat Avcısı)</h2><button onClick={onRunScan} disabled={isScanning} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-5 py-2 rounded-md disabled:bg-gray-600 disabled:cursor-not-allowed flex justify-center items-center gap-2">{isScanning ? <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> Taranıyor...</> : <><Play size={16}/> Şimdi Tara</>}</button></div><p className="text-sm text-gray-400 mt-2">Piyasayı potansiyel ticaret fırsatları için manuel olarak tarar. Otomatik tarama backend'de çalışmaya devam eder.</p></div> );

// --- MODAL BİLEŞENLERİ ---

const SettingsModal = ({ settings, isVisible, onClose, onSave }) => {
    const [editableSettings, setEditableSettings] = useState(settings);

    useEffect(() => { 
        if (isVisible) {
            setEditableSettings(settings); 
        }
    }, [settings, isVisible]);

    const handleChange = (key, value) => setEditableSettings(prev => ({...prev, [key]: value}));

    const renderInput = (key, value) => {
        if (typeof value === 'boolean') { return <Switch checked={value} onChange={(checked) => handleChange(key, checked)} />; }
        if (typeof value === 'number') { return <input type="number" step="0.1" value={value} onChange={e => handleChange(key, parseFloat(e.target.value) || 0)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-24 text-white text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />; }
        if (Array.isArray(value)) { return <input type="text" value={value.join(', ')} onChange={e => handleChange(key, e.target.value.split(',').map(s => s.trim().toUpperCase()))} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />; }
        return <input type="text" value={value} onChange={e => handleChange(key, e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />;
    };

    return ( 
        <Modal isVisible={isVisible} onClose={onClose} maxWidth="max-w-3xl">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white">Uygulama Ayarları</h2>
                <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white"><X size={24} /></button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 max-h-[70vh] overflow-y-auto pr-4 text-sm">
                {Object.keys(editableSettings).length > 0 ? ( Object.keys(editableSettings).sort().map(key => ( 
                    <div key={key} className="flex justify-between items-center border-b border-gray-700 py-2 gap-4">
                        <label className="text-gray-400 flex-shrink-0">{key}</label>
                        {renderInput(key, editableSettings[key])}
                    </div> 
                ))) : ( <p className="text-gray-400 col-span-2">Ayarlar yükleniyor...</p> )}
            </div>
            <div className="mt-6 flex justify-end">
                <button onClick={() => onSave(editableSettings)} className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-md flex items-center gap-2">
                    <Save size={18}/>Ayarları Kaydet
                </button>
            </div>
        </Modal> 
    );
};

const AnalysisResultModal = ({ result, isVisible, onClose, onConfirmTrade }) => {
    const isTradeable = result?.recommendation === 'AL' || result?.recommendation === 'SAT';
    return ( 
        <Modal isVisible={isVisible} onClose={onClose}>
            <h2 className="text-2xl font-bold text-white mb-4">Analiz Sonucu</h2>
            <div className="space-y-3 text-gray-300">
                <p><span className="font-semibold text-gray-400">Sembol:</span> {result?.symbol}</p>
                <p><span className="font-semibold text-gray-400">Tavsiye:</span> <span className={`font-bold ${isTradeable ? (result?.recommendation === 'AL' ? 'text-green-400' : 'text-red-400') : 'text-yellow-400'}`}>{result?.recommendation}</span></p>
                <p><span className="font-semibold text-gray-400">Neden:</span> {result?.reason}</p>
            </div>
            <div className="mt-6 flex gap-4">
                <button onClick={onClose} className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 rounded-md">Kapat</button>
                {isTradeable && <button onClick={() => onConfirmTrade(result)} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-md">Pozisyon Aç</button>}
            </div>
        </Modal> 
    );
};

const ConfirmationModal = ({ isVisible, onClose, onConfirm, title, children }) => ( 
    <Modal isVisible={isVisible} onClose={onClose}>
        <h2 className="text-2xl font-bold text-white mb-4">{title}</h2>
        <div className="text-gray-300 mb-6">{children}</div>
        <div className="flex gap-4">
            <button onClick={onClose} className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 rounded-md">İptal</button>
            <button onClick={onConfirm} className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded-md">Onayla</button>
        </div>
    </Modal> 
);

const ScanResultModal = ({ results, isVisible, onClose, onConfirmTrade }) => {
    const getIcon = (type) => {
        switch (type) {
            case 'success': return <CheckCircle className="text-green-400" size={18} />;
            case 'opportunity': return <Zap className="text-yellow-400" size={18} />;
            case 'error': return <AlertTriangle className="text-orange-400" size={18} />;
            case 'critical': return <XCircle className="text-red-500" size={18} />;
            default: return <Info className="text-blue-400" size={18} />;
        }
    };
    return ( 
        <Modal isVisible={isVisible} onClose={onClose} maxWidth="max-w-3xl">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white">Tarama Sonuçları</h2>
                <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white"><X size={24} /></button>
            </div>
            <div className="bg-gray-900/50 p-4 rounded-lg mb-4 grid grid-cols-3 gap-4 text-center">
                <div><p className="text-gray-400 text-sm">Taranan Sembol</p><p className="text-xl font-bold text-white">{results?.summary?.total_scanned || 0}</p></div>
                <div><p className="text-gray-400 text-sm">Bulunan Fırsat</p><p className="text-xl font-bold text-yellow-400">{results?.summary?.opportunities_found || 0}</p></div>
                <div><p className="text-gray-400 text-sm">Veri Hatası</p><p className="text-xl font-bold text-red-400">{results?.summary?.data_errors || 0}</p></div>
            </div>
            <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-4">
                {results?.details?.map((item, index) => ( 
                    <div key={index} className="p-3 bg-gray-900/50 rounded-md flex items-start gap-3">
                        <div className="flex-shrink-0 mt-1">{getIcon(item.type)}</div>
                        <div className="flex-grow">
                            <p className="font-semibold text-white">{item.symbol}</p>
                            <p className="text-sm text-gray-400">{item.message}</p>
                            {item.type === 'opportunity' && ( 
                                <button onClick={() => onConfirmTrade(item.data)} className="mt-2 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold px-3 py-1 rounded-md">Onayla ve Pozisyon Aç</button> 
                            )}
                        </div>
                    </div> 
                ))}
            </div>
        </Modal> 
    );
};

const ReanalysisResultModal = ({ result, isVisible, onClose, onConfirmClose }) => (
    <Modal isVisible={isVisible} onClose={onClose}>
        <h2 className="text-2xl font-bold text-white mb-4">Pozisyon Yeniden Analiz Sonucu</h2>
        <div className="space-y-3 text-gray-300">
            <p><span className="font-semibold text-gray-400">Sembol:</span> {result?.symbol}</p>
            <p><span className="font-semibold text-gray-400">AI Tavsiyesi:</span> <span className={`font-bold ${result?.recommendation === 'KAPAT' ? 'text-red-400' : 'text-green-400'}`}>{result?.recommendation}</span></p>
            <p><span className="font-semibold text-gray-400">Gerekçe:</span> {result?.reason}</p>
        </div>
        <div className="mt-6 flex gap-4">
            <button onClick={onClose} className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 rounded-md">Pozisyonu Tut</button>
            {result?.recommendation === 'KAPAT' && <button onClick={() => onConfirmClose(result.symbol)} className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded-md">Kapatmayı Onayla</button>}
        </div>
    </Modal>
);

// ==============================================================================
//  ANA DASHBOARD SAYFA BİLEŞENİ
// ==============================================================================
export const DashboardPage = () => {
  const [stats, setStats] = useState({});
  const [chartData, setChartData] = useState([]);
  const [activePositions, setActivePositions] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [settings, setSettings] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  
  const [isSettingsModalVisible, setIsSettingsModalVisible] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [scanResults, setScanResults] = useState(null);
  const [confirmationDetails, setConfirmationDetails] = useState(null);
  const [refreshingSymbol, setRefreshingSymbol] = useState(null);
  const [analyzingSymbol, setAnalyzingSymbol] = useState(null);
  const [reanalysisResult, setReanalysisResult] = useState(null);

  const { showToast, fetchData, fetchPositions, fetchSettings, saveSettings, runAnalysis, runScanner, openPosition, closePosition, refreshPnl, reanalyzePosition } = useAuth();

  const loadAllData = useCallback(async (showLoading = false) => {
      if (showLoading) setIsLoading(true);
      setError(null);
      try {
          const [dashboardData, positionsData, settingsData] = await Promise.all([
              fetchData(),
              fetchPositions(),
              fetchSettings()
          ]);
          setStats(dashboardData.stats);
          setChartData(dashboardData.chart_data.points);
          setTradeHistory(dashboardData.trade_history.reverse());
          setActivePositions(positionsData.managed_positions);
          setSettings(settingsData);
      } catch (err) {
          setError(err.message);
      } finally {
          if (showLoading) setIsLoading(false);
      }
  }, [fetchData, fetchPositions, fetchSettings]);

  useEffect(() => {
    loadAllData(true); // İlk yükleme

    let interval;
    // Sadece ayarlar modalı kapalıyken periyodik yenilemeyi başlat.
    if (!isSettingsModalVisible) {
      interval = setInterval(() => {
        loadAllData(false);
      }, 5000);
    }
    
    // Bileşen unmount olduğunda veya modal açıldığında interval'ı temizle.
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [loadAllData, isSettingsModalVisible]); // isSettingsModalVisible'ı dependency array'e ekliyoruz.

  const handleAnalysis = useCallback(async ({ symbol, timeframe }) => {
    setIsAnalyzing(true);
    try {
      const result = await runAnalysis({ symbol, timeframe });
      setAnalysisResult(result);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsAnalyzing(false);
    }
  }, [showToast, runAnalysis]);
  
  const handleConfirmTrade = useCallback(async (result) => {
    setAnalysisResult(null);
    setScanResults(null);
    showToast('Pozisyon açma isteği gönderiliyor...', 'info');
    try {
      const openResult = await openPosition({ symbol: result.symbol, recommendation: result.recommendation, timeframe: result.timeframe, price: result.data.price });
      showToast(openResult.message || 'Pozisyon başarıyla açıldı!', 'success');
      loadAllData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }, [showToast, openPosition, loadAllData]);
  
  const handleRunScan = useCallback(async () => {
    setIsScanning(true);
    setScanResults(null);
    showToast('Proaktif tarama başlatılıyor...', 'info');
    try {
        const result = await runScanner();
        setScanResults(result);
    } catch(err) {
        showToast(err.message, 'error');
    } finally {
        setIsScanning(false);
    }
  }, [showToast, runScanner]);

  const handleSaveSettings = useCallback(async (newSettings) => {
      showToast('Ayarlar veritabanına kaydediliyor...', 'info');
      try {
          const result = await saveSettings(newSettings);
          showToast(result.message, 'success');
          setIsSettingsModalVisible(false);
          loadAllData(true);
      } catch (err) {
          showToast(err.message, 'error');
      }
  }, [showToast, saveSettings, loadAllData]);

  const handleAttemptClosePosition = useCallback((symbol) => setConfirmationDetails({ title: 'Pozisyonu Kapat', message: `${symbol} pozisyonunu kapatmak istediğinizden emin misiniz? Bu işlem geri alınamaz.`, onConfirm: () => handleClosePosition(symbol) }), []);
  
  const handleClosePosition = useCallback(async (symbol) => {
    setConfirmationDetails(null);
    setReanalysisResult(null);
    showToast(`${symbol} pozisyonu kapatılıyor...`, 'info');
    try {
      const result = await closePosition(symbol);
      showToast(result.message, 'success');
      loadAllData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }, [showToast, closePosition, loadAllData]);

  const handleRefreshPnl = useCallback(async (symbol) => {
    setRefreshingSymbol(symbol);
    showToast(`${symbol} için PNL yenileniyor...`, 'info');
    try {
        await refreshPnl(symbol);
        setTimeout(() => { loadAllData(); setRefreshingSymbol(null); }, 2000);
    } catch(err) {
        showToast(err.message, 'error');
        setRefreshingSymbol(null);
    }
  }, [showToast, refreshPnl, loadAllData]);

  const handleReanalyze = useCallback(async (symbol) => {
      setAnalyzingSymbol(symbol);
      showToast(`${symbol} pozisyonu yeniden analiz ediliyor...`, 'info');
      try {
          const result = await reanalyzePosition(symbol);
          setReanalysisResult(result);
      } catch (err) {
          showToast(err.message, 'error');
      } finally {
          setAnalyzingSymbol(null);
      }
  }, [showToast, reanalyzePosition]);


  if (error && isLoading) {
    return ( 
        <div className="bg-gray-900 min-h-screen flex justify-center items-center text-white p-4">
            <div className="bg-red-800/50 border border-red-700 p-8 rounded-xl text-center">
                <h2 className="text-2xl font-bold mb-4">Bağlantı Hatası</h2>
                <p className="text-red-200">{error}</p>
                <button onClick={() => loadAllData(true)} className="mt-6 bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold">
                    Yeniden Dene
                </button>
            </div>
        </div> 
    );
  }

  return (
    <>
      <Header appVersion={settings.APP_VERSION || "3.4.0-refactor"} onSettingsClick={() => setIsSettingsModalVisible(true)} isLoading={isLoading} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <NewAnalysis onAnalysisStart={handleAnalysis} isAnalyzing={isAnalyzing} />
        <ProactiveScanner onRunScan={handleRunScan} isScanning={isScanning} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Toplam P&L" isLoading={isLoading} value={`${(stats.total_pnl || 0).toFixed(2)} USDT`} valueClassName={(stats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'} />
        <StatCard title="Kazanma Oranı" isLoading={isLoading} value={`${(stats.win_rate || 0).toFixed(2)}%`} />
        <StatCard title="Kazanan / Kaybeden" isLoading={isLoading} value={`<span class="text-green-400">${stats.winning_trades || 0}</span> / <span class="text-red-400">${stats.losing_trades || 0}</span>`} />
        <StatCard title="Toplam İşlem" isLoading={isLoading} value={stats.total_trades || 0} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          <PnlChart chartData={chartData} isLoading={isLoading} />
          <ActivePositions positions={activePositions} isLoading={isLoading} onAttemptClose={handleAttemptClosePosition} onRefreshPnl={handleRefreshPnl} refreshingSymbol={refreshingSymbol} onReanalyze={handleReanalyze} analyzingSymbol={analyzingSymbol} />
      </div>
      <TradeHistory history={tradeHistory} isLoading={isLoading} />

      <SettingsModal settings={settings} isVisible={isSettingsModalVisible} onClose={() => setIsSettingsModalVisible(false)} onSave={handleSaveSettings} />
      <AnalysisResultModal result={analysisResult} isVisible={!!analysisResult} onClose={() => setAnalysisResult(null)} onConfirmTrade={handleConfirmTrade} />
      <ScanResultModal results={scanResults} isVisible={!!scanResults} onClose={() => setScanResults(null)} onConfirmTrade={handleConfirmTrade} />
      <ConfirmationModal isVisible={!!confirmationDetails} onClose={() => setConfirmationDetails(null)} onConfirm={confirmationDetails?.onConfirm} title={confirmationDetails?.title}><p>{confirmationDetails?.message}</p></ConfirmationModal>
      <ReanalysisResultModal result={reanalysisResult} isVisible={!!reanalysisResult} onClose={() => setReanalysisResult(null)} onConfirmClose={handleClosePosition} />
    </>
  );
};
