import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend, ArcElement, BarElement } from 'chart.js';
import { Line, Pie, Bar } from 'react-chartjs-2';
import { Settings, X, Power, BrainCircuit, AlertTriangle, CheckCircle, Info, XCircle, Search, Play, Save, Zap, RefreshCw, Layers, Loader2, Cpu, BarChartHorizontal, ShieldX, Terminal, Calendar as CalendarIcon, FilterX, Edit } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { TradeChartModal } from './TradeChartModal';
import { Modal, Switch, TooltipWrapper, AnalysisResultModal, ReanalysisResultModal, ConfirmationModal } from './SharedComponents';

ChartJS.register( CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend, ArcElement, BarElement );

// === YARDIMCI FONKSİYONLAR ===
const formatHoldingPeriod = (seconds) => {
    if (isNaN(seconds) || seconds < 1) return `0 saniye`;
    if (seconds < 60) return `${Math.round(seconds)} saniye`;
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    if (hours < 1) return `${minutes} dakika`;
    return `${hours} saat, ${minutes % 60} dakika`;
};

// === YENİ VE GÜNCELLENMİŞ BİLEŞENLER ===
const Header = ({ appVersion, onSettingsClick, isLoading }) => ( <header className="mb-8 flex justify-between items-center"><div><h1 className="text-3xl md:text-4xl font-bold text-white">Gemini Trading Agent</h1><p className="text-gray-400 mt-1">v{appVersion} - Canlı Performans Paneli</p></div><button onClick={onSettingsClick} disabled={isLoading} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><Settings size={24} /></button></header> );

const StatCard = ({ title, value, isLoading, valueClassName = '', icon, tooltip }) => ( <div className="bg-gray-800 p-4 sm:p-5 rounded-xl border border-gray-700 shadow-lg transition-transform hover:scale-105"><div className="flex justify-between items-start"><h2 className="text-gray-400 text-sm font-medium">{title}</h2><TooltipWrapper content={tooltip}>{icon || <Info size={16} className="text-gray-500" />}</TooltipWrapper></div>{isLoading ? <div className="animate-pulse bg-gray-700 h-8 w-3/4 mt-2 rounded-md"></div> : <p className={`text-2xl font-semibold mt-1 ${valueClassName}`} dangerouslySetInnerHTML={{ __html: value }}></p>}</div> );

const PnlChart = ({ chartData, isLoading }) => { const options = { responsive: true, maintainAspectRatio: false, scales: { x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#9ca3af' } }, y: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#9ca3af', callback: (value) => `${value} $` } } }, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1f2937', titleFont: { size: 14 }, bodyFont: { size: 12 }, padding: 10, cornerRadius: 6 } } }; const sortedData = [...chartData].sort((a, b) => new Date(a.x) - new Date(b.x)); const data = { labels: sortedData.map(d => new Date(d.x).toLocaleDateString('tr-TR')), datasets: [{ label: 'Kümülatif P&L (USDT)', data: sortedData.map(d => d.y), borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.2)', fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: '#38bdf8' }] }; return ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 lg:col-span-2 h-96"><h2 className="text-lg font-semibold text-white mb-4">Kümülatif P&L Zaman Çizelgesi</h2><div className="relative h-72">{isLoading ? <div className="flex justify-center items-center h-full"><Loader2 className="animate-spin mx-auto text-white" size={40} /></div> : <Line options={options} data={data} />}</div></div> );};

const PerformanceCharts = ({ bySymbol, byWeek, isLoading }) => {
    const pieData = { labels: bySymbol.map(d => d.symbol), datasets: [{ data: bySymbol.map(d => d.count), backgroundColor: ['#38bdf8', '#34d399', '#f87171', '#fbbf24', '#a78bfa', '#a8a29e'], borderColor: '#1f2937', borderWidth: 2, }] };
    const pieOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top', labels: { color: '#d1d5db', padding: 20 } } } };
    const barData = { labels: byWeek.map(d => d.week), datasets: [{ label: 'Haftalık P&L (USDT)', data: byWeek.map(d => d.pnl), backgroundColor: byWeek.map(d => d.pnl >= 0 ? 'rgba(52, 211, 153, 0.6)' : 'rgba(248, 113, 113, 0.6)'), borderColor: byWeek.map(d => d.pnl >= 0 ? '#34d399' : '#f87171'), borderWidth: 1, }] };
    const barOptions = { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { color: '#9ca3af' } }, y: { ticks: { color: '#9ca3af' } } }, plugins: { legend: { display: false } } };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 h-96"><h2 className="text-lg font-semibold text-white mb-4">İşlem Dağılımı (Sembole Göre)</h2><div className="relative h-72">{isLoading ? <Loader2 className="animate-spin text-white mx-auto mt-24" /> : bySymbol.length > 0 ? <Pie data={pieData} options={pieOptions} /> : <p className="text-center text-gray-500 mt-24">Veri yok</p>}</div></div>
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 h-96"><h2 className="text-lg font-semibold text-white mb-4">Haftalık Performans</h2><div className="relative h-72">{isLoading ? <Loader2 className="animate-spin text-white mx-auto mt-24" /> : byWeek.length > 0 ? <Bar data={barData} options={barOptions} /> : <p className="text-center text-gray-500 mt-24">Veri yok</p>}</div></div>
        </div>
    );
};

const LogPanel = ({ logs, isLoading }) => {
    const logContainerRef = useRef(null);
    useEffect(() => { if (logContainerRef.current) { logContainerRef.current.scrollTop = 0; } }, [logs]);
    return (
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 mt-8">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Terminal />Canlı Sistem Olayları</h2>
            <div ref={logContainerRef} className="bg-black/50 rounded-md p-4 font-mono text-xs text-gray-300 h-64 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-black/50">
                {isLoading && <p>Loglar yükleniyor...</p>}
                {logs.map(log => {
                    const levelColor = log.level === 'CRITICAL' ? 'text-red-500' : log.level === 'ERROR' ? 'text-red-400' : log.level === 'WARNING' ? 'text-yellow-400' : log.level === 'SUCCESS' ? 'text-green-400' : 'text-gray-500';
                    return (<div key={log.id}><span className="text-gray-600">{new Date(log.timestamp).toLocaleTimeString('tr-TR')} | </span><span className={`${levelColor} font-bold`}>{log.category}</span>: <span className="text-gray-300">{log.message}</span></div>);
                })}
            </div>
        </div>
    );
};

// ... diğer bileşenler (ActivePositions, TradeHistory, NewAnalysis vb.) yukarıdaki halleriyle kullanılabilir ...
// ... SettingsModal bileşenini de daha kapsamlı hale getiriyoruz ...
const SettingsModal = ({ settings, isVisible, onClose, onSave }) => { /* ... önceki yanıttaki tam kapsamlı hali ... */ };
const ScanResultModal = ({ results, isVisible, onClose, onConfirmTrade, processingOpportunities }) => { /* ... önceki yanıttaki hali ... */ };

// ... ana bileşen ...
export const DashboardPage = () => {
    // State'ler
    const [stats, setStats] = useState({});
    const [performanceData, setPerformanceData] = useState({ bySymbol: [], byWeek: [] });
    const [chartData, setChartData] = useState([]);
    const [activePositions, setActivePositions] = useState([]);
    const [tradeHistory, setTradeHistory] = useState([]);
    const [filteredHistory, setFilteredHistory] = useState([]);
    const [settings, setSettings] = useState({});
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDataLoaded, setIsDataLoaded] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isScanning, setIsScanning] = useState(false);
    const [isOpeningTrade, setIsOpeningTrade] = useState(false);
    const [isSettingsModalVisible, setIsSettingsModalVisible] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [scanResults, setScanResults] = useState(null);
    const [confirmationDetails, setConfirmationDetails] = useState(null);
    const [refreshingSymbol, setRefreshingSymbol] = useState(null);
    const [analyzingSymbol, setAnalyzingSymbol] = useState(null);
    const [reanalysisResult, setReanalysisResult] = useState(null);
    const [selectedTradeForChart, setSelectedTradeForChart] = useState(null);
    const [isChartModalVisible, setIsChartModalVisible] = useState(false);
    const [processingOpportunities, setProcessingOpportunities] = useState({});

    const { showToast, fetchData, fetchPositions, fetchSettings, saveSettings, runAnalysis, runProactiveScan, openPosition, closePosition, refreshPnl, reanalyzePosition, fetchEvents } = useAuth();
    
    const handleChartModalOpen = (trade) => { setSelectedTradeForChart(trade); setIsChartModalVisible(true); };

    const loadAllData = useCallback(async (showLoadingSpinner = false) => {
        if (showLoadingSpinner && !isDataLoaded) setIsLoading(true);
        try {
            const [dashboardData, positionsData, settingsData, eventsData] = await Promise.all([
                fetchData(),
                fetchPositions(),
                fetchSettings(),
                fetchEvents()
            ]);
            setStats(dashboardData.stats);
            setPerformanceData({
                bySymbol: dashboardData.performance_by_symbol || [],
                byWeek: dashboardData.performance_by_week || [],
            });
            setChartData(dashboardData.chart_data.points);
            setTradeHistory(dashboardData.trade_history);
            setFilteredHistory(dashboardData.trade_history);
            setActivePositions(positionsData.managed_positions);
            setSettings(settingsData);
            setLogs(eventsData);
            if (!isDataLoaded) setIsDataLoaded(true);
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            if (showLoadingSpinner) setIsLoading(false);
        }
    }, [fetchData, fetchPositions, fetchSettings, fetchEvents, showToast, isDataLoaded]);

    useEffect(() => {
        loadAllData(true);
        const interval = setInterval(() => loadAllData(false), 5000);
        return () => clearInterval(interval);
    }, [loadAllData]);
    
    useEffect(() => {
        const filtered = tradeHistory.filter(trade => 
            trade.symbol.toLowerCase().includes(searchQuery.toLowerCase())
        );
        setFilteredHistory(filtered);
    }, [searchQuery, tradeHistory]);

    // ... Diğer tüm handle fonksiyonları (değişiklik olmadan) ...
    const handleAnalysis = useCallback(async ({ symbol, timeframe }) => { /* ... */ }, [runAnalysis, showToast]);
    const handleConfirmTrade = useCallback(async (tradeData) => { /* ... */ }, [openPosition, showToast, loadAllData]);
    const handleRunScan = useCallback(async () => { /* ... */ }, [runProactiveScan, showToast]);
    const handleSaveSettings = useCallback(async (newSettings) => { /* ... */ }, [saveSettings, showToast, loadAllData]);
    const handleAttemptClosePosition = useCallback((symbol) => { /* ... */ }, []);
    const handleClosePosition = useCallback(async (symbol) => { /* ... */ }, [closePosition, showToast, loadAllData]);
    const handleRefreshPnl = useCallback(async (symbol) => { /* ... */ }, [refreshPnl, showToast, loadAllData]);
    const handleReanalyze = useCallback(async (symbol) => { /* ... */ }, [reanalyzePosition, showToast]);
    const handleConfirmTradeFromScanner = useCallback(async (tradeData) => { /* ... */ }, [openPosition, showToast, loadAllData]);

    if (!isDataLoaded) { return ( <div className="bg-gray-900 min-h-screen flex justify-center items-center text-white p-4"><div className="text-center"><Loader2 className="animate-spin text-white mx-auto" size={48} /><p className="mt-4 text-gray-400">Veriler ilk kez yükleniyor, lütfen bekleyin...</p></div></div> ); }

    return (
        <>
            <Header appVersion={settings.APP_VERSION || "4.3.0"} onSettingsClick={() => setIsSettingsModalVisible(true)} isLoading={isLoading && !isDataLoaded} />
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                {/* ... NewAnalysis ve ProactiveScanner ... */}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6 mb-8">
                <StatCard title="Toplam P&L" isLoading={isLoading} value={`${(stats.total_pnl || 0).toFixed(2)} USDT`} valueClassName={(stats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'} tooltip="Tüm kapalı işlemlerden elde edilen net kâr/zarar." />
                <StatCard title="Kâr Faktörü" isLoading={isLoading} value={(stats.profit_factor || 0).toFixed(2)} valueClassName={(stats.profit_factor || 0) >= 1 ? 'text-green-400' : 'text-red-400'} tooltip="Toplam kârın toplam zarara oranı. 1'den büyük olması istenir."/>
                <StatCard title="Maks. Düşüş" isLoading={isLoading} value={`${(stats.max_drawdown || 0).toFixed(2)} USDT`} valueClassName="text-yellow-400" tooltip="Hesabın zirveden gördüğü en büyük düşüş miktarı." />
                <StatCard title="Kazanma Oranı" isLoading={isLoading} value={`${(stats.win_rate || 0).toFixed(2)}%`} tooltip="Kârlı kapatılan işlemlerin toplam işlemlere oranı."/>
                <StatCard title="Ort. Pozisyon Süresi" isLoading={isLoading} value={formatHoldingPeriod(stats.avg_holding_seconds || 0)} tooltip="Bir pozisyonun ortalama açık kalma süresi." />
                <StatCard title="Aktif AI Modeli" isLoading={isLoading} value={stats.active_model || "..."} valueClassName="text-sky-400 text-lg" icon={<Cpu size={20} className="text-gray-500" />} tooltip="Analizler için o an kullanılan AI modeli."/>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
                <PnlChart chartData={chartData} isLoading={isLoading && !isDataLoaded} />
                {/* ... ActivePositions ... */}
            </div>

            <PerformanceCharts bySymbol={performanceData.bySymbol} byWeek={performanceData.byWeek} isLoading={isLoading && !isDataLoaded} />
            
            <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold text-white">İşlem Geçmişi</h2>
                    <div className="flex items-center gap-2">
                        <input type="text" placeholder="Sembol ara..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-white placeholder-gray-500 w-40"/>
                    </div>
                </div>
                <TradeHistory history={filteredHistory} isLoading={isLoading && !isDataLoaded} onRowClick={handleChartModalOpen} />
            </div>

            <LogPanel logs={logs} isLoading={isLoading && !isDataLoaded} />

            {/* ... Modals ... */}
        </>
    );
};
