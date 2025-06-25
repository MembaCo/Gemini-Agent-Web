import React, { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { ScanSearch, PlayCircle, Loader2, Bot, Check, AlertTriangle } from 'lucide-react';
import { AnalysisResultModal } from './DashboardPage'; // Dashboard'daki modalı yeniden kullanıyoruz

export const ScannerPage = () => {
    const { showToast, runScannerCandidates, runAnalysis } = useAuth();

    const [isLoading, setIsLoading] = useState(false);
    const [candidates, setCandidates] = useState([]);
    const [analyzingSymbol, setAnalyzingSymbol] = useState(null);
    const [analysisResult, setAnalysisResult] = useState(null);

    const handleScan = async () => {
        setIsLoading(true);
        setCandidates([]);
        showToast('Potansiyel fırsatlar için piyasa taranıyor...', 'info');
        try {
            const result = await runScannerCandidates();
            setCandidates(result);
            showToast(`${result.length} potansiyel fırsat bulundu.`, 'success');
        } catch (error) {
            showToast(`Tarama sırasında bir hata oluştu: ${error.message}`, 'error');
        } finally {
            setIsLoading(false);
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
                        <p className="text-sm text-gray-400 mt-1">Piyasayı potansiyel fırsatlar için tarayın ve sadece seçtiğiniz adayları AI ile analiz edin.</p>
                    </div>
                    <button onClick={handleScan} disabled={isLoading} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-5 rounded-md flex justify-center items-center gap-2 shrink-0">
                        {isLoading ? <Loader2 className="animate-spin" size={20} /> : <PlayCircle size={20} />}
                        {isLoading ? 'Taranıyor...' : 'Potansiyel Fırsatları Tara'}
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
                                <th scope="col" className="px-4 py-3 text-center">Eylem</th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading && (
                                <tr><td colSpan="5" className="text-center p-8"><Loader2 className="animate-spin text-white mx-auto" /></td></tr>
                            )}
                            {!isLoading && candidates.length === 0 && (
                                <tr><td colSpan="5" className="text-center p-8 text-gray-400">Henüz taranmış aday bulunmuyor. Taramayı başlatın.</td></tr>
                            )}
                            {candidates.map(c => (
                                <tr key={c.symbol} className="border-b border-gray-700 hover:bg-gray-900/30">
                                    <td className="px-4 py-3 font-medium text-white">{c.symbol}</td>
                                    <td className="px-4 py-3 text-gray-400">{c.source}</td>
                                    <td className={`px-4 py-3 font-semibold ${c.indicators.RSI > 65 ? 'text-red-400' : 'text-green-400'}`}>{c.indicators.RSI}</td>
                                    <td className="px-4 py-3 text-blue-300">{c.indicators.ADX}</td>
                                    <td className="px-4 py-3 text-center">
                                        <button onClick={() => handleAnalyze(c)} disabled={analyzingSymbol === c.symbol} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3 py-1 text-xs rounded-md flex items-center gap-1.5 disabled:bg-gray-600">
                                            {analyzingSymbol === c.symbol ? <Loader2 size={14} className="animate-spin" /> : <Bot size={14} />}
                                            Analiz Et
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

             <AnalysisResultModal 
                result={analysisResult} 
                isVisible={!!analysisResult} 
                onClose={() => setAnalysisResult(null)} 
                onConfirmTrade={() => { /* Bu sayfadan doğrudan işlem açılmayacak, modal sadece bilgi verir */ setAnalysisResult(null); showToast('İşlem açmak için Dashboard sayfasını kullanın.', 'info'); }} 
            />
        </div>
    );
};
