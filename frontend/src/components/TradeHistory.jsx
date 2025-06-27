// frontend/src/components/TradeHistory.jsx

import React from 'react';

const TradeHistory = ({ history, isLoading, onRowClick }) => (
    <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-400 uppercase bg-gray-700/50">
                <tr>
                    <th scope="col" className="px-4 py-3">Sembol</th>
                    <th scope="col" className="px-4 py-3">Yön</th>
                    <th scope="col" className="px-4 py-3">Giriş</th>
                    <th scope="col" className="px-4 py-3">Çıkış</th>
                    <th scope="col" className="px-4 py-3">P&L (USDT)</th>
                    <th scope="col" className="px-4 py-3">Durum</th>
                    <th scope="col" className="px-4 py-3">Kapanış Zamanı</th>
                </tr>
            </thead>
            <tbody>
                {isLoading ? (
                    <tr><td colSpan="7" className="text-center p-8 text-gray-400">Yükleniyor...</td></tr>
                ) : history && history.length > 0 ? (
                    history.map(trade => (
                        <tr 
                            key={trade.id} 
                            className={`border-b border-gray-700 ${onRowClick ? 'hover:bg-gray-900/30 cursor-pointer' : ''}`}
                            onClick={() => onRowClick ? onRowClick(trade) : null}
                        >
                            <td className="px-4 py-3 font-medium text-white">{trade.symbol}</td>
                            <td className="px-4 py-3">{trade.side.toUpperCase()}</td>
                            <td className="px-4 py-3">{trade.entry_price.toFixed(4)}</td>
                            <td className="px-4 py-3">{trade.close_price.toFixed(4)}</td>
                            <td className={`px-4 py-3 font-semibold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {trade.pnl.toFixed(2)}
                            </td>
                            <td className="px-4 py-3">{trade.status}</td>
                            <td className="px-4 py-3 text-gray-400">{new Date(trade.closed_at).toLocaleString('tr-TR')}</td>
                        </tr>
                    ))
                ) : (
                    <tr><td colSpan="7" className="text-center p-8 text-gray-400">Görüntülenecek işlem bulunamadı.</td></tr>
                )}
            </tbody>
        </table>
    </div>
);

export default TradeHistory;