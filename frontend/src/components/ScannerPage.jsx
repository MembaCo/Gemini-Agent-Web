import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ScanSearch, PlayCircle, Loader2, Bot, RefreshCw, SlidersHorizontal, X, Info, Save } from 'lucide-react';
// === YENİ: Ortak bileşenleri yeni dosyadan import ediyoruz ===
import { Modal, Switch, TooltipWrapper, AnalysisResultModal } from './SharedComponents';

// Tarayıcı Ayarları için özel olarak oluşturulmuş Modal
const ScannerSettingsModal = ({ settings, isVisible, onClose, onSave, onSettingsChange }) => {
    const settingDefinitions = { 'PROACTIVE_SCAN_ENABLED': { description: "Aktifse, bot arka planda sürekli olarak piyasayı yeni işlem fırsatları için tarar." }, 'PROACTIVE_SCAN_INTERVAL_SECONDS': { description: "Proaktif Tarayıcının iki tarama döngüsü arasında kaç saniye bekleyeceğini belirler." }, 'PROACTIVE_SCAN_AUTO_CONFIRM': { description: "Tarayıcı bir fırsat bulduğunda, kullanıcı onayı olmadan otomatik olarak işlem açar. Yüksek risklidir." }, 'PROACTIVE_SCAN_USE_GAINERS_LOSERS': { description: "Tarama listesine Binance'in 'En Çok Yükselenler/Düşenler' listesini dahil eder." }, 'PROACTIVE_SCAN_TOP_N': { description: "Yükselenler/Düşenler listesinden kaç coinin analize dahil edileceği." }, 'PROACTIVE_SCAN_USE_VOLUME_SPIKE': { description: "Tarama listesine, işlem hacminde ani artış yaşayan ('Hacim Patlaması') coinleri dahil eder." }, 'PROACTIVE_SCAN_VOLUME_TIMEFRAME': { description: "Hacim analizi için kullanılacak zaman aralığı (örn: 1h, 4h)." }, 'PROACTIVE_SCAN_VOLUME_PERIOD': { description: "Hacim ortalaması için kaç mum geriye bakılacak." }, 'PROACTIVE_SCAN_VOLUME_MULTIPLIER': { description: "Son mumun hacmi, ortalamanın kaç katı olmalı." }, 'PROACTIVE_SCAN_MIN_VOLUME_USDT': { description: "Taranacak coinler için minimum 24 saatlik işlem hacmi (USDT cinsinden). Düşük hacimli coinleri filtreler." }, 'PROACTIVE_SCAN_BLACKLIST': { description: "Bu listedeki coinler (virgülle ayırın) taramalara asla dahil edilmez." }, 'PROACTIVE_SCAN_WHITELIST': { description: "Bu listedeki coinler (virgülle ayırın) her tarama döngüsünde mutlaka analize dahil edilir." }, };
    const renderInput = (key, value) => { if (typeof value === 'boolean') { return <Switch checked={value} onChange={(checked) => onSettingsChange(key, checked)} />; } if (typeof value === 'number') { return <input type="number" step={key.includes('PERCENT') ? "0.1" : "1"} value={value} onChange={e => onSettingsChange(key, parseFloat(e.target.value) || 0)} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-28 text-white text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />; } if (Array.isArray(value)) { return <input type="text" value={value.join(', ')} onChange={e => onSettingsChange(key, e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(s => s))} className="bg-gray-900 border border-gray-700 rounded-md px-3 py-1 w-full text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />; } return <input type="text" value={value} onChange={e => onSettingsChange(key, e.target.value)} className="bg-gray-700 border border-gray-600 rounded-md px-3 py-1 w-full text-white" />; };
    return ( <Modal isVisible={isVisible} onClose={onClose}><div className="flex justify-between items-center mb-6"><h2 className="text-2xl font-bold text-white flex items-center gap-2"><SlidersHorizontal/> Tarayıcı Ayarları</h2><button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700"><X size={24} /></button></div><div className="space-y-4 max-h-[60vh] overflow-y-auto pr-4">{Object.keys(settings).sort().map(key => ( <div key={key} className="flex justify-between items-center border-b border-gray-700/50 py-3 gap-4"><div className="flex items-center gap-2"><label className="text-gray-300 text-sm">{key}</label>{settingDefinitions[key] && ( <TooltipWrapper content={settingDefinitions[key].description}><Info size={14} className="text-gray-500 cursor-help" /></TooltipWrapper> )}</div>{renderInput(key, settings[key])}</div> ))}</div><div className="mt-6 flex justify-end"><button onClick={() => onSave(settings)} className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-md flex items-center gap-2"><Save size={18}/> Ayarları Kaydet ve Uygula</button></div></Modal> );
};

export const ScannerPage = () => {
    const { showToast, runScannerCandidates, fetchScannerCandidates, refreshScannerCandidate, runAnalysis, fetchSettings, saveSettings, openPosition } = useAuth();
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

    const loadScannerSettings = useCallback(async () => { try { const allSettings = await fetchSettings(); const filteredSettings = Object.keys(allSettings).filter(key => key.startsWith('PROACTIVE_SCAN_')).reduce((obj, key) => { obj[key] = allSettings[key]; return obj; }, {}); setScannerSettings(filteredSettings); } catch (error) { showToast("Tarayıcı ayarları alınamadı: " + error.message, "error"); } }, [fetchSettings, showToast]);
    const handleSaveSettings = useCallback(async (newSettings) => { showToast('Tarayıcı ayarları kaydediliyor...', 'info'); try { const result = await saveSettings(newSettings); showToast(result.message, 'success'); setIsSettingsModalVisible(false); loadScannerSettings(); } catch (err) { showToast(err.message, 'error'); } }, [saveSettings, showToast, loadScannerSettings]);
    const handleSettingsChange = (key, value) => { setScannerSettings(prev => ({...prev, [key]: value})); };
    const loadInitialData = useCallback(async () => { setIsFetchingInitial(true); try { await Promise.all([ (async () => { const initialCandidates = await fetchScannerCandidates(); setCandidates(initialCandidates); })(), loadScannerSettings() ]); } catch (error) { showToast(`Sayfa verileri yüklenemedi: ${error.message}`, 'error'); } finally { setIsFetchingInitial(false); } }, [fetchScannerCandidates, loadScannerSettings, showToast]);
    useEffect(() => { loadInitialData(); }, [loadInitialData]);
    const handleScan = async () => { setIsScanning(true); setCandidates([]); showToast('Yeni tarama başlatıldı...', 'info'); setLoadingStage('Piyasa verileri çekiliyor ve filtreleniyor...'); try { const result = await runScannerCandidates(); setCandidates(result.found_candidates); const foundCount = result.found_candidates.length; const scannedCount = result.total_scanned; if (foundCount > 0) { showToast(`${foundCount} potansiyel fırsat bulundu ve kaydedildi.`, 'success'); } else { showToast(`${scannedCount} aday tarandı ancak uygun fırsat bulunamadı.`, 'info'); } } catch (error) { showToast(`Tarama sırasında bir hata oluştu: ${error.message}`, 'error'); } finally { setIsScanning(false); setLoadingStage(''); } };
    const handleRefresh = async (symbol) => { setRefreshingSymbol(symbol); try { const refreshedData = await refreshScannerCandidate(symbol); setCandidates(currentCandidates => currentCandidates.map(c => (c.symbol === symbol ? refreshedData : c)) ); showToast(`${symbol} verileri yenilendi.`, 'success'); } catch (error) { showToast(`Yenileme hatası: ${error.message}`, 'error'); } finally { setRefreshingSymbol(null); } };
    const handleAnalyze = useCallback(async (candidate) => { setAnalyzingSymbol(candidate.symbol); try { const result = await runAnalysis({ symbol: candidate.symbol, timeframe: candidate.timeframe }); setAnalysisResult(result); } catch (err) { showToast(err.message, 'error'); } finally { setAnalyzingSymbol(null); } }, [runAnalysis, showToast]);
    const handleConfirmTrade = useCallback(async (tradeData) => { setIsOpeningTrade(true); showToast(`${tradeData.symbol} için pozisyon açılıyor...`, 'info'); try { const result = await openPosition({ symbol: tradeData.symbol, recommendation: tradeData.recommendation, timeframe: tradeData.timeframe, price: tradeData.data.price, }); showToast(result.message || 'Pozisyon başarıyla açıldı!', 'success'); setAnalysisResult(null); } catch (err) { showToast(err.message, 'error'); } finally { setIsOpeningTrade(false); } }, [openPosition, showToast]);

    return (
        <div className="space-y-8">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-3"><ScanSearch size={24} /> İnteraktif Fırsat Tarayıcı</h2>
                        <p className="text-sm text-gray-400 mt-1">Piyasayı potansiyel fırsatlar için tarayın ve seçtiğiniz adayları AI ile analiz edin.</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <button onClick={() => setIsSettingsModalVisible(true)} className="bg-gray-700 hover:bg-gray-600 text-white font-semibold p-2.5 rounded-md"><SlidersHorizontal size={20}/></button>
                        <button onClick={handleScan} disabled={isScanning} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-5 rounded-md flex justify-center items-center gap-2 disabled:bg-gray-600 disabled:cursor-not-allowed min-w-[200px]">{isScanning ? <Loader2 className="animate-spin" size={20} /> : <PlayCircle size={20} />}{isScanning ? loadingStage : 'Yeni Tarama Başlat'}</button>
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
                                return ( <tr key={c.symbol} className="border-b border-gray-700 hover:bg-gray-900/30"><td className="px-4 py-3 font-medium text-white">{c.symbol}</td><td className="px-4 py-3 text-gray-400">{c.source}</td><td className={`px-4 py-3 font-semibold ${c.indicators.RSI > 65 ? 'text-red-400' : 'text-green-400'}`}>{c.indicators.RSI.toFixed(2)}</td><td className="px-4 py-3 text-blue-300">{c.indicators.ADX.toFixed(2)}</td><td className="px-4 py-3 text-gray-500 text-xs">{new Date(c.last_updated).toLocaleString('tr-TR')}</td><td className="px-4 py-3 text-center"><div className="flex justify-center items-center gap-2"><button onClick={() => handleAnalyze(c)} disabled={isRowAnalyzing || isRowRefreshing} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3 py-1 text-xs rounded-md flex items-center gap-1.5 disabled:bg-gray-600 disabled:cursor-not-allowed">{isRowAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Bot size={14} />}Analiz</button><button onClick={() => handleRefresh(c.symbol)} disabled={isRowRefreshing || isRowAnalyzing} className="p-1.5 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white disabled:bg-gray-600 disabled:cursor-not-allowed">{isRowRefreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}</button></div></td></tr> )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
            <AnalysisResultModal 
                result={analysisResult} 
                isVisible={!!analysisResult} 
                onClose={() => setAnalysisResult(null)} 
                onConfirmTrade={handleConfirmTrade} 
                isOpeningTrade={isOpeningTrade}
            />
            <ScannerSettingsModal
                settings={scannerSettings}
                isVisible={isSettingsModalVisible}
                onClose={() => setIsSettingsModalVisible(false)}
                onSave={handleSaveSettings}
                onSettingsChange={handleSettingsChange}
            />
        </div>
    );
};