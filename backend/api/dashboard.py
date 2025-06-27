# api/dashboard.py
# @author: Memba Co.

from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime, timedelta

import database
from core import agent as core_agent # Agent modülünü import ediyoruz

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

@router.get("/stats", summary="Genel performans istatistiklerini ve grafik verilerini al")
async def get_dashboard_data():
    """
    Frontend dashboard'u için gerekli tüm verileri hesaplar ve döndürür.
    Bu, genel PNL, kazanma oranı gibi temel istatistikleri, aktif AI modelini
    ve PNL zaman çizelgesi grafiği için verileri içerir.
    """
    logging.info("API: Dashboard verileri için istek alındı.")
    
    try:
        trade_history = database.get_trade_history()
        if not isinstance(trade_history, list):
             trade_history = []

        # --- Genel İstatistikleri Hesapla ---
        total_pnl = sum(item['pnl'] for item in trade_history)
        total_trades = len(trade_history)
        winning_trades = sum(1 for item in trade_history if item['pnl'] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        best_trade = max(trade_history, key=lambda x: x['pnl'], default={'pnl': 0})
        worst_trade = min(trade_history, key=lambda x: x['pnl'], default={'pnl': 0})

        # YENİ: Aktif olarak çalışan AI modelinin adını al
        active_model = "N/A"
        if core_agent.model_fallback_list:
            try:
                active_model = core_agent.model_fallback_list[core_agent.current_model_index]
            except IndexError:
                logging.error("Dashboard: Aktif model indeksi, model listesinin dışında.")
        
        stats = {
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "best_trade_pnl": best_trade['pnl'],
            "worst_trade_pnl": worst_trade['pnl'],
            "active_model": active_model, # Aktif model istatistiklere eklendi
        }

        # --- PNL Grafiği Verilerini Oluştur ---
        cumulative_pnl = 0
        chart_points = []
        if trade_history:
             try:
                 first_trade_date_str = trade_history[0]['closed_at'].split('.')[0]
                 first_trade_date = datetime.strptime(first_trade_date_str, '%Y-%m-%d %H:%M:%S')
                 start_date = first_trade_date - timedelta(days=1)
                 chart_points.append({'x': start_date.strftime('%Y-%m-%d'), 'y': 0})
             except (ValueError, IndexError):
                chart_points.append({'x': datetime.now().strftime('%Y-%m-%d'), 'y': 0})
        for trade in reversed(trade_history): # Grafiğin doğru çizilmesi için eskiden yeniye sırala
            cumulative_pnl += trade['pnl']
            chart_points.append({
                'x': trade['closed_at'].split(' ')[0],
                'y': round(cumulative_pnl, 2)
            })
        
        chart_data = {"points": chart_points}

        response_data = {
            "stats": stats,
            "chart_data": chart_data,
            "trade_history": trade_history
        }

        return response_data

    except Exception as e:
        logging.error(f"Dashboard verileri alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Dashboard verileri alınırken bir sunucu hatası oluştu.")
