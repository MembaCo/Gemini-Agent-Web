import React from 'react';
import { Loader2, X, Brain, ShieldX } from 'lucide-react';

export const Modal = ({ children, isVisible, onClose, maxWidth = 'max-w-md' }) => {
    if (!isVisible) return null;
    return (
      <div className="fixed inset-0 bg-black/70 flex justify-center items-center z-50 p-4" onClick={onClose}>
        <div className={`bg-gray-800 border border-gray-700 rounded-xl p-6 sm:p-8 w-full ${maxWidth} flex flex-col`} onClick={e => e.stopPropagation()}>{children}</div>
      </div>
    );
  };

export const Switch = ({ checked, onChange }) => (
    <button type="button" onClick={() => onChange(!checked)} className={`${checked ? 'bg-blue-600' : 'bg-gray-600'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0`}>
        <span className={`${checked ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
    </button>
);

export const TooltipWrapper = ({ content, children }) => (
    <div className="relative flex items-center group">
        {children}
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs p-2 text-xs text-white bg-gray-900 border border-gray-700 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10 pointer-events-none">
            {content}
        </div>
    </div>
);

export const AnalysisResultModal = ({ result, isVisible, onClose, onConfirmTrade, isOpeningTrade }) => {
    const isTradeable = result?.recommendation === 'AL' || result?.recommendation === 'SAT';
    return (
        <Modal isVisible={isVisible} onClose={onClose}>
            <h2 className="text-2xl font-bold text-white mb-4">Analiz Sonucu</h2>
            <div className="space-y-3 text-gray-300">
                <p><span className="font-semibold text-gray-400">Sembol:</span> {result?.symbol}</p>
                <p><span className="font-semibold text-gray-400">Tavsiye:</span> <span className={`font-bold ${isTradeable ? (result?.recommendation === 'AL' ? 'text-green-400' : 'text-red-400') : 'text-yellow-400'}`}>{result?.recommendation}</span></p>
                <p><span className="font-semibold text-gray-400">Gerekçe:</span> {result?.reason}</p>
            </div>
            <div className="mt-6 flex gap-4">
                <button onClick={onClose} className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 rounded-md">Kapat</button>
                {isTradeable && (
                    <button onClick={() => onConfirmTrade(result)} disabled={isOpeningTrade} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-md flex justify-center items-center gap-2 disabled:bg-gray-500 disabled:cursor-wait">
                        {isOpeningTrade && <Loader2 className="animate-spin" size={20} />}
                        {isOpeningTrade ? 'İşlem Açılıyor...' : 'Pozisyon Aç'}
                    </button>
                )}
            </div>
        </Modal>
    );
};

export const ReanalysisResultModal = ({ result, isVisible, onClose, onConfirmClose }) => (
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

export const ConfirmationModal = ({ isVisible, onClose, onConfirm, title, children }) => (
    <Modal isVisible={isVisible} onClose={onClose}>
        <h2 className="text-2xl font-bold text-white mb-4">{title}</h2>
        <div className="text-gray-300 mb-6">{children}</div>
        <div className="flex gap-4">
            <button onClick={onClose} className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 rounded-md">İptal</button>
            <button onClick={onConfirm} className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 rounded-md">Onayla</button>
        </div>
    </Modal>
);

export const ProactiveScanResultsModal = ({ opportunities, isVisible, onClose, onConfirmTrade, openingTradeSymbol }) => {
    if (!isVisible || opportunities.length === 0) return null;
    return (
        <Modal isVisible={isVisible} onClose={onClose} maxWidth="max-w-2xl">
            <div className="flex justify-between items-center mb-1"><h2 className="text-2xl font-bold text-white">Proaktif Tarama Sonuçları</h2><button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white"><X size={24} /></button></div>
            <p className="text-sm text-gray-400 mb-6">{opportunities.length} adet onay bekleyen fırsat bulundu.</p>
            <div className="space-y-4 max-h-[50vh] overflow-y-auto pr-4 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
                {opportunities.map((opp, index) => {
                    const isOpeningThisTrade = openingTradeSymbol === opp.symbol;
                    return (
                        <div key={index} className="bg-gray-900/50 p-4 rounded-lg flex justify-between items-center gap-4">
                            <div className="flex-grow"><p className="font-bold text-white">{opp.symbol} <span className="text-xs text-gray-400">({opp.timeframe})</span></p><p className={`font-semibold ${opp.recommendation === 'AL' ? 'text-green-400' : 'text-red-400'}`}>{opp.recommendation === 'AL' ? 'ALIM FIRSATI' : 'SATIM FIRSATI'}</p><p className="text-xs text-gray-500 mt-1">{opp.reason}</p></div>
                            <button onClick={() => onConfirmTrade(opp)} disabled={isOpeningThisTrade} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md flex-shrink-0 disabled:bg-gray-500 disabled:cursor-wait w-32">{isOpeningThisTrade ? <Loader2 className="animate-spin mx-auto" /> : 'Onayla'}</button>
                        </div>
                    );
                 })}
            </div>
            <div className="mt-6 flex justify-end"><button onClick={onClose} className="bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-md">Tümünü Kapat</button></div>
        </Modal>
    );
};



export const BulkReanalysisResultModal = ({ results, isVisible, onClose, onConfirmClose }) => {
    if (!isVisible || !results) return null;
    return (
        <Modal isVisible={isVisible} onClose={onClose} maxWidth="max-w-2xl">
            <div className="flex-shrink-0 flex justify-between items-center mb-1"><h2 className="text-2xl font-bold text-white flex items-center gap-2"><Brain size={24}/> Toplu Analiz Sonuçları</h2><button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white"><X size={24} /></button></div>
            <p className="flex-shrink-0 text-sm text-gray-400 mb-6">{results.length} adet açık pozisyon için AI analizi tamamlandı.</p>
            <div className="flex-grow space-y-3 overflow-y-auto pr-4 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
                {results.map((res, index) => {
                    const isError = res.recommendation === 'HATA';
                    const isClose = res.recommendation === 'KAPAT';
                    return (
                        <div key={index} className={`bg-gray-900/50 p-4 rounded-lg flex justify-between items-center gap-4 ${isError ? 'border-l-4 border-red-500' : ''}`}>
                            <div className="flex-grow">
                                <p className="font-bold text-white">{res.symbol}</p>
                                <p className={`font-semibold ${isClose ? 'text-red-400' : isError ? 'text-yellow-400' : 'text-green-400'}`}>Tavsiye: {res.recommendation}</p>
                                <p className="text-xs text-gray-500 mt-1">{res.reason}</p>
                            </div>
                            {isClose && (<button onClick={() => { onClose(); onConfirmClose(res.symbol); }} className="bg-red-600 hover:bg-red-700 text-white font-semibold py-1 px-3 text-xs rounded-md flex-shrink-0 flex items-center gap-1.5"><ShieldX size={14}/> Kapat</button>)}
                        </div>
                    );
                 })}
            </div>
            <div className="flex-shrink-0 mt-6 flex justify-end"><button onClick={onClose} className="bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-md">Pencereyi Kapat</button></div>
        </Modal>
    );
};