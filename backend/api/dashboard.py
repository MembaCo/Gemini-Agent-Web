
# ==============================================================================
# File: backend/api/dashboard.py
# @author: Memba Co.
# Açıklama: Yeni metrikleri ve grafik verilerini hesaplamak için tamamen yenilendi.
#           /events adında yeni bir endpoint eklendi.
# ==============================================================================
import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

import database
from core import agent as core_agent

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", summary="Tüm dashboard verilerini al")
async def get_dashboard_data():
    logging.info("API: Dashboard verileri için istek alındı.")
    try:
        trade_history = database.get_trade_history()
        if not isinstance(trade_history, list): trade_history = []
        
        # --- Gelişmiş İstatistikler ---
        gross_profit = sum(t['pnl'] for t in trade_history if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trade_history if t['pnl'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        total_pnl = gross_profit - gross_loss
        total_trades = len(trade_history)
        winning_trades = sum(1 for t in trade_history if t['pnl'] > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Ortalama pozisyon süresi
        total_holding_seconds = 0
        if total_trades > 0:
            for trade in trade_history:
                try:
                    opened_at = datetime.fromisoformat(trade['opened_at'])
                    closed_at = datetime.fromisoformat(trade['closed_at'])
                    total_holding_seconds += (closed_at - opened_at).total_seconds()
                except (TypeError, ValueError):
                    continue # Geçersiz tarih formatını atla
            avg_holding_seconds = total_holding_seconds / total_trades
        else:
            avg_holding_seconds = 0
        
        # PNL Grafiği ve Max Drawdown
        pnl_df = pd.DataFrame(trade_history)
        max_drawdown = 0
        cumulative_pnl_chart = []
        performance_by_symbol = []
        performance_by_week = []

        if not pnl_df.empty and 'closed_at' in pnl_df.columns and 'pnl' in pnl_df.columns:
            pnl_df['closed_at_dt'] = pd.to_datetime(pnl_df['closed_at'])
            pnl_df = pnl_df.sort_values(by='closed_at_dt')
            pnl_df['cumulative_pnl'] = pnl_df['pnl'].cumsum()
            
            pnl_df['peak'] = pnl_df['cumulative_pnl'].cummax()
            pnl_df['drawdown'] = pnl_df['peak'] - pnl_df['cumulative_pnl']
            max_drawdown = pnl_df['drawdown'].max() if not pnl_df['drawdown'].empty else 0
            
            cumulative_pnl_chart = [{'x': row['closed_at_dt'].strftime('%Y-%m-%d'), 'y': row['cumulative_pnl']} for index, row in pnl_df.iterrows()]

            # Sembollere Göre İşlem Dağılımı (Pie Chart)
            trade_dist = pnl_df.groupby('symbol').size().reset_index(name='count')
            performance_by_symbol = trade_dist.to_dict('records')
            
            # Haftalık Performans (Bar Chart)
            pnl_df['week'] = pnl_df['closed_at_dt'].dt.to_period('W').astype(str)
            weekly_perf = pnl_df.groupby('week')['pnl'].sum().reset_index()
            performance_by_week = weekly_perf.to_dict('records')

        active_model = "N/A"
        if core_agent.model_fallback_list:
            try:
                active_model = core_agent.model_fallback_list[core_agent.current_model_index]
            except IndexError:
                logging.error("Dashboard: Aktif model indeksi, model listesinin dışında.")

        stats = {
            "total_pnl": total_pnl, "win_rate": win_rate, "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades, "total_trades": total_trades,
            "active_model": active_model, "profit_factor": profit_factor,
            "max_drawdown": max_drawdown, "avg_pnl": avg_pnl,
            "avg_holding_seconds": avg_holding_seconds
        }

        return {
            "stats": stats,
            "chart_data": {"points": cumulative_pnl_chart},
            "trade_history": trade_history,
            "performance_by_symbol": performance_by_symbol,
            "performance_by_week": performance_by_week,
        }
    except Exception as e:
        logging.error(f"Dashboard verileri alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Dashboard verileri alınırken bir sunucu hatası oluştu.")

@router.get("/events", summary="Son sistem olaylarını (logları) al")
async def get_system_events(limit: int = 50):
    """Veritabanından en son sistem olaylarını çeker."""
    try:
        return database.get_events(limit)
    except Exception as e:
        logging.error(f"Sistem olayları alınırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Loglar alınırken bir hata oluştu.")
