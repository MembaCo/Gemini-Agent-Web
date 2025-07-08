import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend, ArcElement, BarElement } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Settings, Search, Play, Loader2, Cpu, Terminal, Zap, Wallet, ShieldX, DollarSign, Brain, AlertTriangle, RefreshCw, Bot, X, Save, HelpCircle, ChevronsUpDown, ChevronDown, BotMessageSquare, Wrench, Shield, CandlestickChart, Telescope } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import TradeHistory from './TradeHistory';
import { TradeChartModal } from './TradeChartModal';
import { Modal, Switch, TooltipWrapper, AnalysisResultModal, ReanalysisResultModal, ConfirmationModal, ProactiveScanResultsModal, BulkReanalysisResultModal } from './SharedComponents';

// ChartJS Gerekli Modüller
ChartJS.register( CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend, ArcElement, BarElement );

// --- YARDIMCI BİLEŞENLER VE FONKSİYONLAR ---

const Header = ({ appVersion, onSettingsClick, isLoading }) => (
    <header className="mb-8 flex justify-between items-center">
        <div>
            <h1 className="text-3xl md:text-4xl font-bold text-white">Gemini Trading Agent</h1>
            <p className="text-gray-400 mt-1">v{appVersion} - Canlı Performans Paneli</p>
        </div>
        <button onClick={onSettingsClick} disabled={isLoading} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            <Settings size={24} />
        </button>
    </header>
);

const StatCard = ({ title, value, isLoading, valueClassName = '', icon, tooltip }) => (
    <div className="bg-gray-800 p-4 sm:p-5 rounded-xl border border-gray-700 shadow-lg transition-transform hover:scale-105">
        <div className="flex justify-between items-start">
            <h2 className="text-gray-400 text-sm font-medium">{title}</h2>
            {tooltip && <TooltipWrapper content={tooltip}>{icon}</TooltipWrapper>}
        </div>
        {isLoading ? <div className="animate-pulse bg-gray-700 h-8 w-3/4 mt-2 rounded-md"></div> : <p className={`text-2xl font-semibold mt-1 ${valueClassName}`} dangerouslySetInnerHTML={{ __html: value }}></p>}
    </div>
);

const PnlChart = ({ chartData, isLoading }) => {
    const options = { responsive: true, maintainAspectRatio: false, scales: { x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#9ca3af' } }, y: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#9ca3af', callback: (value) => `${value} $` } } }, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1f2937', titleFont: { size: 14 }, bodyFont: { size: 12 }, padding: 10, cornerRadius: 6 } } };
    const sortedData = [...(chartData || [])].sort((a, b) => new Date(a.x) - new Date(b.x));
    const data = { labels: sortedData.map(d => new Date(d.x).toLocaleDateString('tr-TR')), datasets: [{ label: 'Kümülatif P&L (USDT)', data: sortedData.map(d => d.y), borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.2)', fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: '#38bdf8' }] };
    return ( <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 lg:col-span-2 h-96"><h2 className="text-lg font-semibold text-white mb-4">Kümülatif P&L Zaman Çizelgesi</h2><div className="relative h-72">{isLoading ? <div className="flex justify-center items-center h-full"><Loader2 className="animate-spin mx-auto text-white" size={40} /></div> : <Line options={options} data={data} />}</div></div> );
};

const LogPanel = ({ logs, isLoading }) => {
    const logContainerRef = useRef(null);
    useEffect(() => { if (logContainerRef.current) { logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight; } }, [logs]);
    return ( <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 mt-8"><h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Terminal />Canlı Sistem Olayları</h2><div ref={logContainerRef} className="bg-black/50 rounded-md p-4 font-mono text-xs text-gray-300 h-64 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-black/50">{isLoading ? <p>Loglar yükleniyor...</p> : logs.length > 0 ? logs.map(log => { const levelColor = log.level === 'CRITICAL' ? 'text-red-500' : log.level === 'ERROR' ? 'text-red-400' : log.level === 'WARNING' ? 'text-yellow-400' : log.level === 'SUCCESS' ? 'text-green-400' : 'text-gray-500'; return (<div key={log.id}><span className="text-gray-600">{new Date(log.timestamp).toLocaleTimeString('tr-TR')} | </span><span className={`${levelColor} font-bold`}>{log.category}</span>: <span className="text-gray-300">{log.message}</span></div>); }) : <p className="text-center text-gray-500 pt-20">Henüz sistem olayı kaydedilmedi.</p>}</div></div> );
};

const NewAnalysis = ({ onAnalyze, isAnalyzing, symbol, setSymbol, timeframe, setTimeframe }) => (
    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Zap />Yeni Analiz Başlat</h3>
        <form onSubmit={(e) => { e.preventDefault(); onAnalyze({ symbol, timeframe }); }} className="flex flex-col sm:flex-row gap-3">
            <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="Sembol girin (örn: BTC)" className="flex-grow bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="15m">15 Dakika</option><option value="1h">1 Saat</option><option value="4h">4 Saat</option><option value="1d">1 Gün</option>
            </select>
            <button type="submit" disabled={isAnalyzing} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded-md flex justify-center items-center gap-2 disabled:bg-gray-600 disabled:cursor-not-allowed">
                {isAnalyzing ? <Loader2 className="animate-spin" size={20}/> : <Search size={20}/>} Analiz Et
            </button>
        </form>
    </div>
);

const ProactiveScanner = ({ onScan, isScanning }) => (
    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">Proaktif Tarayıcı</h3>
        <div className="flex justify-between items-center">
            <p className="text-sm text-gray-400 max-w-md">Piyasayı potansiyel ticaret fırsatları için manuel olarak tarar.</p>
            <button onClick={onScan} disabled={isScanning} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-5 py-2 rounded-md flex justify-center items-center gap-2 disabled:bg-gray-600 disabled:cursor-not-allowed min-w-[150px]">
                {isScanning ? <Loader2 className="animate-spin" size={20}/> : <Play size={20}/>} Taramayı Başlat
            </button>
        </div>
    </div>
);

const RiskIndicator = ({ current, sl, tp, side }) => {
    if (!sl || !tp || !current || sl === tp) return <div className="h-1.5 bg-gray-700 rounded-full my-2"></div>;
    const lowerBound = side === 'buy' ? sl : tp;
    const upperBound = side === 'buy' ? tp : sl;
    const totalRange = upperBound - lowerBound;
    if (totalRange <= 0) return <div className="h-1.5 bg-gray-700 rounded-full my-2"></div>;
    let progress = ((current - lowerBound) / totalRange) * 100;
    progress = Math.max(0, Math.min(100, progress));

    return (
        <div className="w-full mt-3 mb-2">
            <div className="relative h-1.5 bg-gray-700 rounded-full">
                <div className="absolute h-1.5 bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full" style={{ width: '100%' }}></div>
                <TooltipWrapper content={`Anlık Fiyat: ${current.toFixed(4)}`}>
                    <div className="absolute top-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-white rounded-full border-2 border-gray-900 shadow-lg" style={{ left: `calc(${progress}% - 7px)` }}></div>
                </TooltipWrapper>
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span className="font-mono">{sl.toFixed(4)}</span>
                <span className="font-mono">{tp.toFixed(4)}</span>
            </div>
        </div>
    );
};

const ActivePositions = ({ positions, onClose, onRefresh, onReanalyze, refreshingSymbol, analyzingSymbol, onGroupAction, isLoadingAction }) => (
    <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700 h-96 flex flex-col">
        <div className="flex-shrink-0 flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-white">Aktif Pozisyonlar ({positions.length})</h2>
            <details className="relative">
                <summary className="p-2 hover:bg-gray-700 rounded-md cursor-pointer list-none flex items-center gap-1 text-sm text-gray-300">
                    <ChevronsUpDown size={16} /> Eylemler
                </summary>
                <div className="absolute top-full right-0 mt-2 w-56 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl z-20">
                    <button onClick={() => onGroupAction('reanalyze-all')} disabled={isLoadingAction} className="w-full text-left flex items-center gap-3 px-4 py-2 text-sm hover:bg-gray-700/80 disabled:opacity-50"><Brain size={16} /> Toplu Analiz</button>
                    <button onClick={() => onGroupAction('close-profitable')} disabled={isLoadingAction} className="w-full text-left flex items-center gap-3 px-4 py-2 text-sm text-green-400 hover:bg-gray-700/80 disabled:opacity-50"><DollarSign size={16} /> Kârı Al</button>
                    <button onClick={() => onGroupAction('close-losing')} disabled={isLoadingAction} className="w-full text-left flex items-center gap-3 px-4 py-2 text-sm text-yellow-400 hover:bg-gray-700/80 disabled:opacity-50"><AlertTriangle size={16} /> Zararı Kes</button>
                    <button onClick={() => onGroupAction('close-all')} disabled={isLoadingAction} className="w-full text-left flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-gray-700/80 disabled:opacity-50"><ShieldX size={16} /> Tümünü Kapat</button>
                </div>
            </details>
        </div>
        <div className="flex-grow space-y-3 overflow-y-auto pr-2 -mr-2 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
            {positions.length > 0 ? positions.map(pos => (
                <div key={pos.symbol} className={`p-4 rounded-lg bg-gray-900/50 border border-gray-700/80 border-l-4 ${pos.pnl >= 0 ? 'border-l-green-500' : 'border-l-red-500'}`}>
                    <div className="flex justify-between items-start">
                        <div className="font-bold text-white text-lg">{pos.symbol}</div>
                        <div className={`px-2 py-0.5 text-xs rounded-full font-semibold ${pos.side === 'buy' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{pos.side.toUpperCase()}</div>
                    </div>
                    <div className={`text-2xl font-bold my-2 ${pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {pos.pnl.toFixed(2)} USDT
                        <span className="text-base font-medium ml-2 text-gray-400">({pos.pnl_percentage.toFixed(2)}%)</span>
                    </div>
                    <RiskIndicator current={pos.current_price} sl={pos.stop_loss} tp={pos.take_profit} side={pos.side} />
                    <div className="text-xs text-gray-400 grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
                        <span>Giriş: <span className="font-mono text-gray-200">{pos.entry_price.toFixed(4)}</span></span>
                        <span>Miktar: <span className="font-mono text-gray-200">{pos.amount.toFixed(3)}</span></span>
                    </div>
                    <div className="flex items-center gap-2 mt-4">
                        <button onClick={() => onClose(pos.symbol)} className="flex-1 bg-red-600/80 hover:bg-red-600 text-white text-xs font-semibold py-1.5 rounded-md">POZİSYONU KAPAT</button>
                        <TooltipWrapper content="Yeniden Analiz Et"><button onClick={() => onReanalyze(pos.symbol)} disabled={analyzingSymbol === pos.symbol} className="p-1.5 hover:bg-gray-700 rounded-md disabled:opacity-50">{analyzingSymbol === pos.symbol ? <Loader2 size={16} className="animate-spin"/> : <Bot size={16} />}</button></TooltipWrapper>
                        <TooltipWrapper content="P&L Yenile"><button onClick={() => onRefresh(pos.symbol)} disabled={refreshingSymbol === pos.symbol} className="p-1.5 hover:bg-gray-700 rounded-md disabled:opacity-50">{refreshingSymbol === pos.symbol ? <Loader2 size={16} className="animate-spin"/> : <RefreshCw size={16}/>}</button></TooltipWrapper>
                    </div>
                </div>
            )) : <div className="h-full flex items-center justify-center"><p className="text-center text-gray-500">Aktif pozisyon bulunmuyor.</p></div>}
        </div>
    </div>
);

// ===================================================================================
// YENİ: AYARLAR MODALİ İÇİN YENİDEN DÜZENLENMİŞ VERİ YAPILARI VE BİLEŞENLER
// ===================================================================================

const settingLabelsAndDescriptions = {
    GEMINI_MODEL: { label: "Ana AI Modeli", description: "Ana analizler için kullanılacak varsayılan Gemini AI modeli." },
    GEMINI_MODEL_FALLBACK_ORDER: { label: "Yedek Model Sırası", description: "Bir modelin kotası dolduğunda denenecek yedek modellerin sıralı listesi (virgülle ayırın)." },
    LIVE_TRADING: { label: "Canlı Ticaret Modu", description: "Aktifse, bot gerçek para ile işlem yapar. Değilse, sadece simülasyon yapar." },
    VIRTUAL_BALANCE: { label: "Sanal Bakiye (USDT)", description: "Simülasyon modunda (LIVE_TRADING kapalıyken) kullanılacak olan sanal bakiye." },
    DEFAULT_MARKET_TYPE: { label: "Piyasa Tipi", description: "İşlemlerin yapılacağı piyasa tipi. 'future' (vadeli) veya 'spot'." },
    DEFAULT_ORDER_TYPE: { label: "Varsayılan Emir Tipi", description: "Varsayılan emir tipi. 'LIMIT' veya 'MARKET'." },
    USE_MTA_ANALYSIS: { label: "Çoklu Zaman Aralığı (MTA) Analizi", description: "Manuel ve proaktif analizlerde Çoklu Zaman Aralığı (MTA) analizi kullanılsın mı?" },
    MTA_TREND_TIMEFRAME: { label: "MTA Ana Trend Zaman Aralığı", description: "MTA için ana trendin belirleneceği üst zaman aralığı (örn: 4h, 1d)." },
    LEVERAGE: { label: "Kaldıraç Oranı", description: "Vadeli işlemlerde kullanılacak kaldıraç oranı." },
    RISK_PER_TRADE_PERCENT: { label: "İşlem Başına Risk (%)", description: "Her bir işlemde toplam sermayenin yüzde kaçının riske edileceği." },
    MAX_CONCURRENT_TRADES: { label: "Maksimum Eşzamanlı İşlem", description: "Aynı anda açık olabilecek maksimum pozisyon sayısı." },
    USE_ATR_FOR_SLTP: { label: "ATR ile SL/TP Belirleme", description: "Zarar Durdur (SL) ve Kâr Al (TP) seviyelerini belirlemek için ATR göstergesi kullanılsın mı?" },
    ATR_MULTIPLIER_SL: { label: "ATR Çarpanı (SL)", description: "Stop-Loss mesafesini belirlemek için ATR değerinin çarpılacağı katsayı." },
    RISK_REWARD_RATIO_TP: { label: "Risk/Ödül Oranı (TP)", description: "Kâr Al (TP) seviyesinin, riske (SL mesafesi) göre oranı." },
    USE_SCALP_EXIT: { label: "Hızlı Kâr Alma (Scalp)", description: "Aktifse, pozisyonlar aşağıda belirlenen kâr yüzdesine ulaştığında diğer kuralları beklemeden hemen kapatılır." },
    SCALP_EXIT_PROFIT_PERCENT: { label: "Hızlı Kâr Alma Hedefi (%)", description: "Hızlı Kâr Alma (Scalp Exit) özelliğinin tetikleneceği kâr yüzdesi." },
    USE_TRAILING_STOP_LOSS: { label: "İz Süren Zarar Durdurma", description: "İz Süren Zarar Durdurma stratejisi aktif edilsin mi?" },
    TRAILING_STOP_ACTIVATION_PERCENT: { label: "İz Süren SL Aktivasyon Kârı (%)", description: "Pozisyonun yüzde kaç kâra geçtiğinde Trailing SL'nin devreye gireceği." },
    USE_PARTIAL_TP: { label: "Kısmi Kâr Alma", description: "Kısmi Kâr Alma stratejisi aktif edilsin mi?" },
    PARTIAL_TP_TARGET_RR: { label: "Kısmi TP Hedefi (R)", description: "Kaç R'a ulaşıldığında (riskedilen miktar kadar kâr edildiğinde) kısmi kâr alınacağı." },
    PARTIAL_TP_CLOSE_PERCENT: { label: "Kısmi TP Kapatma Oranı (%)", description: "Kısmi kâr alınırken pozisyonun yüzde kaçının kapatılacağı." },
    USE_BAILOUT_EXIT: { label: "Akıllı Zarar Azaltma (Bailout)", description: "Aktifse, belirli bir zarara ulaşan pozisyonlar için 'Kurtarma Çıkışı' stratejisini devreye sokar." },
    BAILOUT_ARM_LOSS_PERCENT: { label: "Bailout Aktivasyon Zararı (%)", description: "Pozisyonun yüzde kaç zarara (-%) ulaştığında 'Kurtarma Çıkışı' özelliğinin tetikte beklemeye başlayacağı." },
    BAILOUT_RECOVERY_PERCENT: { label: "Bailout Toparlanma Oranı (%)", description: "Özellik devredeyken, fiyatın gördüğü en dip/tepe noktadan yüzde kaç toparlanma yaparsa pozisyonun kapatılacağı." },
    POSITION_CHECK_INTERVAL_SECONDS: { label: "Pozisyon Kontrol Sıklığı (sn)", description: "Arka plan görevinin aktif pozisyonları kaç saniyede bir kontrol edeceği." },
    ORPHAN_ORDER_CHECK_INTERVAL_SECONDS: { label: "Yetim Emir Kontrol Sıklığı (sn)", description: "Pozisyonu kapanmış ama hala açık kalmış emirleri (yetim emir) kontrol etme sıklığı (saniye)." },
    POSITION_SYNC_INTERVAL_SECONDS: { label: "Pozisyon Senkronizasyon Sıklığı (sn)", description: "Borsadaki pozisyonlarla veritabanını senkronize etme sıklığı (saniye)." },
    TELEGRAM_ENABLED: { label: "Telegram Bildirimleri", description: "Telegram bildirimleri aktif edilsin mi? (.env dosyasında token ve chat_id ayarlanmalıdır)." },
    PROACTIVE_SCAN_ENABLED: { label: "Proaktif Tarama Aktif", description: "Uygulama başladığında Proaktif Tarayıcı arka plan görevi çalışsın mı?" },
    PROACTIVE_SCAN_INTERVAL_SECONDS: { label: "Tarama Sıklığı (sn)", description: "Proaktif Tarayıcının iki tarama döngüsü arasında kaç saniye bekleyeceğini belirler." },
    PROACTIVE_SCAN_AUTO_CONFIRM: { label: "Otomatik İşlem Onayı", description: "Tarayıcı bir fırsat bulduğunda, kullanıcı onayı olmadan otomatik olarak işlem açar. Yüksek risklidir." },
    PROACTIVE_SCAN_BLACKLIST: { label: "Kara Liste (Coinler)", description: "Bu listedeki coinler (virgülle ayırın) taramalara asla dahil edilmez." },
    PROACTIVE_SCAN_WHITELIST: { label: "Beyaz Liste (Coinler)", description: "Bu listedeki coinler (virgülle ayırın) her tarama döngüsünde mutlaka analize dahil edilir." },
    PROACTIVE_SCAN_USE_VOLATILITY_FILTER: { label: "Volatilite Filtresi", description: "ATR kullanarak düşük volatiliteye sahip piyasalardaki sinyalleri filtreler." },
    PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT: { label: "Min. Volatilite Eşiği (%)", description: "Bir sinyalin geçerli olması için ATR değerinin, anlık fiyatın en az yüzde kaçı olması gerektiğini belirtir." },
    PROACTIVE_SCAN_USE_VOLUME_FILTER: { label: "Hacim Teyit Filtresi", description: "İşleme giriş sinyalinin, artan bir işlem hacmiyle teyit edilip edilmeyeceğini belirler." },
    PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER: { label: "Hacim Teyit Çarpanı", description: "Son mumun hacminin, geçmiş hacim ortalamasının kaç katı olması gerektiğini belirtir." }
};

const settingCategories = [
    { title: 'Yapay Zeka Ayarları', icon: <BotMessageSquare className="text-sky-400" />, keys: ['GEMINI_MODEL', 'GEMINI_MODEL_FALLBACK_ORDER', 'USE_MTA_ANALYSIS', 'MTA_TREND_TIMEFRAME'] },
    { title: 'Genel Ticaret & Risk Yönetimi', icon: <Shield className="text-green-400" />, keys: ['LIVE_TRADING', 'VIRTUAL_BALANCE', 'DEFAULT_MARKET_TYPE', 'DEFAULT_ORDER_TYPE', 'LEVERAGE', 'MAX_CONCURRENT_TRADES', 'RISK_PER_TRADE_PERCENT'] },
    { title: 'Kâr & Zarar Stratejileri', icon: <CandlestickChart className="text-amber-400" />, keys: ['USE_ATR_FOR_SLTP', 'ATR_MULTIPLIER_SL', 'RISK_REWARD_RATIO_TP', 'USE_SCALP_EXIT', 'SCALP_EXIT_PROFIT_PERCENT', 'USE_TRAILING_STOP_LOSS', 'TRAILING_STOP_ACTIVATION_PERCENT', 'USE_PARTIAL_TP', 'PARTIAL_TP_TARGET_RR', 'PARTIAL_TP_CLOSE_PERCENT', 'USE_BAILOUT_EXIT', 'BAILOUT_ARM_LOSS_PERCENT', 'BAILOUT_RECOVERY_PERCENT'] },
    { title: 'Proaktif Tarayıcı Ayarları', icon: <Telescope className="text-indigo-400" />, keys: ['PROACTIVE_SCAN_ENABLED', 'PROACTIVE_SCAN_INTERVAL_SECONDS', 'PROACTIVE_SCAN_AUTO_CONFIRM', 'PROACTIVE_SCAN_BLACKLIST', 'PROACTIVE_SCAN_WHITELIST', 'PROACTIVE_SCAN_USE_VOLATILITY_FILTER', 'PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT', 'PROACTIVE_SCAN_USE_VOLUME_FILTER', 'PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER'] },
    { title: 'Sistem & Otomasyon', icon: <Wrench className="text-gray-400" />, keys: ['POSITION_CHECK_INTERVAL_SECONDS', 'ORPHAN_ORDER_CHECK_INTERVAL_SECONDS', 'POSITION_SYNC_INTERVAL_SECONDS', 'TELEGRAM_ENABLED'] },
];

const SettingItem = ({ settingKey, value, onSettingsChange }) => {
    const { label, description } = settingLabelsAndDescriptions[settingKey] || { label: settingKey, description: 'Açıklama bulunamadı.' };
    const type = typeof value;

    const renderInput = () => {
        const selectOptions = { "GEMINI_MODEL": ["gemini-1.5-flash", "gemini-1.5-pro"], "DEFAULT_MARKET_TYPE": ["future", "spot"], "DEFAULT_ORDER_TYPE": ["LIMIT", "MARKET"], "MTA_TREND_TIMEFRAME": ["15m", "1h", "4h", "1d"] };
        // DÜZELTME: 'key' yerine 'settingKey' kullanılıyor.
        if (settingKey in selectOptions) { 
            return <select value={value} onChange={e => onSettingsChange(settingKey, e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                {selectOptions[settingKey].map(o => <option key={o} value={o}>{o}</option>)}
            </select>;
        }
        if (type === 'boolean') return <Switch checked={value} onChange={(checked) => onSettingsChange(settingKey, checked)} />;
        if (type === 'number') return <input type="number" step="0.1" value={value} onChange={e => onSettingsChange(settingKey, parseFloat(e.target.value) || 0)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-28 text-white text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />;
        if (Array.isArray(value)) return <input type="text" placeholder="Değerleri virgülle ayırın..." value={value.join(', ')} onChange={e => onSettingsChange(settingKey, e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(s => s))} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />;
        return <input type="text" value={value} onChange={e => onSettingsChange(settingKey, e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />;
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <div>
                <label className="text-gray-200 font-medium">{label}</label>
                <p className="text-xs text-gray-400 mt-1">{description}</p>
            </div>
            <div className="flex justify-start md:justify-end">
                {renderInput()}
            </div>
        </div>
    );
};

const SettingsModal = ({ isVisible, onClose, settingsData, onSave, onSettingsChange }) => {
    const [openCategory, setOpenCategory] = useState(settingCategories[0]?.title || null);

    if (!isVisible) return null;

    return (
        <Modal isVisible={isVisible} onClose={onClose} maxWidth="max-w-4xl">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2"><Settings /> Uygulama Ayarları</h2>
                <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700"><X size={24} /></button>
            </div>
            <div className="space-y-2 max-h-[65vh] overflow-y-auto pr-4 -mr-4 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
                {settingCategories.map(category => (
                    <div key={category.title} className="border border-gray-700 rounded-lg overflow-hidden">
                        <button
                            onClick={() => setOpenCategory(openCategory === category.title ? null : category.title)}
                            className="w-full flex justify-between items-center p-4 bg-gray-800 hover:bg-gray-700/50 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                {React.cloneElement(category.icon, { size: 20 })}
                                <span className="font-semibold text-white">{category.title}</span>
                            </div>
                            <ChevronDown className={`transform transition-transform ${openCategory === category.title ? 'rotate-180' : ''}`} />
                        </button>
                        {openCategory === category.title && (
                            <div className="p-4 md:p-6 bg-gray-900/50 space-y-6">
                                {Object.keys(settingsData)
                                    .filter(key => category.keys.includes(key))
                                    .sort()
                                    .map(key => (
                                        <SettingItem
                                            key={key}
                                            settingKey={key}
                                            value={settingsData[key]}
                                            onSettingsChange={onSettingsChange}
                                        />
                                    ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
            <div className="mt-8 flex justify-end">
                <button onClick={onSave} className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-md flex items-center gap-2">
                    <Save size={18} />Ayarları Kaydet ve Uygula
                </button>
            </div>
        </Modal>
    );
};


// --- ANA DASHBOARD BİLEŞENİ ---
export const DashboardPage = () => {
    const [stats, setStats] = useState({});
    const [chartData, setChartData] = useState([]);
    const [activePositions, setActivePositions] = useState([]);
    const [tradeHistory, setTradeHistory] = useState([]);
    const [filteredHistory, setFilteredHistory] = useState([]);
    const [searchQuery, setSearchQuery] = useState("");
    const [settings, setSettings] = useState({});
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDataLoaded, setIsDataLoaded] = useState(false);
    const [analysisSymbol, setAnalysisSymbol] = useState('BTC');
    const [analysisTimeframe, setAnalysisTimeframe] = useState('15m');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isScanning, setIsScanning] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [selectedTradeForChart, setSelectedTradeForChart] = useState(null);
    const [reanalysisResult, setReanalysisResult] = useState(null);
    const [proactiveOpportunities, setProactiveOpportunities] = useState([]);
    const [openingTradeSymbol, setOpeningTradeSymbol] = useState(null);
    const [refreshingSymbol, setRefreshingSymbol] = useState(null);
    const [analyzingSymbol, setAnalyzingSymbol] = useState(null);
    const [isSettingsModalVisible, setIsSettingsModalVisible] = useState(false);
    const [tempSettings, setTempSettings] = useState({});
    const [confirmationDetails, setConfirmationDetails] = useState(null);
    const [bulkReanalysisResults, setBulkReanalysisResults] = useState(null);
    const [isGroupActionLoading, setIsGroupActionLoading] = useState(false);

    const { showToast, fetchData, fetchPositions, fetchSettings, saveSettings, fetchEvents, runAnalysis, runProactiveScan, openPosition, closePosition, reanalyzePosition, refreshPnl, ...auth } = useAuth();

    const loadAllData = useCallback(async (showLoadingSpinner = false) => {
        if (showLoadingSpinner && !isDataLoaded) setIsLoading(true);
        try {
            const [dashboardData, positionsData, settingsData, eventsData] = await Promise.all([ fetchData(), fetchPositions(), fetchSettings(), fetchEvents() ]);
            setStats(dashboardData.stats || {});
            setChartData(dashboardData.chart_data?.points || []);
            setTradeHistory(dashboardData.trade_history || []);
            setActivePositions(positionsData.managed_positions || []);
            setSettings(settingsData || {});
            setTempSettings(settingsData || {});
            setLogs(eventsData.sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp)) || []);
            if (!isDataLoaded) setIsDataLoaded(true);
        } catch (err) { showToast(err.message, 'error'); } finally { if (showLoadingSpinner) setIsLoading(false); }
    }, [fetchData, fetchPositions, fetchSettings, fetchEvents, showToast, isDataLoaded]);

    useEffect(() => {
        loadAllData(true);
        let intervalId = null;
        if (!isSettingsModalVisible) {
            intervalId = setInterval(() => loadAllData(false), 5000);
        }
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [loadAllData, isSettingsModalVisible]);

    useEffect(() => { setFilteredHistory(tradeHistory.filter(t => t.symbol.toLowerCase().includes(searchQuery.toLowerCase()))); }, [searchQuery, tradeHistory]);

    const handleAnalysis = useCallback(async ({ symbol, timeframe }) => { setIsAnalyzing(true); showToast(`${symbol} için analiz başlatıldı...`, 'info'); try { const result = await runAnalysis({ symbol, timeframe }); setAnalysisResult(result); } catch (err) { showToast(err.message, 'error'); } finally { setIsAnalyzing(false); } }, [runAnalysis, showToast]);
    const handleRunScan = useCallback(async () => { setIsScanning(true); showToast('Proaktif tarama tetiklendi...', 'info'); try { const result = await runProactiveScan(); const opportunities = result.details?.filter(d => d.type === 'opportunity').map(d => d.data) || []; if (opportunities.length > 0) { setProactiveOpportunities(opportunities); showToast(`${opportunities.length} yeni fırsat bulundu!`, 'success'); } else { showToast('Tarama tamamlandı, yeni fırsat bulunamadı.', 'info'); } await loadAllData(); } catch (err) { showToast(err.message, 'error'); } finally { setIsScanning(false); } }, [runProactiveScan, showToast, loadAllData]);
    const handleConfirmTrade = useCallback(async (tradeData) => { setOpeningTradeSymbol(tradeData.symbol); try { await openPosition({ symbol: tradeData.symbol, recommendation: tradeData.recommendation, timeframe: tradeData.timeframe, price: tradeData.data.price, }); showToast('Pozisyon başarıyla açıldı!', 'success'); setAnalysisResult(null); setProactiveOpportunities(prev => prev.filter(p => p.symbol !== tradeData.symbol)); await loadAllData(); } catch (err) { showToast(err.message, 'error'); } finally { setOpeningTradeSymbol(null); } }, [openPosition, showToast, loadAllData]);
    const handleAttemptClosePosition = (symbol) => setConfirmationDetails({ title: 'Pozisyonu Kapat', message: `${symbol} pozisyonunu manuel olarak kapatmak istediğinizden emin misiniz?`, onConfirm: () => handleClosePosition(symbol) });
    const handleClosePosition = useCallback(async (symbol) => { showToast(`${symbol} kapatılıyor...`, 'info'); try { await closePosition(symbol); showToast(`${symbol} başarıyla kapatıldı.`, 'success'); await loadAllData(); } catch (err) { showToast(err.message, 'error'); } finally { setConfirmationDetails(null); } }, [closePosition, showToast, loadAllData]);
    const handleRefreshPnl = useCallback(async (symbol) => { setRefreshingSymbol(symbol); try { await refreshPnl(symbol); await loadAllData(); } catch(err) { showToast(err.message, 'error');} finally { setRefreshingSymbol(null); }}, [refreshPnl, loadAllData, showToast]);
    const handleReanalyze = useCallback(async (symbol) => { setAnalyzingSymbol(symbol); showToast(`${symbol} yeniden analiz ediliyor...`, 'info'); try { const result = await reanalyzePosition(symbol); setReanalysisResult(result); } catch (err) { showToast(err.message, 'error'); } finally { setAnalyzingSymbol(null); } }, [reanalyzePosition, showToast]);
    const handleSaveSettings = async () => { showToast('Ayarlar kaydediliyor...', 'info'); try { await saveSettings(tempSettings); showToast('Ayarlar başarıyla kaydedildi.', 'success'); setIsSettingsModalVisible(false); await loadAllData(); } catch (err) { showToast(err.message, 'error'); }};
    const handleGroupAction = async (actionType) => { const actions = { 'close-all': { title: 'Tümünü Kapat', confirm: "Tüm açık pozisyonları kapatmak istediğinizden emin misiniz?", apiCall: auth.closeAllPositions }, 'close-profitable': { title: 'Kârı Al', confirm: "Kârda olan tüm pozisyonları kapatmak istediğinizden emin misiniz?", apiCall: auth.closeProfitablePositions }, 'close-losing': { title: 'Zararı Kes', confirm: "Zararda olan tüm pozisyonları kapatmak istediğinizden emin misiniz?", apiCall: auth.closeLosingPositions }, 'reanalyze-all': { title: 'Toplu Analiz', confirm: "Tüm açık pozisyonları AI ile yeniden analiz etmek istiyor musunuz? Bu işlem API kredisi kullanacaktır.", apiCall: async () => { const results = await auth.reanalyzeAllPositions(); setBulkReanalysisResults(results); } } }; const action = actions[actionType]; if (!action) return; setConfirmationDetails({ title: action.title, message: action.confirm, onConfirm: async () => { setConfirmationDetails(null); setIsGroupActionLoading(true); try { const result = await action.apiCall(); if(result?.message) showToast(result.message, 'info'); if(actionType !== 'reanalyze-all') { setTimeout(() => loadAllData(), 2000); } } catch (err) { showToast(err.message, 'error'); } finally { setIsGroupActionLoading(false); } } }); };

    if (!isDataLoaded) return ( <div className="bg-gray-900 min-h-screen flex justify-center items-center text-white"><Loader2 className="animate-spin text-white mr-4" size={48} />Veriler yükleniyor...</div> );

    return (
        <>
            <Header appVersion={settings.APP_VERSION || "4.3.0"} onSettingsClick={() => setIsSettingsModalVisible(true)} isLoading={isLoading && !isDataLoaded} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                <NewAnalysis onAnalyze={handleAnalysis} isAnalyzing={isAnalyzing} symbol={analysisSymbol} setSymbol={setAnalysisSymbol} timeframe={analysisTimeframe} setTimeframe={setAnalysisTimeframe}/>
                <ProactiveScanner onScan={handleRunScan} isScanning={isScanning} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <StatCard title="Güncel Bakiye" isLoading={isLoading} value={`${(stats.wallet_balance || 0).toFixed(2)} USDT`} valueClassName="text-blue-400" icon={<Wallet size={20} className="text-gray-500" />} tooltip="Borsadaki toplam vadeli işlem cüzdanı bakiyesi."/>
                <StatCard title="Toplam P&L" isLoading={isLoading} value={`${(stats.total_pnl || 0).toFixed(2)} USDT`} valueClassName={(stats.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'} />
                <StatCard title="Kazanma Oranı" isLoading={isLoading} value={`${(stats.win_rate || 0).toFixed(2)}%`} />
                <StatCard title="Aktif AI Modeli" isLoading={isLoading} value={stats.active_model || "..."} valueClassName="text-sky-400 text-lg" icon={<Cpu size={20} className="text-gray-500" />} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
                <PnlChart chartData={chartData} isLoading={isLoading && !isDataLoaded} />
                <ActivePositions positions={activePositions} onClose={handleAttemptClosePosition} onRefresh={handleRefreshPnl} onReanalyze={handleReanalyze} refreshingSymbol={refreshingSymbol} analyzingSymbol={analyzingSymbol} onGroupAction={handleGroupAction} isLoadingAction={isGroupActionLoading} />
            </div>
            <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
                <div className="flex justify-between items-center mb-4"><h2 className="text-lg font-semibold text-white">İşlem Geçmişi</h2><div className="flex items-center gap-2"><input type="text" placeholder="Sembol ara..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-white placeholder-gray-500 w-40"/></div></div>
                <TradeHistory history={filteredHistory} isLoading={isLoading && !isDataLoaded} onRowClick={(trade) => setSelectedTradeForChart(trade)} />
            </div>
            <LogPanel logs={logs} isLoading={isLoading && !isDataLoaded} />
            
            {/* Modal Pencereler */}
            <SettingsModal isVisible={isSettingsModalVisible} onClose={() => setIsSettingsModalVisible(false)} settingsData={tempSettings} onSave={handleSaveSettings} onSettingsChange={(key, value) => setTempSettings(prev => ({ ...prev, [key]: value }))} />
            <AnalysisResultModal result={analysisResult} isVisible={!!analysisResult} onClose={() => setAnalysisResult(null)} onConfirmTrade={handleConfirmTrade} isOpeningTrade={openingTradeSymbol === analysisResult?.symbol} />
            <TradeChartModal isVisible={!!selectedTradeForChart} onClose={() => setSelectedTradeForChart(null)} trade={selectedTradeForChart} />
            <ReanalysisResultModal result={reanalysisResult} isVisible={!!reanalysisResult} onClose={() => setReanalysisResult(null)} onConfirmClose={() => { setReanalysisResult(null); handleAttemptClosePosition(reanalysisResult.symbol); }} />
            <ProactiveScanResultsModal opportunities={proactiveOpportunities} isVisible={proactiveOpportunities.length > 0} onClose={() => setProactiveOpportunities([])} onConfirmTrade={handleConfirmTrade} openingTradeSymbol={openingTradeSymbol} />
            <BulkReanalysisResultModal results={bulkReanalysisResults} isVisible={!!bulkReanalysisResults} onClose={() => setBulkReanalysisResults(null)} onConfirmClose={handleAttemptClosePosition} />
            {confirmationDetails && <ConfirmationModal isVisible={!!confirmationDetails} onClose={() => setConfirmationDetails(null)} onConfirm={confirmationDetails.onConfirm} title={confirmationDetails.title}>{confirmationDetails.message}</ConfirmationModal>}
        </>
    );
};
