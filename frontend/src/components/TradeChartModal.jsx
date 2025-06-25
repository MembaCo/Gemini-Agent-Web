import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { useAuth } from '../context/AuthContext';
import { X, Loader2 } from 'lucide-react';

// Modal bileşeni, daha büyük projelerde kendi dosyasına taşınabilir.
const Modal = ({ children, isVisible, onClose, maxWidth = 'max-w-4xl' }) => {
    if (!isVisible) return null;
    return (
      <div className="fixed inset-0 bg-black/70 flex justify-center items-center z-50 p-4" onClick={onClose}>
        <div className={`bg-gray-800 border border-gray-700 rounded-xl w-full h-full md:h-auto md:max-h-[80vh] ${maxWidth}`} onClick={e => e.stopPropagation()}>
            {children}
        </div>
      </div>
    );
};

export const TradeChartModal = ({ isVisible, onClose, trade }) => {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const { fetchChartData, showToast } = useAuth();
    const [chartData, setChartData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Modal görünür değilse veya işlem verisi yoksa hiçbir şey yapma
        if (!isVisible || !trade) return;

        const getChartData = async () => {
            setIsLoading(true);
            try {
                // 'timeframe' bilgisi veritabanından gelecek.
                // Eğer yoksa (eski kayıtlar için), '1h' varsayılan olarak kullanılacak.
                const timeframeToFetch = trade.timeframe || '1h';
                
                const data = await fetchChartData({ 
                    symbol: trade.symbol,
                    timeframe: timeframeToFetch, 
                    limit: 500 
                });
                
                if (data.length === 0) {
                    showToast(`${trade.symbol} için ${timeframeToFetch} zaman aralığında grafik verisi bulunamadı. Bu, eski bir işlem kaydı olabilir.`, 'warning');
                }
                setChartData(data);

            } catch (error) {
                showToast(`Grafik verileri alınamadı: ${error.message}`, 'error');
                setChartData([]); // Hata durumunda veriyi temizle
            } finally {
                setIsLoading(false);
            }
        };

        getChartData();

    }, [isVisible, trade, fetchChartData, showToast]);

    useEffect(() => {
        // Grafiği oluşturmadan önce, verinin yüklendiğinden ve boş olmadığından emin ol
        if (isLoading || !chartData.length || !chartContainerRef.current) {
            // Eğer bir önceki grafik varsa temizle
            if(chartRef.current) {
                chartRef.current.remove();
                chartRef.current = null;
            }
            return;
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { color: '#1f2937' },
                textColor: '#d1d5db',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            }
        });

        chartRef.current = chart;

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });
        candlestickSeries.setData(chartData);

        const markers = [];
        const entryTimestamp = Math.floor(new Date(trade.opened_at || trade.created_at).getTime() / 1000);
        if (trade.entry_price) {
            markers.push({
                time: entryTimestamp,
                position: 'aboveBar',
                color: trade.side === 'buy' ? '#3b82f6' : '#f97316',
                shape: trade.side === 'buy' ? 'arrowUp' : 'arrowDown',
                text: `Giriş @ ${trade.entry_price.toFixed(4)}`,
            });
        }
        if (trade.close_price && trade.closed_at) {
             const closeTimestamp = Math.floor(new Date(trade.closed_at).getTime() / 1000);
             markers.push({
                time: closeTimestamp,
                position: 'aboveBar',
                color: '#a855f7',
                shape: 'circle',
                text: `Kapanış @ ${trade.close_price.toFixed(4)}`,
            });
        }
        candlestickSeries.setMarkers(markers);

        if (trade.stop_loss) {
            candlestickSeries.createPriceLine({
                price: trade.stop_loss,
                color: '#ef4444',
                lineWidth: 1,
                lineStyle: 2, // Kesikli çizgi
                axisLabelVisible: true,
                title: 'SL',
            });
        }
        if (trade.take_profit) {
            candlestickSeries.createPriceLine({
                price: trade.take_profit,
                color: '#22c55e',
                lineWidth: 1,
                lineStyle: 2, // Kesikli çizgi
                axisLabelVisible: true,
                title: 'TP',
            });
        }

        chart.timeScale().fitContent();

        const resizeObserver = new ResizeObserver(entries => {
            const { width, height } = entries[0].contentRect;
            chart.applyOptions({ width, height });
        });
        resizeObserver.observe(chartContainerRef.current);


        return () => {
            resizeObserver.disconnect();
            chart.remove();
            chartRef.current = null;
        };
    }, [isLoading, chartData, trade]);

    return (
        <Modal isVisible={isVisible} onClose={onClose}>
            <div className="flex flex-col h-full">
                <div className="flex justify-between items-center p-4 border-b border-gray-700">
                    <h2 className="text-xl font-bold text-white">İşlem Detayı: {trade?.symbol} ({trade?.timeframe || '...'})</h2>
                    <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white">
                        <X size={24} />
                    </button>
                </div>
                {/* DEĞİŞTİRİLDİ: JSX yapısı daha kararlı hale getirildi */}
                <div className="flex-grow relative">
                    {isLoading ? (
                        <div className="absolute inset-0 flex justify-center items-center bg-gray-800/50 z-10">
                            <Loader2 className="animate-spin text-white" size={48} />
                        </div>
                    ) : chartData.length > 0 ? (
                        <div ref={chartContainerRef} className="w-full h-full" />
                    ) : (
                        <div className="absolute inset-0 flex justify-center items-center z-10">
                            <p className="text-gray-400 p-4 text-center">Bu işlem için grafik verisi bulunamadı.</p>
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    );
};
