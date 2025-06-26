# backend/config_defaults.py
# @author: Memba Co.
# Bu dosya, ayarlar veritabanına ilk kez yazılırken kullanılacak
# varsayılan değerleri ve açıklamalarını içerir.

default_settings = {
    # === UYGULAMA & MODEL AYARLARI ===
    "GEMINI_MODEL": 'gemini-1.5-flash',
    # YENİ: Model Fallback (Yedek) Sırası. Bir modelin kotası dolduğunda,
    # listedeki bir sonrakine otomatik olarak geçilir.
    "GEMINI_MODEL_FALLBACK_ORDER": [
        "gemini-1.5-flash",        # Hızlı ve ucuz, ilk deneme için ideal.
        "gemini-2.5-flash",        # Biraz daha yetenekli ve maliyet-etkin.
        "gemini-1.5-pro",          # Daha karmaşık durumlar için güçlü bir seçenek.
        "gemini-2.5-pro",          # En güçlü model, son çare olarak.
    ],

    # === CANLI İŞLEM AYARI ===
    "LIVE_TRADING": True,

    # === TEMEL STRATEJİ AYARLARI ===
    "USE_MTA_ANALYSIS": True,               # Manuel analizlerde Çoklu Zaman Aralığı (MTA) analizi kullanılsın mı?
    "MTA_TREND_TIMEFRAME": "4h",            # MTA için ana trendin belirleneceği üst zaman aralığı.
    "DEFAULT_ORDER_TYPE": 'LIMIT',          # Varsayılan emir tipi ('LIMIT' veya 'MARKET').
    "DEFAULT_MARKET_TYPE": 'future',        # İşlem yapılacak piyasa tipi ('future' veya 'spot').
    "LEVERAGE": 10.0,                       # Vadeli işlemlerde kullanılacak kaldıraç oranı.

    # === RİSK YÖNETİMİ AYARLARI ===
    "RISK_PER_TRADE_PERCENT": 5.0,          # Her bir işlemde cüzdanın yüzde kaçının riske edileceği.
    "MAX_CONCURRENT_TRADES": 5,             # Aynı anda açık olabilecek maksimum pozisyon sayısı.
    
    # --- Stop-Loss ve Take-Profit Ayarları ---
    "USE_ATR_FOR_SLTP": True,               # SL/TP belirlemek için ATR (Average True Range) kullanılsın mı?
    "ATR_MULTIPLIER_SL": 2.0,               # Stop-Loss mesafesini belirlemek için ATR değerinin çarpılacağı katsayı.
    "RISK_REWARD_RATIO_TP": 2.0,            # Kâr Al (Take-Profit) seviyesinin, riske (SL mesafesi) göre oranı.

    # --- Gelişmiş Kâr Alma Stratejileri ---
    "USE_TRAILING_STOP_LOSS": True,         # İz Süren Zarar Durdur aktif edilsin mi?
    "TRAILING_STOP_ACTIVATION_PERCENT": 1.5,# Pozisyonun yüzde kaç kâra geçtiğinde Trailing SL'nin devreye gireceği.
    "USE_PARTIAL_TP": True,                 # Kısmi Kâr Alma stratejisi aktif edilsin mi?
    "PARTIAL_TP_TARGET_RR": 1.0,            # 1R'a ulaşıldığında (riskedilen miktar kadar kâr edildiğinde) kısmi kâr alınsın mı?
    "PARTIAL_TP_CLOSE_PERCENT": 50.0,       # Kısmi kâr alınırken pozisyonun yüzde kaçının kapatılacağı.

    # === OTOMASYON & TARAYICI AYARLARI ===
    "POSITION_CHECK_INTERVAL_SECONDS": 60,  # Arka plan görevinin aktif pozisyonları kaç saniyede bir kontrol edeceği.
    "ORPHAN_ORDER_CHECK_INTERVAL_SECONDS": 300, # Yetim (pozisyonsuz) emirleri kontrol etme sıklığı (saniye).
    "PROACTIVE_SCAN_ENABLED": False,        # Uygulama başladığında Proaktif Tarayıcı arka plan görevi çalışsın mı?
    "PROACTIVE_SCAN_INTERVAL_SECONDS": 900, # Proaktif Tarayıcının kaç saniyede bir piyasayı tarayacağı (15 dakika).
    "PROACTIVE_SCAN_AUTO_CONFIRM": False,   # Tarayıcı bir fırsat bulduğunda kullanıcı onayı olmadan otomatik işlem açsın mı?
    "PROACTIVE_SCAN_IN_LOOP": True,         # Arka plan görevinin döngüsel olarak çalışıp çalışmayacağı.
    "PROACTIVE_SCAN_USE_GAINERS_LOSERS": True,# Tarama listesine "En Çok Yükselenler/Düşenler" eklensin mi?
    "PROACTIVE_SCAN_TOP_N": 10,             # Yükselenler/Düşenler listesinden kaç coinin analize dahil edileceği.
    "PROACTIVE_SCAN_MIN_VOLUME_USDT": 1000000,# Taranacak coinler için minimum 24 saatlik işlem hacmi (USDT cinsinden).
    "PROACTIVE_SCAN_MTA_ENABLED": True,     # Proaktif tarama sırasında MTA analizi yapılsın mı?
    "PROACTIVE_SCAN_ENTRY_TIMEFRAME": "15m",# Proaktif taramada giriş sinyali için kullanılacak zaman aralığı.
    "PROACTIVE_SCAN_TREND_TIMEFRAME": "4h", # Proaktif taramada ana trend için kullanılacak zaman aralığı.
    
    # === Hacim Patlaması Taraması Ayarları ===
    "PROACTIVE_SCAN_USE_VOLUME_SPIKE": True, # Tarama listesine 'Hacim Patlaması' yaşayanları ekle
    "PROACTIVE_SCAN_VOLUME_TIMEFRAME": "1h", # Hacim analizi için kullanılacak zaman aralığı
    "PROACTIVE_SCAN_VOLUME_MULTIPLIER": 5.0, # Son mumun hacmi, ortalamanın kaç katı olmalı
    "PROACTIVE_SCAN_VOLUME_PERIOD": 24,      # Hacim ortalaması için kaç mum geriye bakılacak
    
    # --- FİLTRELEME & BİLDİRİM ---
    "PROACTIVE_SCAN_BLACKLIST": ["SHIB", "PEPE", "MEME", "DOGE"], # Taramalarda asla analize dahil edilmeyecek coinler.
    "PROACTIVE_SCAN_WHITELIST": ["BTC", "ETH", "SOL"],           # Her tarama döngüsünde mutlaka analize dahil edilecek coinler.
    "TELEGRAM_ENABLED": True,               # Telegram bildirimleri aktif edilsin mi?
}
