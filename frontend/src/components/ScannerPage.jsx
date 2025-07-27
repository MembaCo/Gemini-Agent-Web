import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ScanSearch, PlayCircle, Loader2, Bot, RefreshCw, SlidersHorizontal, X, Info, Save, Layers } from 'lucide-react';
import { Modal, Switch, TooltipWrapper, AnalysisResultModal } from './SharedComponents';

// --- YENİ VE KAPSAMLI AYAR TANIMLAMALARI ---
const scannerSettingDefinitions = {
    // Aday Kaynakları
    'PROACTIVE_SCAN_USE_GAINERS_LOSERS': {
        label: "En Çok Yükselen/Düşenleri Kullan",
        description: "Aday listesine, borsanın anlık 'En Çok Değer Kazananlar' ve 'En Çok Değer Kaybedenler' listesindeki coinleri dahil eder."
    },
    'PROACTIVE_SCAN_TOP_N': {
        label: "Yükselen/Düşen Listesi Limiti",
        description: "'En Çok Yükselen/Düşenler' listesinden kaç adet coinin taramaya dahil edileceğini belirler."
    },
    'PROACTIVE_SCAN_USE_VOLUME_SPIKE': {
        label: "Hacim Patlamalarını Kullan",
        description: "Aday listesine, işlem hacminde ani ve anormal bir artış yaşayan ('Hacim Patlaması') coinleri dahil eder."
    },
    'PROACTIVE_SCAN_VOLUME_TIMEFRAME': {
        label: "Hacim Analizi Zaman Aralığı",
        description: "Hacim patlaması analizinin hangi zaman aralığındaki mumlara göre yapılacağını belirler (örn: 1h, 4h)."
    },
    'PROACTIVE_SCAN_VOLUME_PERIOD': {
        label: "Hacim Ortalaması Periyodu",
        description: "Son mumun hacminin, geçmiş kaç mumun ortalamasıyla karşılaştırılacağını belirler."
    },
    'PROACTIVE_SCAN_VOLUME_MULTIPLIER': {
        label: "Hacim Patlaması Çarpanı",
        description: "Son mumun hacminin, geçmiş hacim ortalamasının en az kaç katı olması gerektiğini belirtir."
    },
    'PROACTIVE_SCAN_MIN_VOLUME_USDT': {
        label: "Minimum 24s Hacim (USDT)",
        description: "Taranacak coinler için minimum 24 saatlik işlem hacmi. Düşük hacimli coinleri filtreler."
    },
    'PROACTIVE_SCAN_BLACKLIST': {
        label: "Kara Liste (Virgülle Ayırın)",
        description: "Bu listedeki coinler, diğer tüm koşulları sağlasalar bile taramalara asla dahil edilmez."
    },
    'PROACTIVE_SCAN_WHITELIST': {
        label: "Beyaz Liste (Virgülle Ayırın)",
        description: "Bu listedeki coinler, başka hiçbir koşula bakılmaksızın her tarama döngüsünde mutlaka analize dahil edilir."
    },
    // AI Öncesi Teknik Filtreleme
    'PROACTIVE_SCAN_PREFILTER_ENABLED': {
        label: "AI Öncesi Teknik Filtreleme Aktif",
        description: "Adayları AI'a göndermeden önce RSI, ADX gibi temel göstergelere göre bir ön eleme yapar. API maliyetlerini düşürür."
    },
    'PROACTIVE_SCAN_RSI_LOWER': {
        label: "Ön Filtre RSI Alt Sınır",
        description: "Teknik filtreleme için RSI'ın altında olması gereken değer (örn: 35)."
    },
    'PROACTIVE_SCAN_RSI_UPPER': {
        label: "Ön Filtre RSI Üst Sınır",
        description: "Teknik filtreleme için RSI'ın üstünde olması gereken değer (örn: 65)."
    },
    'PROACTIVE_SCAN_ADX_THRESHOLD': {
        label: "Ön Filtre ADX Eşiği",
        description: "Teknik filtreleme için ADX'in üzerinde olması gereken trend gücü değeri (örn: 20)."
    },
    'PROACTIVE_SCAN_USE_VOLATILITY_FILTER': { 
        label: "Volatilite Filtresi (ATR)",
        description: "ATR kullanarak düşük volatiliteye sahip, durgun piyasalardaki sinyalleri filtreler."
    },
    'PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT': {
        label: "Min. Volatilite Eşiği (%)",
        description: "Bir sinyalin geçerli olması için ATR değerinin, anlık fiyatın en az yüzde kaçı olması gerektiğini belirtir."
    },
    'PROACTIVE_SCAN_USE_VOLUME_FILTER': { 
        label: "Hacim Teyit Filtresi",
        description: "İşleme giriş sinyalinin, artan bir işlem hacmiyle teyit edilip edilmeyeceğini belirler."
    },
    'PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER': {
        label: "Hacim Teyit Çarpanı",
        description: "Son mumun hacminin, geçmiş ortalama hacmin en az kaç katı olması gerektiğini belirtir."
    },
    // Genel Otomasyon ve Analiz
    'PROACTIVE_SCAN_MTA_ENABLED': {
        label: "Çoklu Zaman Aralığı (MTA) Analizi",
        description: "Tarayıcı analizlerinde Çoklu Zaman Aralığı (MTA) analizi kullanılsın mı?"
    },
    'PROACTIVE_SCAN_ENTRY_TIMEFRAME': {
        label: "Giriş Sinyali Zaman Aralığı",
        description: "Tarayıcının ana sinyalleri arayacağı zaman aralığı (örn: 15m)."
    },
    'PROACTIVE_SCAN_TREND_TIMEFRAME': {
        label: "Ana Trend Zaman Aralığı",
        description: "MTA için ana trendin belirleneceği üst zaman aralığı (örn: 4h)."
    }
};

const settingCategories = {
    'Aday Kaynakları': ['PROACTIVE_SCAN_USE_GAINERS_LOSERS', 'PROACTIVE_SCAN_TOP_N', 'PROACTIVE_SCAN_USE_VOLUME_SPIKE', 'PROACTIVE_SCAN_VOLUME_TIMEFRAME', 'PROACTIVE_SCAN_VOLUME_PERIOD', 'PROACTIVE_SCAN_VOLUME_MULTIPLIER', 'PROACTIVE_SCAN_MIN_VOLUME_USDT', 'PROACTIVE_SCAN_BLACKLIST', 'PROACTIVE_SCAN_WHITELIST'],
    'AI Öncesi Teknik Filtreleme': ['PROACTIVE_SCAN_PREFILTER_ENABLED', 'PROACTIVE_SCAN_RSI_LOWER', 'PROACTIVE_SCAN_RSI_UPPER', 'PROACTIVE_SCAN_ADX_THRESHOLD', 'PROACTIVE_SCAN_USE_VOLATILITY_FILTER', 'PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT', 'PROACTIVE_SCAN_USE_VOLUME_FILTER', 'PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER'],
    'Genel Analiz Ayarları': ['PROACTIVE_SCAN_MTA_ENABLED', 'PROACTIVE_SCAN_ENTRY_TIMEFRAME', 'PROACTIVE_SCAN_TREND_TIMEFRAME']
};

const ScannerSettingsModal = ({ settings, isVisible, onClose, onSave, onSettingsChange }) => {
    if (!isVisible) return null;

    const renderInput = (key, value) => {
        const selectOptions = { 
            "PROACTIVE_SCAN_VOLUME_TIMEFRAME": ["15m", "1h", "4h", "1d"],
            "PROACTIVE_SCAN_ENTRY_TIMEFRAME": ["5m", "15m", "1h", "4h"],
            "PROACTIVE_SCAN_TREND_TIMEFRAME": ["1h", "4h", "1d"],
        };
        if (key in selectOptions) {
            return <select value={value} onChange={e => onSettingsChange(key, e.target.value)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                {selectOptions[key].map(o => <option key={o} value={o}>{o}</option>)}
            </select>;
        }
        if (typeof value === 'boolean') {
            return <Switch checked={value} onChange={(checked) => onSettingsChange(key, checked)} />;
        }
        if (typeof value === 'number') {
            return <input type="number" step={key.includes('MULTIPLIER') || key.includes('PERCENT') ? "0.1" : "1"} value={value} onChange={e => onSettingsChange(key, parseFloat(e.target.value) || 0)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-28 text-white text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />;
        }
        if (Array.isArray(value)) {
            return <input type="text" placeholder="Değerleri virgülle ayırın..." value={value.join(', ')} onChange={e => onSettingsChange(key, e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(s => s))} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />;
        }
        return <input type="text" value={value} onChange={e => onSettingsChange(key, e.target.value)} className="bg-gray-700 border border-gray-600 rounded-md px-3 py-1 w-full text-white" />;
    };

    return (
        <Modal isVisible={isVisible} onClose={onClose} maxWidth="max-w-3xl">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2"><SlidersHorizontal/> Fırsat Tarayıcı Ayarları</h2>
                <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700"><X size={24} /></button>
            </div>
            <div className="space-y-6 max-h-[65vh] overflow-y-auto pr-4 -mr-4">
                {Object.entries(settingCategories).map(([category, keys]) => (
                    <div key={category}>
                        <h3 className="text-lg font-semibold text-sky-400 mb-4 border-b border-gray-700 pb-2">{category}</h3>
                        <div className="space-y-4">
                            {keys.filter(key => key in settings).map(key => (
                                <div key={key} className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
                                    <div>
                                        <label className="text-gray-200 font-medium">{scannerSettingDefinitions[key]?.label || key}</label>
                                        <p className="text-xs text-gray-400 mt-1">{scannerSettingDefinitions[key]?.description || ''}</p>
                                    </div>
                                    <div className="flex justify-start md:justify-end">
                                        {renderInput(key, settings[key])}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
            <div className="mt-8 flex justify-end border-t border-gray-700 pt-6">
                <button onClick={() => onSave(settings)} className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-md flex items-center gap-2">
                    <Save size={18}/> Ayarları Kaydet ve Uygula
                </button>
            </div>
        </Modal>
    );
};

export const ScannerPage = () => {
    const { showToast, runInteractiveScan, fetchScannerCandidates, refreshScannerCandidate, runAnalysis, fetchSettings, saveSettings, openPosition } = useAuth();
    const [isScanning, setIsScanning] = useState(false);
    const [isFetchingInitial, setIsFetchingInitial] = useState(true);
    const [loadingStage, setLoadingStage] = useState('');
    const [candidates, setCandidates] = useState([]);
    const [analyzingSymbol, setAnalyzingSymbol] = useState(null);
    const [refreshingSymbol, setRefreshingSymbol] = useState(null);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isSettingsModalVisible, setIsSettingsModalVisible] = useState(false);
    const [scannerSettings, setScannerSettings] = useState({});
    const [isOpeningTrade, setIsOpeningTrade] = useState(false);
    const [isBulkRefreshing, setIsBulkRefreshing] = useState(false);

    const loadScannerSettings = useCallback(async () => {
        try {
            const allSettings = await fetchSettings();
            const filteredSettings = Object.keys(allSettings)
                .filter(key => key.startsWith('PROACTIVE_SCAN_'))
                .reduce((obj, key) => {
                    obj[key] = allSettings[key];
                    return obj;
                }, {});
            setScannerSettings(filteredSettings);
        } catch (error) {
            showToast("Tarayıcı ayarları alınamadı: " + error.message, "error");
        }
    }, [fetchSettings, showToast]);

    const handleSaveSettings = useCallback(async (newSettings) => {
        showToast('Tarayıcı ayarları kaydediliyor...', 'info');
        try {
            await saveSettings(newSettings);
            showToast('Tarayıcı ayarları başarıyla kaydedildi.', 'success');
            setIsSettingsModalVisible(false);
            loadScannerSettings();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }, [saveSettings, showToast, loadScannerSettings]);

    const handleSettingsChange = (key, value) => {
        setScannerSettings(prev => ({...prev, [key]: value}));
    };

    const loadInitialData = useCallback(async () => {
        setIsFetchingInitial(true);
        try {
            await Promise.all([
                fetchScannerCandidates().then(setCandidates),
                loadScannerSettings()
            ]);
        } catch (error) {
            showToast(`Sayfa verileri yüklenemedi: ${error.message}`, 'error');
        } finally {
            setIsFetchingInitial(false);
        }
    }, [fetchScannerCandidates, loadScannerSettings, showToast]);

    useEffect(() => {
        loadInitialData();
    }, [loadInitialData]);
    
    const handleScan = async () => {
        setIsScanning(true);
        setCandidates([]);
        showToast('Yeni interaktif tarama başlatıldı...', 'info');
        setLoadingStage('Piyasa verileri çekiliyor...');
        try {
            const newCandidates = await runInteractiveScan();
            setCandidates(newCandidates);
            if (newCandidates.length > 0) {
                showToast(`${newCandidates.length} potansiyel aday bulundu.`, 'success');
            } else {
                showToast('Tarama tamamlandı ancak filtrelere uyan aday bulunamadı.', 'info');
            }
        } catch (error) {
            showToast(`Tarama sırasında bir hata oluştu: ${error.message}`, 'error');
        } finally {
            setIsScanning(false);
            setLoadingStage('');
        }
    };

    const handleBulkRefresh = useCallback(async () => {
        if (candidates.length === 0) {
            showToast("Yenilenecek aday bulunmuyor.", "warning");
            return;
        }
        setIsBulkRefreshing(true);
        showToast(`${candidates.length} adayın tümü yenileniyor...`, "info");

        const refreshPromises = candidates.map(candidate => refreshScannerCandidate(candidate.symbol));
        const results = await Promise.allSettled(refreshPromises);
        
        let successCount = 0;
        let errorCount = 0;
        const updatedCandidates = [...candidates];

        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                const refreshedData = result.value;
                const originalIndex = updatedCandidates.findIndex(c => c.symbol === refreshedData.symbol);
                if (originalIndex !== -1) {
                    updatedCandidates[originalIndex] = refreshedData;
                }
                successCount++;
            } else {
                console.error(`Toplu yenileme sırasında hata (${candidates[index].symbol}):`, result.reason);
                errorCount++;
            }
        });

        setCandidates(updatedCandidates);

        if (errorCount > 0) {
            showToast(`${successCount} aday yenilendi, ${errorCount} adayda hata oluştu.`, "warning");
        } else {
            showToast('Tüm adaylar başarıyla yenilendi.', "success");
        }
        setIsBulkRefreshing(false);
    }, [candidates, refreshScannerCandidate, showToast]);

    const handleRefresh = async (symbol) => { 
        setRefreshingSymbol(symbol); 
        try { 
            const refreshedData = await refreshScannerCandidate(symbol); 
            setCandidates(currentCandidates => currentCandidates.map(c => (c.symbol === symbol ? refreshedData : c))); 
            showToast(`${symbol} verileri yenilendi.`, 'success'); 
        } catch (error) { 
            showToast(`Yenileme hatası: ${error.message}`, 'error'); 
        } finally { 
            setRefreshingSymbol(null); 
        } 
    };
    
    const handleAnalyze = useCallback(async (candidate) => { 
        setAnalyzingSymbol(candidate.symbol); 
        try { 
            const result = await runAnalysis({ symbol: candidate.symbol, timeframe: candidate.timeframe }); 
            setAnalysisResult(result); 
        } catch (err) { 
            showToast(err.message, 'error'); 
        } finally { 
            setAnalyzingSymbol(null); 
        } 
    }, [runAnalysis, showToast]);

    const handleConfirmTrade = useCallback(async (tradeData) => { 
        setIsOpeningTrade(true); 
        showToast(`${tradeData.symbol} için pozisyon açılıyor...`, 'info'); 
        try { 
            const result = await openPosition({ 
                symbol: tradeData.symbol, 
                recommendation: tradeData.recommendation, 
                timeframe: tradeData.timeframe, 
                price: tradeData.data.price, 
            }); 
            showToast(result.message || 'Pozisyon başarıyla açıldı!', 'success'); 
            setAnalysisResult(null); 
        } catch (err) { 
            showToast(err.message, 'error'); 
        } finally { 
            setIsOpeningTrade(false); 
        } 
    }, [openPosition, showToast]);

    return (
        <div className="space-y-8">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-3"><ScanSearch size={24} /> İnteraktif Fırsat Tarayıcı</h2>
                        <p className="text-sm text-gray-400 mt-1">Piyasayı potansiyel fırsatlar için tarayın ve seçtiğiniz adayları AI ile analiz edin.</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <TooltipWrapper content="Tüm Tarayıcı Ayarları">
                            <button onClick={() => setIsSettingsModalVisible(true)} className="bg-gray-700 hover:bg-gray-600 text-white font-semibold p-2.5 rounded-md disabled:bg-gray-600/50 disabled:cursor-not-allowed" disabled={isScanning || isBulkRefreshing}>
                                <SlidersHorizontal size={20}/>
                            </button>
                        </TooltipWrapper>
                        <TooltipWrapper content="Listedeki Tüm Adayları Yenile">
                            <button onClick={handleBulkRefresh} disabled={isScanning || isBulkRefreshing || candidates.length === 0} className="bg-purple-600 hover:bg-purple-700 text-white font-semibold p-2.5 rounded-md disabled:bg-gray-600/50 disabled:cursor-not-allowed">
                                {isBulkRefreshing ? <Loader2 className="animate-spin" size={20}/> : <Layers size={20}/>}
                            </button>
                        </TooltipWrapper>
                        <button onClick={handleScan} disabled={isScanning || isBulkRefreshing} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-5 rounded-md flex justify-center items-center gap-2 disabled:bg-gray-600/50 disabled:cursor-not-allowed min-w-[200px]">
                            {isScanning ? <Loader2 className="animate-spin" size={20} /> : <PlayCircle size={20} />}
                            {isScanning ? loadingStage : 'Yeni Tarama Başlat'}
                        </button>
                    </div>
                </div>
            </div>
            <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Analize Hazır Adaylar ({candidates.length})</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left"><thead className="text-xs text-gray-400 uppercase bg-gray-700/50"><tr><th scope="col" className="px-4 py-3">Sembol</th><th scope="col" className="px-4 py-3">Kaynak</th><th scope="col" className="px-4 py-3">RSI</th><th scope="col" className="px-4 py-3">ADX</th><th scope="col" className="px-4 py-3">Son Güncelleme</th><th scope="col" className="px-4 py-3 text-center">Eylemler</th></tr></thead>
                        <tbody>
                            {(isFetchingInitial) && ( <tr><td colSpan="6" className="text-center p-8 text-gray-400"><Loader2 className="animate-spin text-white mx-auto mb-2" />Kayıtlı adaylar ve ayarlar yükleniyor...</td></tr> )}
                            {!isFetchingInitial && candidates.length === 0 && ( <tr><td colSpan="6" className="text-center p-8 text-gray-400">Kayıtlı aday bulunamadı. Yeni bir tarama başlatın.</td></tr> )}
                            {candidates.map(c => {
                                const isRowRefreshing = refreshingSymbol === c.symbol; const isRowAnalyzing = analyzingSymbol === c.symbol;
                                return ( <tr key={c.symbol} className="border-b border-gray-700 hover:bg-gray-900/30"><td className="px-4 py-3 font-medium text-white">{c.symbol}</td><td className="px-4 py-3 text-gray-400">{c.source}</td><td className={`px-4 py-3 font-semibold ${c.indicators.RSI > 65 ? 'text-red-400' : c.indicators.RSI < 35 ? 'text-green-400' : ''}`}>{c.indicators.RSI.toFixed(2)}</td><td className="px-4 py-3 text-blue-300">{c.indicators.ADX.toFixed(2)}</td><td className="px-4 py-3 text-gray-500 text-xs">{new Date(c.last_updated).toLocaleString('tr-TR')}</td><td className="px-4 py-3 text-center"><div className="flex justify-center items-center gap-2"><button onClick={() => handleAnalyze(c)} disabled={isRowAnalyzing || isRowRefreshing} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3 py-1 text-xs rounded-md flex items-center gap-1.5 disabled:bg-gray-600 disabled:cursor-not-allowed">{isRowAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Bot size={14} />}Analiz</button><button onClick={() => handleRefresh(c.symbol)} disabled={isRowRefreshing || isRowAnalyzing} className="p-1.5 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white disabled:bg-gray-600 disabled:cursor-not-allowed">{isRowRefreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}</button></div></td></tr> )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
            <AnalysisResultModal result={analysisResult} isVisible={!!analysisResult} onClose={() => setAnalysisResult(null)} onConfirmTrade={handleConfirmTrade} isOpeningTrade={isOpeningTrade}/>
            <ScannerSettingsModal settings={scannerSettings} isVisible={isSettingsModalVisible} onClose={() => setIsSettingsModalVisible(false)} onSave={handleSaveSettings} onSettingsChange={handleSettingsChange}/>
        </div>
    );
};