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
    "LIVE_TRADING": False,
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

    # YENİ: Dinamik Risk Yönetimi Ayarları
    "USE_DYNAMIC_RISK": True,                   # Bu özellik aktif edilsin mi?
    "DYNAMIC_RISK_ATR_PERIOD": 14,              # Volatilite ölçümü için kullanılacak ATR periyodu.
    "DYNAMIC_RISK_BASE_RISK": 1.5,              # Ortalama volatilitede kullanılacak temel risk yüzdesi.
    "DYNAMIC_RISK_LOW_VOL_THRESHOLD": 1.5,      # ATR / Fiyat oranının bu değerin altına düşmesi "Düşük Volatilite" sayılır.
    "DYNAMIC_RISK_LOW_VOL_MULTIPLIER": 1.5,     # Düşük volatilitede temel riskin çarpılacağı katsayı (örn: 1.5x daha fazla risk al).
    "DYNAMIC_RISK_HIGH_VOL_THRESHOLD": 4.0,     # ATR / Fiyat oranının bu değerin üstüne çıkması "Yüksek Volatilite" sayılır.
    "DYNAMIC_RISK_HIGH_VOL_MULTIPLIER": 0.75,   # Yüksek volatilitede temel riskin çarpılacağı katsayı (örn: 0.75x daha az risk al).

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

    # --- Akıllı Zarar Azaltma (Bailout Exit) Ayarları ---
    "USE_BAILOUT_EXIT": True,
    "BAILOUT_ARM_LOSS_PERCENT": -2.0,
    "BAILOUT_RECOVERY_PERCENT": 1.0,
    "USE_AI_BAILOUT_CONFIRMATION": True,

    # (Diğer ayarlarınız burada devam ediyor...)
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
    "PROACTIVE_SCAN_MIN_VOLUME_USDT": 750000,
    "PROACTIVE_SCAN_MTA_ENABLED": True,
    "PROACTIVE_SCAN_USE_SENTIMENT": True, # Twitter (X) duyarlılık analizi
    "USE_NEWSAPI": True,                  # NewsAPI.org haber kaynağı
    "USE_CRYPTOPANIC_NEWS": True,         # CryptoPanic.com haber kaynağı
    "PROACTIVE_SCAN_ENTRY_TIMEFRAME": "15m",
    "PROACTIVE_SCAN_TREND_TIMEFRAME": "4h",
    
    # --- Hacim Patlaması Taraması Ayarları ---
    "PROACTIVE_SCAN_USE_VOLUME_SPIKE": True,
    "PROACTIVE_SCAN_VOLUME_TIMEFRAME": "1h",
    "PROACTIVE_SCAN_VOLUME_MULTIPLIER": 5.0,
    "PROACTIVE_SCAN_VOLUME_PERIOD": 24,

    # --- AI Öncesi Filtreleme Ayarları ---
    "PROACTIVE_SCAN_PREFILTER_ENABLED": True,
    "PROACTIVE_SCAN_RSI_LOWER": 38,
    "PROACTIVE_SCAN_RSI_UPPER": 62,
    "PROACTIVE_SCAN_ADX_THRESHOLD": 18,
    
    # Gelişmiş Filtre Ayarları
    "PROACTIVE_SCAN_USE_VOLATILITY_FILTER": True, 
    "PROACTIVE_SCAN_ATR_PERIOD": 14,              
    "PROACTIVE_SCAN_ATR_THRESHOLD_PERCENT": 0.4,  
    "PROACTIVE_SCAN_USE_VOLUME_FILTER": True,     
    "PROACTIVE_SCAN_VOLUME_AVG_PERIOD": 20,       
    "PROACTIVE_SCAN_VOLUME_CONFIRM_MULTIPLIER": 1.2, 
    
    # Harici Keşif Kaynakları Ayarları
    "DISCOVERY_USE_TAAPI_SCANNER": True,       
    "DISCOVERY_USE_COINGECKO_TRENDING": True, 
    
    # --- FİLTRELEME & BİLDİRİM ---
    "PROACTIVE_SCAN_BLACKLIST": ["SHIB", "PEPE", "MEME", "DOGE"],
    "PROACTIVE_SCAN_WHITELIST": ["BTC", "ETH", "SOL"],
    "TELEGRAM_ENABLED": True,

    "INTERACTIVE_SCAN_USE_HOLISTIC_ANALYSIS": False, 
}