# ==============================================================================
# File: backend/telegram_bot.py
# @author: Memba Co.
# ==============================================================================
import logging
import os
from dotenv import load_dotenv
from telegram import Update
# DÜZELTME: ParseMode, en son sürümlerle uyumlu olması için 'telegram.constants' modülünden import edildi.
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from core import app_config, trader, agent as core_agent
from tools import _get_unified_symbol, _fetch_price_natively, get_technical_indicators # Düzeltildi: get_technical_indicators doğrudan import edildi
import database
from ccxt.base.errors import BadSymbol

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def format_positions_message(positions: list) -> str:
    """Açık pozisyonları formatlı bir metne dönüştürür."""
    if not positions:
        return "Yönetilen açık pozisyon bulunmuyor."
    
    message = "*Açık Pozisyonlar:*\n"
    for pos in positions:
        symbol = pos['symbol'].replace('/', r'\/')
        side_emoji = "📈" if pos.get('side') == 'buy' else "📉"
        
        current_price = _fetch_price_natively(pos['symbol'])
        pnl_text = ""
        if current_price:
            pnl = (current_price - pos['entry_price']) * pos['amount'] if pos['side'] == 'buy' else (pos['entry_price'] - current_price) * pos['amount']
            pnl_emoji = "✅" if pnl >= 0 else "🔻"
            pnl_text = f" | *PNL:* `{pnl:+.2f}$` {pnl_emoji}"
            
        message += f"\n{side_emoji} `{symbol}`\n"
        message += f"  *Giriş:* `{pos['entry_price']:.4f}`{pnl_text}\n"
    
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start komutuna yanıt verir."""
    await update.message.reply_text(
        'Merhaba! *Gemini Trading Agent* hizmetinizde.\n\n'
        'Kullanılabilir komutlar:\n'
        '• `/analiz <SEMBOL>` - Belirtilen sembol için AI analizi yapar.\n'
        '• `/pozisyonlar` - Mevcut açık pozisyonları listeler.\n'
        '• `/kapat <SEMBOL>` - Belirtilen semboldeki pozisyonu kapatır.',
        parse_mode=ParseMode.MARKDOWN
    )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/analiz <SEMBOL> komutunu işler ve tam analiz yapar."""
    try:
        if not context.args:
            await update.message.reply_text('Lütfen bir sembol girin. Örnek: `/analiz btc`')
            return

        symbol = context.args[0].upper()
        unified_symbol = _get_unified_symbol(symbol)
        await update.message.reply_text(f'`{unified_symbol}` için analiz başlatılıyor, lütfen bekleyin...')
        
        current_price = _fetch_price_natively(unified_symbol)
        if current_price is None:
            raise BadSymbol(f"Fiyat bilgisi alınamadı: {unified_symbol}")

        use_mta = app_config.settings.get('USE_MTA_ANALYSIS', True)
        entry_timeframe = '15m'
        
        # Düzeltildi: get_technical_indicators.invoke() yerine get_technical_indicators() çağrıldı
        entry_indicators_result = get_technical_indicators(symbol_and_timeframe=f"{unified_symbol},{entry_timeframe}")
        if entry_indicators_result.get("status") != "success":
            raise ValueError(f"Teknik veri alınamadı: {entry_indicators_result.get('message')}")
        entry_indicators_data = entry_indicators_result["data"]
        
        final_prompt = ""
        if use_mta:
            trend_timeframe = app_config.settings.get('MTA_TREND_TIMEFRAME', '4h')
            # Düzeltildi: get_technical_indicators.invoke() yerine get_technical_indicators() çağrıldı
            trend_indicators_result = get_technical_indicators(symbol_and_timeframe=f"{unified_symbol},{trend_timeframe}")
            if trend_indicators_result.get("status") != "success":
                 raise ValueError(f"Trend verisi alınamadı: {trend_indicators_result.get('message')}")
            trend_indicators_data = trend_indicators_result["data"]
            final_prompt = core_agent.create_mta_analysis_prompt(unified_symbol, current_price, entry_timeframe, entry_indicators_data, trend_timeframe, trend_indicators_data)
        else:
            final_prompt = core_agent.create_final_analysis_prompt(unified_symbol, entry_timeframe, current_price, entry_indicators_data)
        
        result = core_agent.llm.invoke(final_prompt)
        parsed_data = core_agent.parse_agent_response(result.content)
        
        if not parsed_data:
            await update.message.reply_text(f'`{unified_symbol}` için yapay zekadan geçerli bir analiz yanıtı alınamadı.')
            return
            
        rec = parsed_data.get('recommendation', 'N/A')
        reason = parsed_data.get('reason', 'N/A')
        
        response_message = (
            f"*Analiz Sonucu: `{unified_symbol}`*\n\n"
            f"🔮 *Tavsiye:* `{rec}`\n\n"
            f"📝 *Gerekçe:* {reason}"
        )
        await update.message.reply_text(response_message, parse_mode=ParseMode.MARKDOWN)

    except (IndexError, ValueError) as e:
        await update.message.reply_text(f'Bir hata oluştu: {str(e)}')
    except BadSymbol as e:
        await update.message.reply_text(f'Geçersiz sembol veya veri bulunamadı: `{str(e)}`')
    except Exception as e:
        await update.message.reply_text(f'Analiz sırasında beklenmedik bir hata oluştu: {e}')

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/pozisyonlar komutunu işler."""
    try:
        positions = database.get_all_positions()
        message = format_positions_message(positions)
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f'Pozisyonlar alınırken bir hata oluştu: {e}')
        
async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/kapat <SEMBOL> komutunu işler."""
    try:
        if not context.args:
            await update.message.reply_text('Lütfen kapatmak için bir sembol girin. Örnek: `/kapat btc`')
            return
            
        symbol = context.args[0].upper()
        unified_symbol = _get_unified_symbol(symbol)
        
        await update.message.reply_text(f'`{unified_symbol}` pozisyonu kapatılıyor...')
        
        result = trader.close_existing_trade(unified_symbol, close_reason="MANUAL_TELEGRAM")
        
        await update.message.reply_text(f"✅ Sonuç: {result.get('message')}")
        
    except trader.TradeException as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")
    except Exception as e:
         await update.message.reply_text(f'Pozisyon kapatılırken beklenmedik bir hata oluştu: {e}')

def create_telegram_app():
    """Telegram bot uygulamasını oluşturur ve yapılandırır."""
    if not TOKEN:
        logging.warning("Telegram Bot Token bulunamadı. Telegram botu başlatılamıyor.")
        return None

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analiz", analyze_command))
    application.add_handler(CommandHandler("pozisyonlar", positions_command))
    application.add_handler(CommandHandler("kapat", close_command))

    return application