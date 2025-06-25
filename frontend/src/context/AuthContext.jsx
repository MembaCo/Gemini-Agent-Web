import React, { createContext, useState, useCallback, useContext } from 'react';
import { Power } from 'lucide-react';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('authToken'));
    const [token, setToken] = useState(localStorage.getItem('authToken'));
    const [toast, setToast] = useState(null);

    const API_URL = "/api";

    const showToast = useCallback((message, type = 'info') => {
        setToast({ message, type });
    }, []);

    const apiFetch = useCallback(async (url, options = {}) => {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_URL}${url}`, { ...options, headers });

        if (response.status === 401) {
            logout();
            showToast('Oturum süreniz doldu. Lütfen tekrar giriş yapın.', 'error');
            throw new Error('Unauthorized');
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || `HTTP error! status: ${response.status}`);
        }
        return data;
    }, [token, showToast]);


    const login = async (username, password) => {
        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch(`${API_URL}/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Giriş başarısız.");
            }

            const new_token = data.access_token;
            localStorage.setItem('authToken', new_token);
            setToken(new_token);
            setIsAuthenticated(true);
            showToast('Başarıyla giriş yapıldı!', 'success');
            return true;
        } catch (error) {
            showToast(error.message, 'error');
            return false;
        }
    };

    const logout = () => {
        localStorage.removeItem('authToken');
        setToken(null);
        setIsAuthenticated(false);
        showToast('Başarıyla çıkış yapıldı.', 'info');
    };
    
    // API fonksiyonları
    const fetchData = useCallback(() => apiFetch('/dashboard/stats'), [apiFetch]);
    const fetchPositions = useCallback(() => apiFetch('/positions/'), [apiFetch]);
    const fetchSettings = useCallback(() => apiFetch('/settings/'), [apiFetch]);
    const saveSettings = useCallback((newSettings) => apiFetch('/settings/', { method: 'PUT', body: JSON.stringify(newSettings) }), [apiFetch]);
    const runAnalysis = useCallback((params) => apiFetch('/analysis/new', { method: 'POST', body: JSON.stringify(params) }), [apiFetch]);
    const openPosition = useCallback((params) => apiFetch('/positions/open', { method: 'POST', body: JSON.stringify(params) }), [apiFetch]);
    const closePosition = useCallback((symbol) => apiFetch(`/positions/${encodeURIComponent(symbol)}/close`, { method: 'POST' }), [apiFetch]);
    const refreshPnl = useCallback((symbol) => apiFetch(`/positions/${encodeURIComponent(symbol)}/refresh-pnl`, { method: 'POST' }), [apiFetch]);
    const reanalyzePosition = useCallback((symbol) => apiFetch(`/positions/${encodeURIComponent(symbol)}/reanalyze`, { method: 'POST' }), [apiFetch]);
    const runBacktest = useCallback((params) => apiFetch('/backtest/run', { method: 'POST', body: JSON.stringify(params) }), [apiFetch]);
    const fetchChartData = useCallback((params) => {const query = new URLSearchParams(params).toString();return apiFetch(`/charts/ohlcv?${query}`);},[apiFetch]);
    const fetchPresets = useCallback(() => apiFetch('/presets/'), [apiFetch]);
    const savePreset = useCallback((preset) => apiFetch('/presets/', { method: 'POST', body: JSON.stringify(preset) }), [apiFetch]);
    const deletePreset = useCallback((presetId) => apiFetch(`/presets/${presetId}`, { method: 'DELETE' }), [apiFetch]);
    
    // YENİ VE GÜNCELLENMİŞ SCANNER FONKSİYONLARI
    const runScannerCandidates = useCallback(() => apiFetch('/scanner/candidates', { method: 'POST' }), [apiFetch]);
    const fetchScannerCandidates = useCallback(() => apiFetch('/scanner/candidates'), [apiFetch]);
    const refreshScannerCandidate = useCallback((symbol) => apiFetch(`/scanner/candidates/${encodeURIComponent(symbol)}/refresh`, { method: 'POST' }), [apiFetch]);


    const value = {
        isAuthenticated,
        token,
        login,
        logout,
        apiFetch,
        toast,
        showToast,
        setToast,
        fetchData,
        fetchPositions,
        fetchSettings,
        saveSettings,
        runAnalysis,
        openPosition,
        closePosition,
        refreshPnl,
        reanalyzePosition,
        runBacktest,
        fetchChartData,
        fetchPresets,
        savePreset,
        deletePreset,
        runScannerCandidates,
        fetchScannerCandidates,
        refreshScannerCandidate
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
            {isAuthenticated && (
                 <button onClick={logout} className="fixed top-5 right-5 bg-red-600/80 hover:bg-red-600 text-white p-2 rounded-full shadow-lg z-50 group transition-transform hover:scale-110">
                    <Power size={20} />
                    <span className="absolute right-full mr-2 top-1/2 -translate-y-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                        Çıkış Yap
                    </span>
                </button>
            )}
        </AuthContext.Provider>
    );
};
