import React, { createContext, useState, useCallback, useContext, useEffect } from 'react';
import { Power } from 'lucide-react';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('authToken'));
    const [toast, setToast] = useState(null);
    // YENİ: Ayarları global olarak tutmak için state eklendi.
    const [settings, setSettings] = useState({});

    const API_URL = "/api";

    const showToast = useCallback((message, type = 'info') => {
        setToast({ message, type });
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('authToken');
        setIsAuthenticated(false);
        setSettings({}); // Çıkış yapıldığında ayarları temizle
        showToast('Başarıyla çıkış yapıldı.', 'info');
    }, [showToast]);

    const apiFetch = useCallback(async (url, options = {}) => {
        const currentToken = localStorage.getItem('authToken');
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        if (currentToken) {
            headers['Authorization'] = `Bearer ${currentToken}`;
        }

        const response = await fetch(`${API_URL}${url}`, { ...options, headers });

        if (response.status === 401) {
            logout();
            throw new Error('Oturum süreniz doldu. Lütfen tekrar giriş yapın.');
        }
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || `HTTP Hatası: ${response.status}`);
            return data;
        } else {
            if (!response.ok) throw new Error(`HTTP Hatası: ${response.status}`);
            return; 
        }
    }, [logout]);

    const login = async (username, password) => {
        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);
            const response = await fetch(`${API_URL}/auth/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData });
            const data = await response.json();
            if (!response.ok || data.detail) {
                throw new Error(data.detail || "Giriş başarısız.");
            }
            localStorage.setItem('authToken', data.access_token);
            setIsAuthenticated(true);
            showToast('Başarıyla giriş yapıldı!', 'success');
            return true;
        } catch (error) {
            showToast(error.message, 'error');
            return false;
        }
    };
    
    // API Fonksiyonları
    const fetchSettings = useCallback(() => apiFetch('/settings/'), [apiFetch]);
    const saveSettings = useCallback((newSettings) => apiFetch('/settings/', { method: 'PUT', body: JSON.stringify(newSettings) }), [apiFetch]);
    
    // ... (diğer tüm API fetch fonksiyonları burada aynı kalır) ...
    const fetchAppVersion = useCallback(() => apiFetch('/app-version'), [apiFetch]);
    const fetchData = useCallback(() => apiFetch('/dashboard/stats'), [apiFetch]);
    const fetchPositions = useCallback(() => apiFetch('/positions/'), [apiFetch]);
    const runAnalysis = useCallback((params) => apiFetch('/analysis/new', { method: 'POST', body: JSON.stringify(params) }), [apiFetch]);
    const openPosition = useCallback((params) => apiFetch('/positions/open', { method: 'POST', body: JSON.stringify(params) }), [apiFetch]);
    const closePosition = useCallback((symbol) => apiFetch(`/positions/${encodeURIComponent(symbol)}/close`, { method: 'POST' }), [apiFetch]);
    const refreshPnl = useCallback((symbol) => apiFetch(`/positions/${encodeURIComponent(symbol)}/refresh-pnl`, { method: 'POST' }), [apiFetch]);
    const reanalyzePosition = useCallback((symbol) => apiFetch(`/positions/${encodeURIComponent(symbol)}/reanalyze`, { method: 'POST' }), [apiFetch]);
    const fetchEvents = useCallback(() => apiFetch('/dashboard/events'), [apiFetch]);
    const closeAllPositions = useCallback(() => apiFetch('/positions/close-all', { method: 'POST' }), [apiFetch]);
    const closeProfitablePositions = useCallback(() => apiFetch('/positions/close-profitable', { method: 'POST' }), [apiFetch]);
    const closeLosingPositions = useCallback(() => apiFetch('/positions/close-losing', { method: 'POST' }), [apiFetch]);
    const reanalyzeAllPositions = useCallback(() => apiFetch('/positions/reanalyze-all', { method: 'POST' }), [apiFetch]);
    const runBacktest = useCallback((params) => apiFetch('/backtest/run', { method: 'POST', body: JSON.stringify(params) }), [apiFetch]);
    const fetchChartData = useCallback((params) => {const query = new URLSearchParams(params).toString();return apiFetch(`/charts/ohlcv?${query}`);},[apiFetch]);
    const fetchPresets = useCallback(() => apiFetch('/presets/'), [apiFetch]);
    const savePreset = useCallback((preset) => apiFetch('/presets/', { method: 'POST', body: JSON.stringify(preset) }), [apiFetch]);
    const deletePreset = useCallback((presetId) => apiFetch(`/presets/${presetId}`, { method: 'DELETE' }), [apiFetch]);
    const runInteractiveScan = useCallback(() => apiFetch('/scanner/run-interactive-scan', { method: 'POST' }), [apiFetch]);
    const runProactiveScan = useCallback(() => apiFetch('/scanner/run-proactive-scan', { method: 'POST' }), [apiFetch]);
    const fetchScannerCandidates = useCallback(() => apiFetch('/scanner/candidates'), [apiFetch]);
    const refreshScannerCandidate = useCallback((symbol) => apiFetch(`/scanner/candidates/${encodeURIComponent(symbol)}/refresh`, { method: 'POST' }), [apiFetch]);

    // YENİ: Oturum açıldığında ayarları yükle
    useEffect(() => {
        if (isAuthenticated) {
            fetchSettings().then(setSettings).catch(err => showToast("Uygulama ayarları yüklenemedi: " + err.message, "error"));
        }
    }, [isAuthenticated, fetchSettings, showToast]);

    const value = {
        isAuthenticated, login, logout, toast, showToast, setToast,
        // YENİ: Ayarlar state'i ve güncelleyici fonksiyonu context'e ekleniyor.
        settings, 
        setSettings,
        // API fonksiyonları
        fetchAppVersion, fetchData, fetchPositions, fetchSettings, saveSettings, runAnalysis, openPosition,
        closePosition, refreshPnl, reanalyzePosition, fetchEvents,
        closeAllPositions, closeProfitablePositions, closeLosingPositions, reanalyzeAllPositions,
        runBacktest, fetchChartData, fetchPresets, savePreset, deletePreset,
        runInteractiveScan, runProactiveScan, fetchScannerCandidates, refreshScannerCandidate,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
            {isAuthenticated && (
                <button onClick={logout} className="fixed top-5 right-5 bg-red-600/80 hover:bg-red-600 text-white p-2 rounded-full shadow-lg z-30 group transition-transform hover:scale-110">
                    <Power size={20} />
                </button>
            )}
        </AuthContext.Provider>
    );
};