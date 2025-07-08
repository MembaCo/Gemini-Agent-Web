# backend/config_defaults.py
# @author: Memba Co.
# Bu dosya, ayarlar veritabanına ilk kez yazılırken kullanılacak
# varsayılan değerleri ve açıklamalarını içerir.

default_settings = {
    # === UYGULAMA & MODEL AYARLARI ===
    "GEMINI_MODEL": 'gemini-1.5-flash',
    "GEMINI_MODEL_FALLBACK_ORDER": [
        "gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-2.5-pro",
    ],

# === CANLI İŞLEM AYARI ===
    "LIVE_TRADING": True,
    # YENİ: Simülasyon modu için sanal bakiye ayarı
    "VIRTUAL_BALANCE": 10000.0,

    # === TEMEL STRATEJİ AYARLARI ===
    "USE_MTA_ANALYSIS": True,
    "MTA_TREND_TIMEFRAME": "4h",
    "DEFAULT_ORDER_TYPE": 'LIMIT',
    "DEFAULT_MARKET_TYPE": 'future',
    "LEVERAGE": 10.0,

    # === RİSK YÖNETİMİ AYARLARI ===
    "RISK_PER_TRADE_PERCENT": 5.0,
    "MAX_CONCURRENT_TRADES": 5,
    
    # --- Stop-Loss ve Take-Profit Ayarları ---
    "USE_ATR_FOR_SLTP": True,
    "ATR_MULTIPLIER_SL": 2.0,
    "RISK_REWARD_RATIO_TP": 2.0,
    "USE_SCALP_EXIT": False,
    "SCALP_EXIT_PROFIT_PERCENT": 5.0, 

    # --- Gelişmiş Kâr Alma Stratejileri ---
    "USE_TRAILING_STOP_LOSS": True,
    "TRAILING_STOP_ACTIVATION_PERCENT": 1.5,
    "USE_PARTIAL_TP": True,
    "PARTIAL_TP_TARGET_RR": 1.0,
    "PARTIAL_TP_CLOSE_PERCENT": 50.0,

    # YENİ: Akıllı Zarar Azaltma (Bailout Exit) Ayarları
    "USE_BAILOUT_EXIT": True,              # Bu özellik aktif edilsin mi?
    "BAILOUT_ARM_LOSS_PERCENT": -2.0,      # Pozisyon yüzde kaç zarara ulaşınca bu özellik devreye girsin?
    "BAILOUT_RECOVERY_PERCENT": 1.0,       # Görülen en dipten yüzde kaç toparlanınca pozisyon kapatılsın?
    "USE_AI_BAILOUT_CONFIRMATION": True,   # YENİ: Bailout kararını AI'a onaylat. False ise, AI'a sormadan direkt kapatır.

    # === OTOMASYON & TARAYICI AYARLARI ===
    "POSITION_CHECK_INTERVAL_SECONDS": 60,
    "ORPHAN_ORDER_CHECK_INTERVAL_SECONDS": 300,
    "PROACTIVE_SCAN_ENABLED": False,
    "POSITION_SYNC_INTERVAL_SECONDS": 300,
    "PROACTIVE_SCAN_INTERVAL_SECONDS": 900,
    "PROACTIVE_SCAN_AUTO_CONFIRM": False,
    "PROACTIVE_SCAN_IN_LOOP": True,
    "PROACTIVE_SCAN_USE_GAINERS_LOSERS": True,
    "PROACTIVE_SCAN_TOP_N": 10,
    "PROACTIVE_SCAN_MIN_VOLUME_USDT": 1000000,
    "PROACTIVE_SCAN_MTA_ENABLED": True,
    "PROACTIVE_SCAN_ENTRY_TIMEFRAME": "15m",
    "PROACTIVE_SCAN_TREND_TIMEFRAME": "4h",
    
    # --- Hacim Patlaması Taraması Ayarları ---
    "PROACTIVE_SCAN_USE_VOLUME_SPIKE": True,
    "PROACTIVE_SCAN_VOLUME_TIMEFRAME": "1h",
    "PROACTIVE_SCAN_VOLUME_MULTIPLIER": 5.0,
    "PROACTIVE_SCAN_VOLUME_PERIOD": 24,

    # --- AI Öncesi Filtreleme Ayarları ---
    "PROACTIVE_SCAN_PREFILTER_ENABLED": True,
    "PROACTIVE_SCAN_RSI_LOWER": 35,
    "PROACTIVE_SCAN_RSI_UPPER": 65,
    "PROACTIVE_SCAN_ADX_THRESHOLD": 20,
    
    # YENİ: Gelişmiş Filtre Ayarları
    "PROACTIVE_SCAN_USE_VOLATILITY_FILTER": True, # ATR kullanarak volatilite filtresi aktif edilsin mi?
    "PROACTIVE_SCAN_ATR_PERIOD": 14,              # Volatilite hesaplaması için ATR periyodu.
    "PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT": 0.5,  # ATR değeri, anlık fiyatın en az yüzde kaçı olmalı? (örn: 0.5 -> %0.5)
    "PROACTIVE_SCAN_USE_VOLUME_FILTER": True,     # Hacim onayı filtresi aktif edilsin mi?
    "PROACTIVE_SCAN_VOLUME_AVG_PERIOD": 20,       # Ortalama hacim hesaplaması için kullanılacak periyot.
    "PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER": 1.2, # Son mumun hacmi, ortalama hacmin en az kaç katı olmalı? (örn: 1.2 -> %20 daha fazla)
    
    # --- FİLTRELEME & BİLDİRİM ---
    "PROACTIVE_SCAN_BLACKLIST": ["SHIB", "PEPE", "MEME", "DOGE"],
    "PROACTIVE_SCAN_WHITELIST": ["BTC", "ETH", "SOL"],
    "TELEGRAM_ENABLED": True,
}