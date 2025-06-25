import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { LoginPage } from './components/LoginPage';
import { DashboardPage } from './components/DashboardPage';
import { BacktestingPage } from './components/BacktestingPage';
import { ScannerPage } from './components/ScannerPage'; // YENİ
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

const Toast = ({ message, type, onClose }) => {
  if (!message) return null;
  const icons = { success: <CheckCircle className="text-green-400" />, error: <XCircle className="text-red-400" />, warning: <AlertTriangle className="text-yellow-400" />, info: <Info className="text-blue-400" /> };
  const borderColors = { success: 'border-green-500', error: 'border-red-500', warning: 'border-yellow-500', info: 'border-blue-500' };
  useEffect(() => { const timer = setTimeout(onClose, 5000); return () => clearTimeout(timer); }, [onClose]);
  return (
    <div className={`fixed bottom-5 right-5 bg-gray-800 border-l-4 ${borderColors[type]} text-white p-4 rounded-lg shadow-2xl flex items-center gap-4 z-50 animate-fade-in-up`}>
      {icons[type]}<p>{message}</p><button onClick={onClose} className="ml-auto text-gray-500 hover:text-white"><X size={18} /></button>
    </div>
  );
};

export default function App() {
    const { isAuthenticated, toast, setToast } = useAuth();
    const [view, setView] = useState('dashboard');

    if (!isAuthenticated) {
        return (
            <>
                <LoginPage />
                <Toast message={toast?.message} type={toast?.type} onClose={() => setToast(null)} />
            </>
        );
    }

    return (
        <div className="bg-gray-900 min-h-screen text-gray-300 font-sans">
            <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
                {/* Navigasyon Çubuğu */}
                <div className="mb-6 flex items-center border-b border-gray-700">
                    <button onClick={() => setView('dashboard')} className={`px-4 py-2 text-sm font-medium ${view === 'dashboard' ? 'border-b-2 border-blue-500 text-white' : 'text-gray-400 hover:text-white'}`}>
                        Dashboard
                    </button>
                     <button onClick={() => setView('scanner')} className={`px-4 py-2 text-sm font-medium ${view === 'scanner' ? 'border-b-2 border-blue-500 text-white' : 'text-gray-400 hover:text-white'}`}>
                        Fırsat Tarayıcı
                    </button>
                    <button onClick={() => setView('backtesting')} className={`px-4 py-2 text-sm font-medium ${view === 'backtesting' ? 'border-b-2 border-blue-500 text-white' : 'text-gray-400 hover:text-white'}`}>
                        Backtesting
                    </button>
                </div>

                {/* Görünüm Değiştirici */}
                {view === 'dashboard' && <DashboardPage />}
                {view === 'scanner' && <ScannerPage />}
                {view === 'backtesting' && <BacktestingPage />}
            </div>
            <Toast message={toast?.message} type={toast?.type} onClose={() => setToast(null)} />
        </div>
    );
}
