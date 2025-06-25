import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ScanSearch, PlayCircle, Loader2, Bot, RefreshCw } from 'lucide-react';
import { AnalysisResultModal } from './DashboardPage';

export const ScannerPage = () => {
    const { showToast, runScannerCandidates, fetchScannerCandidates, refreshScannerCandidate, runAnalysis } = useAuth();

    const [isScanning, setIsScanning] = useState(false);
    const [isFetchingInitial, setIsFetchingInitial] = useState(true);
    const [loadingStage, setLoadingStage] = useState('');
    const [candidates, setCandidates] = useState([]);
    
    const [analyzingSymbol, setAnalyzingSymbol] = useState(null);
    const [refreshingSymbol, setRefreshingSymbol] = useState(null);
    const [analysisResult, setAnalysisResult] = useState(null);

    // Sayfa ilk yüklendiğinde kayıtlı adayları çek
    const loadInitialCandidates = useCallback(async () => {
        setIsFetchingInitial(true);
        try {
            const initialCandidates = await fetchScannerCandidates();
            setCandidates(initialCandidates);
            if (initialCandidates.length > 0) {
                 showToast(`${initialCandidates.length} kayıtlı aday yüklendi.`, 'info');
            }
        } catch (error) {
            showToast(`Kayıtlı adaylar yüklenemedi: ${error.message}`, 'error');
        } finally {
            setIsFetchingInitial(false);
        }
    }, [fetchScannerCandidates, showToast]);

    useEffect(() => {
        loadInitialCandidates();
    }, [loadInitialCandidates]);


    const handleScan = async () => {
        setIsScanning(true);
        setCandidates([]); // Yeni tarama başladığında listeyi hemen temizle
        showToast('Yeni tarama başlatıldı...', 'info');
        setLoadingStage('Piyasa verileri çekiliyor ve filtreleniyor...');
        
        try {
            const result = await runScannerCandidates();
            setCandidates(result);
            showToast(`${result.length} potansiyel fırsat bulundu ve kaydedildi.`, 'success');
        } catch (error) {
            showToast(`Tarama sırasında bir hata oluştu: ${error.message}`, 'error');
        } finally {
            setIsScanning(false);
            setLoadingStage('');
        }
    };
    
    // Tek bir adayı yenileme fonksiyonu
    const handleRefresh = async (symbol) => {
        setRefreshingSymbol(symbol);
        try {
            const refreshedData = await refreshScannerCandidate(symbol);
            setCandidates(currentCandidates =>
                currentCandidates.map(c => (c.symbol === symbol ? refreshedData : c))
            );
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

    return (
        <div className="space-y-8">
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                            <ScanSearch size={24} /> İnteraktif Fırsat Tarayıcı
                        </h2>
                        <p className="text-sm text-gray-400 mt-1">Piyasayı potansiyel fırsatlar için tarayın, listeyi yenileyin ve seçtiğiniz adayları AI ile analiz edin.</p>
                    </div>
                    <button onClick={handleScan} disabled={isScanning} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-5 rounded-md flex justify-center items-center gap-2 shrink-0 disabled:bg-gray-600 disabled:cursor-not-allowed min-w-[240px]">
                        {isScanning ? <Loader2 className="animate-spin" size={20} /> : <PlayCircle size={20} />}
                        {isScanning ? loadingStage : 'Yeni Tarama Başlat'}
                    </button>
                </div>
            </div>

            <div className="bg-gray-800 p-4 sm:p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Analize Hazır Adaylar ({candidates.length})</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs text-gray-400 uppercase bg-gray-700/50">
                            <tr>
                                <th scope="col" className="px-4 py-3">Sembol</th>
                                <th scope="col" className="px-4 py-3">Kaynak</th>
                                <th scope="col" className="px-4 py-3">RSI</th>
                                <th scope="col" className="px-4 py-3">ADX</th>
                                <th scope="col" className="px-4 py-3">Son Güncelleme</th>
                                <th scope="col" className="px-4 py-3 text-center">Eylemler</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(isFetchingInitial || (isScanning && candidates.length === 0)) && (
                                <tr><td colSpan="6" className="text-center p-8 text-gray-400">
                                    <Loader2 className="animate-spin text-white mx-auto mb-2" />
                                    {isScanning ? loadingStage : 'Kayıtlı adaylar yükleniyor...'}
                                </td></tr>
                            )}
                            {!isFetchingInitial && !isScanning && candidates.length === 0 && (
                                <tr><td colSpan="6" className="text-center p-8 text-gray-400">Kayıtlı aday bulunamadı. Yeni bir tarama başlatın.</td></tr>
                            )}
                            {candidates.map(c => {
                                const isRowRefreshing = refreshingSymbol === c.symbol;
                                const isRowAnalyzing = analyzingSymbol === c.symbol;
                                return (
                                <tr key={c.symbol} className="border-b border-gray-700 hover:bg-gray-900/30">
                                    <td className="px-4 py-3 font-medium text-white">{c.symbol}</td>
                                    <td className="px-4 py-3 text-gray-400">{c.source}</td>
                                    <td className={`px-4 py-3 font-semibold ${c.indicators.RSI > 65 ? 'text-red-400' : 'text-green-400'}`}>{c.indicators.RSI.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-blue-300">{c.indicators.ADX.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-gray-500 text-xs">{new Date(c.last_updated).toLocaleString('tr-TR')}</td>
                                    <td className="px-4 py-3 text-center">
                                        <div className="flex justify-center items-center gap-2">
                                            <button onClick={() => handleAnalyze(c)} disabled={isRowAnalyzing || isRowRefreshing} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3 py-1 text-xs rounded-md flex items-center gap-1.5 disabled:bg-gray-600 disabled:cursor-not-allowed">
                                                {isRowAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Bot size={14} />}
                                                Analiz
                                            </button>
                                            <button onClick={() => handleRefresh(c.symbol)} disabled={isRowRefreshing || isRowAnalyzing} className="p-1.5 rounded-md hover:bg-gray-700 text-gray-400 hover:text-white disabled:bg-gray-600 disabled:cursor-not-allowed">
                                                {isRowRefreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            )})}
                        </tbody>
                    </table>
                </div>
            </div>

             <AnalysisResultModal 
                result={analysisResult} 
                isVisible={!!analysisResult} 
                onClose={() => setAnalysisResult(null)} 
                onConfirmTrade={() => { 
                    setAnalysisResult(null); 
                    showToast('İşlem açmak için Dashboard sayfasını kullanın.', 'info'); 
                }} 
            />
        </div>
    );
};
