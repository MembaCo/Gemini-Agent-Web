import React from 'react';
import { Loader2, X } from 'lucide-react';

export const Modal = ({ children, isVisible, onClose, maxWidth = 'max-w-md' }) => {
  if (!isVisible) return null;
  return (
    <div className="fixed inset-0 bg-black/70 flex justify-center items-center z-40 p-4" onClick={onClose}>
      <div className={`bg-gray-800 border border-gray-700 rounded-xl p-6 sm:p-8 w-full ${maxWidth}`} onClick={e => e.stopPropagation()}>{children}</div>
    </div>
  );
};

export const Switch = ({ checked, onChange }) => (
    <button type="button" onClick={() => onChange(!checked)} className={`${checked ? 'bg-blue-600' : 'bg-gray-600'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}>
        <span className={`${checked ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`} />
    </button>
);

export const TooltipWrapper = ({ content, children }) => (
    <div className="relative flex items-center group">
        {children}
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 text-xs text-white bg-gray-900 border border-gray-700 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10 pointer-events-none">
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
                    <button 
                        onClick={() => onConfirmTrade(result)} 
                        disabled={isOpeningTrade}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded-md flex justify-center items-center gap-2 disabled:bg-gray-500 disabled:cursor-wait"
                    >
                        {isOpeningTrade ? <Loader2 className="animate-spin" size={20} /> : null}
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