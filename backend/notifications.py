# backend/notifications.py
# @author: Memba Co.

import requests
import logging
import os
from dotenv import load_dotenv
from core import app_config
import re # YENİ: Regex kütüphanesi import edildi

load_dotenv()

def escape_markdown_v2(text: str) -> str:
    """
    Telegram'ın MarkdownV2 formatı için özel karakterleri kaçış karakteriyle (\) değiştirir.
    """
    if not isinstance(text, str):
        text = str(text)
    # Kaçış karakterleri: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_telegram_message(message: str):
    """
    Telegram'a bir metin mesajı gönderir.
    Bu fonksiyon, ayarlar ve .env dosyası üzerinden yapılandırılmıştır.
    """
    if not app_config.settings.get('TELEGRAM_ENABLED'):
        return
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logging.warning("Telegram token veya sohbet ID'si .env dosyasında bulunamadı. Bildirim gönderilemiyor.")
        return
        
    # DİKKAT: Telegram API'si MarkdownV2 için farklı bir parse_mode değeri ister.
    # Ancak biz manuel olarak escape yaptığımız için eski parse_mode'u korumak daha güvenli olabilir.
    # Ya da parse_mode'u "MarkdownV2" yapıp bu fonksiyonu kullanabilirsiniz.
    # Şimdilik mevcut yapıyı koruyarak sadece tehlikeli olabilecek karakterleri escape edelim.
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            # Hata durumunda, formatlanmamış mesajı logla
            logging.error(f"Telegram'a bildirim gönderilemedi: {response.status_code} - {response.text}")
            logging.error(f"Gönderilemeyen Mesaj İçeriği: {message}")
    except requests.RequestException as e:
        logging.error(f"Telegram API'sine bağlanırken bir ağ hatası oluştu: {e}")

def format_open_position_message(pos_details: dict, is_simulation: bool = False) -> str:
    """
    Yeni açılan bir pozisyon için formatlı bir Telegram mesajı oluşturur.
    """
    # DÜZELTME: Değişkenler escape ediliyor
    symbol = escape_markdown_v2(pos_details.get('symbol', 'N/A'))
    side = escape_markdown_v2(pos_details.get('side', 'N/A').upper())
    
    side_emoji = "📈" if pos_details.get('side') == 'buy' else "📉"
    title = f"*{side_emoji} YENİ POZİSYON AÇILDI* `{symbol}`"
    if is_simulation:
        title = f"*[SİMÜLASYON] {title}*" # Simülasyon başlığını da kalın yapalım
    
    return (
        f"{title}\n\n"
        f"➡️ *Yön:* `{side}`\n"
        f"💰 *Giriş Fiyatı:* `{pos_details.get('entry_price', 0):.4f}`\n"
        f"📦 *Miktar:* `{pos_details.get('amount', 0):.4f}`\n"
        f"⚙️ *Kaldıraç:* `{int(pos_details.get('leverage', 1))}x`\n\n"
        f"🛑 *Stop-Loss:* `{pos_details.get('stop_loss', 0):.4f}`\n"
        f"🎯 *Take-Profit:* `{pos_details.get('take_profit', 0):.4f}`"
    )

def format_close_position_message(closed_pos: dict, pnl: float, status: str, is_simulation: bool = False) -> str:
    """
    Kapanan bir pozisyon için formatlı bir Telegram mesajı oluşturur.
    """
    # DÜZELTME: Değişkenler escape ediliyor
    symbol = escape_markdown_v2(closed_pos.get('symbol', 'N/A'))
    status_text = escape_markdown_v2(status)
    
    pnl_emoji = "✅" if pnl >= 0 else "❌"
    title = f"*{pnl_emoji} POZİSYON KAPANDI* `{symbol}`"
    if is_simulation:
        title = f"*[SİMÜLASYON] {title}*"

    return (
        f"{title}\n\n"
        f"▪️ *Kapanış Nedeni:* `{status_text}`\n"
        f"💵 *P&L:* `{pnl:+.2f} USDT`\n\n"
        f"Giriş Fiyatı: `{closed_pos.get('entry_price', 0):.4f}`\n"
        f"Kapanış Fiyatı: `{closed_pos.get('close_price', 0):.4f}`"
    )

def format_partial_tp_message(symbol: str, close_amount: float, remaining_amount: float, entry_price: float) -> str:
    """
    Kısmi kâr alınan bir işlem için formatlı bir Telegram mesajı oluşturur.
    """
    # DÜZELTME: Değişkenler escape ediliyor
    symbol_md = escape_markdown_v2(symbol)
    is_live = app_config.settings.get('LIVE_TRADING', False)
    title = f"✅ *KISMİ KÂR ALINDI* `{symbol_md}`"
    if not is_live:
        title = f"*[SİMÜLASYON] {title}*"

    return (
        f"{title}\n\n"
        f"Pozisyonun bir kısmı kapatılarak kâr realize edildi ve kalan pozisyonun riski sıfırlandı.\n\n"
        f"▪️ *Kapatılan Miktar:* `{close_amount:.4f}`\n"
        f"▪️ *Kalan Miktar:* `{remaining_amount:.4f}`\n"
        f"▪️ *Yeni Stop-Loss:* `{entry_price:.4f}` (Giriş Seviyesi)"
    )