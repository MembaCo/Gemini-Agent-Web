# backend/telegram_bot.py
# @author: Memba Co.

import logging
import os
import warnings
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.warnings import PTBUserWarning
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from google.api_core.exceptions import ResourceExhausted
from io import BytesIO
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import json

from core import app_config, trader, agent as core_agent
from tools import (
    _get_unified_symbol, get_price_with_cache, get_technical_indicators,
    exchange as exchange_tools
)
import database
from ccxt.base.errors import BadSymbol

# DÜZELTME: ConversationHandler ile ilgili uyarıyı gizler.
# Bu, botun işlevselliğini etkilemez, sadece konsol çıktısını temizler.
warnings.filterwarnings("ignore", category=PTBUserWarning)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ConversationHandler için durumlar
SELECTING_CATEGORY, SELECTING_SETTING, TYPING_VALUE = range(3)

# --- Yardımcı Fonksiyonlar ---

def str_to_correct_type(value_str: str, target_type: str):
    try:
        if target_type == 'int': return int(value_str)
        if target_type == 'float': return float(value_str)
        if target_type == 'bool': return value_str.lower() in ['true', '1', 'evet', 'acik', 'on']
        if target_type == 'list': return [item.strip().upper() for item in value_str.split(',')]
        return value_str
    except (ValueError, TypeError):
        return None

# --- Komut ve Buton İşleyici Fonksiyonlar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Merhaba! *Gemini Trading Agent* hizmetinizde.\n\n'
        'Kullanılabilir komutlar:\n'
        '• `/analiz <SEMBOL>` - Sembol analizi yapar.\n'
        '• `/pozisyonlar` - Açık pozisyonları interaktif yönetir.\n'
        '• `/rapor` - Genel performans raporu sunar.\n'
        '• `/ayarlar` - Mevcut ayarları gösterir.\n'
        '• `/ayar_degistir` - Ayarları interaktif değiştirir.\n'
        '• `/durdur` & `/baslat` - Canlı ticareti durdurur/başlatır.\n'
        '• `/grafik <SEMBOL> <ARALIK>` - Anlık grafik çizer.\n'
        '• `/detay <SEMBOL>` - Pozisyon detaylarını gösterir.\n'
        '• `/iptal` - Aktif bir işlemi iptal eder.',
        parse_mode=ParseMode.MARKDOWN
    )

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        history = database.get_trade_history()
        positions = database.get_all_positions()
        total_pnl = sum(t['pnl'] for t in history)
        total_trades = len(history)
        winning_trades = sum(1 for t in history if t['pnl'] > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        message = (
            f"📊 *Performans Raporu*\n\n"
            f"• *Toplam P&L:* `{total_pnl:+.2f} USDT`\n"
            f"• *Kazanma Oranı:* `{win_rate:.2f}%`\n"
            f"• *Kazanan İşlem:* `{winning_trades}`\n"
            f"• *Kaybeden İşlem:* `{total_trades - winning_trades}`\n"
            f"• *Aktif Pozisyon:* `{len(positions)}`"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Rapor oluşturulurken hata: {e}")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        settings = database.get_all_settings()
        message = (
            f"⚙️ *Mevcut Ayarlar*\n\n"
            f"• *Canlı Ticaret:* `{'✅ AKTİF' if settings.get('LIVE_TRADING') else '❌ PASİF'}`\n"
            f"• *Risk/İşlem:* `{settings.get('RISK_PER_TRADE_PERCENT')}%`\n"
            f"• *Maks. Pozisyon:* `{settings.get('MAX_CONCURRENT_TRADES')}`\n"
            f"• *Hızlı Kâr Alma:* `{'✅ AKTİF' if settings.get('USE_SCALP_EXIT') else '❌ PASİF'}` (`{settings.get('SCALP_EXIT_PROFIT_PERCENT')}%`)\n"
            f"• *İz Süren SL:* `{'✅ AKTİF' if settings.get('USE_TRAILING_STOP_LOSS') else '❌ PASİF'}`"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Ayarlar alınırken hata: {e}")

async def toggle_trading_command(update: Update, context: ContextTypes.DEFAULT_TYPE, live: bool) -> None:
    try:
        database.update_settings({'LIVE_TRADING': live})
        app_config.load_config()
        status = "AKTİF" if live else "PASİF"
        await update.message.reply_text(f"✅ Canlı ticaret modu başarıyla *{status}* hale getirildi.")
    except Exception as e:
        await update.message.reply_text(f"Ayar değiştirilirken hata: {e}")

async def positions_interactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    positions = database.get_all_positions()
    if not positions:
        await update.message.reply_text("Yönetilen açık pozisyon bulunmuyor.")
        return

    for pos in positions:
        symbol_md = pos['symbol'].replace('/', r'\/')
        side_emoji = "📈" if pos.get('side') == 'buy' else "📉"
        pnl_text = ""
        current_price = get_price_with_cache(pos['symbol'])
        if current_price:
            pnl = (current_price - pos['entry_price']) * pos['amount'] if pos['side'] == 'buy' else (pos['entry_price'] - current_price) * pos['amount']
            pnl_emoji = "✅" if pnl >= 0 else "🔻"
            pnl_text = f" | *PNL:* `{pnl:+.2f}$` {pnl_emoji}"
        
        message = f"{side_emoji} `{symbol_md}`\n  *Giriş:* `{pos['entry_price']:.4f}`{pnl_text}"
        
        keyboard = [[
            InlineKeyboardButton("Yeniden Analiz Et 🤖", callback_data=f"reanalyze_{pos['symbol']}"),
            InlineKeyboardButton("Kapat ❌", callback_data=f"close_{pos['symbol']}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 2:
        await update.message.reply_text("Kullanım: `/grafik <SEMBOL> <ZAMAN_ARALIĞI>` (örn: `/grafik btc 1h`)")
        return
    try:
        symbol_input, timeframe = context.args[0], context.args[1]
        symbol = _get_unified_symbol(symbol_input)
        await update.message.reply_text(f"`{symbol} - {timeframe}` için grafik oluşturuluyor...")
        bars = exchange_tools.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.ta.rsi(length=14, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        ap = [
            mpf.make_addplot(df['RSI_14'], panel=2, color='purple', ylabel='RSI'),
            mpf.make_addplot(df['SMA_20'], panel=0, color='blue'),
            mpf.make_addplot(df['SMA_50'], panel=0, color='orange')
        ]
        buf = BytesIO()
        mpf.plot(df, type='candle', style='charles', title=f'\n{symbol} - {timeframe}', volume=True, addplot=ap, savefig=dict(fname=buf, dpi=150), panel_ratios=(3,1,1))
        buf.seek(0)
        await update.message.reply_photo(photo=buf)
    except Exception as e:
        await update.message.reply_text(f"Grafik oluşturulurken hata: {e}")

async def detail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Lütfen detayını görmek istediğiniz pozisyonun sembolünü girin.")
        return
    symbol = _get_unified_symbol(context.args[0])
    pos = database.get_position_by_symbol(symbol)
    if not pos:
        await update.message.reply_text(f"`{symbol}` için açık pozisyon bulunamadı.")
        return
    pnl, pnl_percentage = 0, 0
    current_price = get_price_with_cache(pos['symbol'])
    if current_price:
        pnl = (current_price - pos['entry_price']) * pos['amount'] if pos['side'] == 'buy' else (pos['entry_price'] - current_price) * pos['amount']
        margin = (pos['entry_price'] * pos['amount']) / pos['leverage']
        pnl_percentage = (pnl / margin) * 100 if margin > 0 else 0
    message = (
        f"📈 *Pozisyon Detayı: {pos['symbol']}*\n\n"
        f"• *Yön:* `{pos['side'].upper()}`\n"
        f"• *Açılış Sebebi:* `{pos.get('reason', 'Belirtilmemiş')}`\n"
        f"• *Açılış Zamanı:* `{pos['created_at']}`\n"
        f"• *PNL:* `{pnl:+.2f}$ ({pnl_percentage:+.2f}%)`\n"
        f"• *Giriş Fiyatı:* `{pos['entry_price']}`\n"
        f"• *Mevcut SL:* `{pos['stop_loss']}`\n"
        f"• *Mevcut TP:* `{pos['take_profit']}`"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text('Lütfen bir sembol girin. Örnek: `/analiz btc`')
            return
        symbol = _get_unified_symbol(context.args[0])
        await update.message.reply_text(f'`{symbol}` için analiz başlatılıyor, lütfen bekleyin...')
        current_price = get_price_with_cache(symbol)
        if current_price is None: raise BadSymbol(f"Fiyat bilgisi alınamadı: {symbol}")
        use_mta = app_config.settings.get('USE_MTA_ANALYSIS', True)
        entry_timeframe = '15m'
        entry_indicators_result = get_technical_indicators(f"{symbol},{entry_timeframe}")
        if entry_indicators_result.get("status") != "success": raise ValueError(f"Teknik veri alınamadı: {entry_indicators_result.get('message')}")
        final_prompt = ""
        if use_mta:
            trend_timeframe = app_config.settings.get('MTA_TREND_TIMEFRAME', '4h')
            trend_indicators_result = get_technical_indicators(f"{symbol},{trend_timeframe}")
            if trend_indicators_result.get("status") != "success": raise ValueError(f"Trend verisi alınamadı: {trend_indicators_result.get('message')}")
            final_prompt = core_agent.create_mta_analysis_prompt(symbol, current_price, entry_timeframe, entry_indicators_result["data"], trend_timeframe, trend_indicators_result["data"])
        else:
            final_prompt = core_agent.create_final_analysis_prompt(symbol, entry_timeframe, current_price, entry_indicators_result["data"])
        result = core_agent.llm_invoke_with_fallback(final_prompt)
        parsed_data = core_agent.parse_agent_response(result.content)
        if not parsed_data:
            await update.message.reply_text(f'`{symbol}` için yapay zekadan geçerli bir analiz yanıtı alınamadı.')
            return
        rec = parsed_data.get('recommendation', 'N/A')
        reason = parsed_data.get('reason', 'N/A')
        response_message = (f"*Analiz Sonucu: `{symbol}`*\n\n🔮 *Tavsiye:* `{rec}`\n\n📝 *Gerekçe:* {reason}")
        await update.message.reply_text(response_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f'Analiz sırasında bir hata oluştu: {str(e)}')

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action, symbol = query.data.split('_', 1)

    if action == 'reanalyze':
        await query.edit_message_text(text=f"`{symbol}` için yeniden analiz başlatılıyor...", parse_mode=ParseMode.MARKDOWN)
        try:
            position_to_manage = database.get_position_by_symbol(symbol)
            if not position_to_manage:
                await query.edit_message_text(text=f"Hata: `{symbol}` pozisyonu bulunamadı.", parse_mode=ParseMode.MARKDOWN)
                return
            current_price = get_price_with_cache(symbol)
            if current_price is None:
                await query.edit_message_text(text=f"Hata: `{symbol}` için fiyat alınamadı.", parse_mode=ParseMode.MARKDOWN)
                return
            timeframe = position_to_manage.get('timeframe', '15m')
            indicators_result = get_technical_indicators(f"{symbol},{timeframe}")
            if indicators_result.get("status") != "success":
                await query.edit_message_text(text=f"Hata: Göstergeler alınamadı: {indicators_result.get('message')}", parse_mode=ParseMode.MARKDOWN)
                return
            reanalysis_prompt = core_agent.create_reanalysis_prompt(position=position_to_manage, current_price=current_price, indicators=indicators_result['data'])
            result = core_agent.llm_invoke_with_fallback(reanalysis_prompt)
            parsed_data = core_agent.parse_agent_response(result.content)
            if not parsed_data or "recommendation" not in parsed_data:
                await query.edit_message_text(text=f"`{symbol}` için AI'dan geçerli yanıt alınamadı.", parse_mode=ParseMode.MARKDOWN)
                return
            rec = parsed_data.get('recommendation', 'N/A')
            reason = parsed_data.get('reason', 'N/A')
            response_message = (f"*Yeniden Analiz Sonucu: `{symbol}`*\n🔮 *Tavsiye:* `{rec}`\n📝 *Gerekçe:* {reason}")
            await query.edit_message_text(text=response_message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.edit_message_text(text=f"Yeniden analiz sırasında hata: {e}", parse_mode=ParseMode.MARKDOWN)
    elif action == 'close':
        await query.edit_message_text(text=f"`{symbol}` pozisyonu kapatılıyor...", parse_mode=ParseMode.MARKDOWN)
        try:
            result = trader.close_existing_trade(symbol, close_reason="MANUAL_TELEGRAM_BTN")
            await query.edit_message_text(text=f"✅ `{symbol}` pozisyonu başarıyla kapatıldı.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.edit_message_text(text=f"❌ Kapatma hatası: {e}", parse_mode=ParseMode.MARKDOWN)

# --- Ayar Değiştirme Sihirbazı (ConversationHandler) ---

async def settings_conversation_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Genel Ticaret & Risk", callback_data="category_RISK")],
        [InlineKeyboardButton("Kâr & Zarar Stratejileri", callback_data="category_STRATEGY")],
        [InlineKeyboardButton("Proaktif Tarayıcı", callback_data="category_SCANNER")],
        [InlineKeyboardButton("İptal", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "Hangi kategorideki ayarı değiştirmek istersiniz?"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    return SELECTING_SETTING

async def select_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    category_key = query.data.split('_')[1]
    setting_groups = {
        "RISK": ['LIVE_TRADING', 'VIRTUAL_BALANCE', 'LEVERAGE', 'RISK_PER_TRADE_PERCENT', 'MAX_CONCURRENT_TRADES'],
        "STRATEGY": ['USE_SCALP_EXIT', 'SCALP_EXIT_PROFIT_PERCENT', 'USE_TRAILING_STOP_LOSS', 'TRAILING_STOP_ACTIVATION_PERCENT'],
        "SCANNER": ['PROACTIVE_SCAN_ENABLED', 'PROACTIVE_SCAN_INTERVAL_SECONDS', 'PROACTIVE_SCAN_AUTO_CONFIRM']
    }
    keyboard = [[InlineKeyboardButton(s_name, callback_data=f"setting_{s_name}")] for s_name in setting_groups.get(category_key, [])]
    keyboard.append([InlineKeyboardButton("<< Geri", callback_data="back_to_category")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Hangi ayarı değiştirmek istersiniz?", reply_markup=reply_markup)
    return TYPING_VALUE

async def ask_for_value_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    setting_key = query.data.split('_')[1]
    context.user_data['setting_to_change'] = setting_key
    settings = database.get_all_settings()
    current_value = settings.get(setting_key)
    await query.edit_message_text(
        f"`{setting_key}` için yeni değeri girin.\n*Mevcut Değer:* `{current_value}`\n\n_İşlemi iptal etmek için /iptal yazın._",
        parse_mode=ParseMode.MARKDOWN
    )
    return TYPING_VALUE

async def receive_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    setting_key = context.user_data.get('setting_to_change')
    if not setting_key:
        await update.message.reply_text("Hata, lütfen `/ayar_degistir` ile yeniden başlatın.")
        return ConversationHandler.END
    new_value_str = update.message.text
    all_settings = database.get_all_settings()
    setting_type = type(all_settings.get(setting_key)).__name__
    new_value = str_to_correct_type(new_value_str, setting_type)
    if new_value is None:
        await update.message.reply_text(f"Geçersiz değer: '{new_value_str}'. Lütfen doğru formatta girin.")
        return TYPING_VALUE
    try:
        database.update_settings({setting_key: new_value})
        app_config.load_config()
        await update.message.reply_text(f"✅ Ayar güncellendi!\n`{setting_key}` = `{new_value}`")
    except Exception as e:
        await update.message.reply_text(f"❌ Ayar güncellenirken hata: {e}")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message_text = "İşlem iptal edildi."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=message_text)
    else:
        await update.message.reply_text(message_text)
    return ConversationHandler.END

# --- Ana Bot Uygulaması Oluşturucu ---

def create_telegram_app():
    if not TOKEN:
        logging.warning("Telegram Bot Token bulunamadı. Telegram botu başlatılamıyor.")
        return None
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('ayar_degistir', settings_conversation_start)],
        states={
            SELECTING_SETTING: [CallbackQueryHandler(select_setting_callback, pattern='^category_')],
            TYPING_VALUE: [
                CallbackQueryHandler(ask_for_value_callback, pattern='^setting_'),
                CallbackQueryHandler(settings_conversation_start, pattern='^back_to_category$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_value)
            ],
        },
        fallbacks=[
            CommandHandler('iptal', cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern='^cancel$')
        ],
        per_message=False
    )
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rapor", report_command))
    application.add_handler(CommandHandler("ayarlar", settings_command))
    application.add_handler(CommandHandler("durdur", lambda u, c: toggle_trading_command(u, c, live=False)))
    application.add_handler(CommandHandler("baslat", lambda u, c: toggle_trading_command(u, c, live=True)))
    application.add_handler(CommandHandler("pozisyonlar", positions_interactive_command))
    application.add_handler(CommandHandler("grafik", chart_command))
    application.add_handler(CommandHandler("detay", detail_command))
    application.add_handler(CommandHandler("analiz", analyze_command))
    
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    return application
