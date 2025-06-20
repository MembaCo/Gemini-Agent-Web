# run.py
# @author: Memba Co.

import threading
import logging
from waitress import serve

# Projemizin ana mantığını ve yapılandırmasını içeri aktarıyoruz
import config
import database
from main import background_position_checker, _perform_analysis, _execute_single_scan_cycle, _get_reanalysis_report, handle_manual_close, get_status_as_string, initialize_exchange
from telegram_bot import run_telegram_bot
from dashboard.app import create_app # Web arayüzü uygulamamızı buradan alacağız

# Temel loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Uygulamanın ana başlangıç fonksiyonu.
    """
    logging.info("======================================================")
    logging.info(f"   GEMINI TRADING AGENT BAŞLATILIYOR (Umbrel Modu)")
    logging.info(f"                 Versiyon: {config.APP_VERSION}")
    logging.info("======================================================")
    logging.info(f"CANLI İŞLEM MODU: {'✅ AKTİF' if config.LIVE_TRADING else '❌ KAPALI (Simülasyon)'}")
    logging.info(f"TELEGRAM BİLDİRİMLERİ: {'✅ AKTİF' if config.TELEGRAM_ENABLED else '❌ KAPALI'}")
    logging.info("======================================================")

    # 1. Veritabanını ve Borsa bağlantısını başlat
    database.init_db()
    initialize_exchange(config.DEFAULT_MARKET_TYPE)

    # main.py'den alınan ana uygulama fonksiyonlarını bir sözlükte topluyoruz.
    # Bu sözlüğü hem Telegram botuna hem de Web arayüzüne (Flask app) geçireceğiz.
    bot_actions = {
        'analyze': _perform_analysis,
        'scan': _execute_single_scan_cycle,
        'reanalyze': _get_reanalysis_report,
        'close': handle_manual_close,
        'get_status': get_status_as_string
    }

    # 2. Arka plan pozisyon kontrolcüsünü bir thread'de başlat
    checker_thread = threading.Thread(target=background_position_checker, daemon=True)
    checker_thread.start()
    logging.info("✅ Arka plan pozisyon kontrolcüsü başlatıldı.")

    # 3. Telegram botunu (eğer aktifse) bir thread'de başlat
    if config.TELEGRAM_ENABLED:
        telegram_thread = threading.Thread(target=run_telegram_bot, args=(bot_actions,), daemon=True)
        telegram_thread.start()
        logging.info("✅ Telegram botu dinleme modunda başlatıldı.")

    # 4. Flask web uygulamasını oluştur ve bot_actions'ı ona aktar
    flask_app = create_app(bot_actions)

    # 5. Üretime uygun bir WSGI sunucusu olan Waitress ile web arayüzünü yayınla
    logging.info("📈 Web Arayüzü (Dashboard) başlatılıyor...")
    logging.info("Sunucu http://0.0.0.0:5001 adresinde çalışıyor.")
    serve(flask_app, host='0.0.0.0', port=5001)

if __name__ == "__main__":
    main()