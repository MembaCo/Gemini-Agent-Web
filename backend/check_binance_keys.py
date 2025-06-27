# backend/check_binance_keys.py

import os
import ccxt
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

print("--- Binance Bağlantı Testi Başlatılıyor ---")

api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")

if not api_key or not secret_key:
    print("\n!!! HATA: BINANCE_API_KEY veya BINANCE_SECRET_KEY .env dosyasında bulunamadı!")
    print("Lütfen `backend/.env` dosyasını kontrol edin ve değişkenlerin dolu olduğundan emin olun.")
    exit(1)

print("\n[ADIM 1/3] API anahtarları .env dosyasından başarıyla okundu.")

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'options': {'defaultType': 'future'},
    'enableRateLimit': True,
})

print("[ADIM 2/3] CCXT Borsa objesi oluşturuldu.")

try:
    print("[ADIM 3/3] Bakiye bilgisi çekilerek anahtarlar doğrulanıyor. Lütfen bekleyin...")
    balance = exchange.fetch_balance()
    print("\n" + "="*30)
    print("--- BAĞLANTI BAŞARILI! ---")
    print("Binance API anahtarlarınız geçerli ve bağlantı kurulabildi.")
    if 'USDT' in balance['total']:
         print(f"Vadeli Cüzdan Toplam USDT Bakiyeniz: {balance['total']['USDT']:.2f} USDT")
    print("="*30)

except ccxt.AuthenticationError as e:
    print("\n" + "!"*30)
    print("!!! HATA: Kimlik Doğrulama Hatası (AuthenticationError) !!!")
    print("Bu hata, API anahtarınızın (apiKey) veya gizli anahtarınızın (secretKey) geçersiz olduğu anlamına gelir.")
    print("Lütfen anahtarları Binance'ten doğru kopyaladığınızdan ve IP kısıtlaması gibi ayarları doğru yaptığınızdan emin olun.")
    print(f"\nOrijinal Hata Mesajı: {e}")
    print("!"*30)
    exit(1)
except Exception as e:
    print(f"\n!!! HATA: Beklenmedik bir hata oluştu: {e}")
    exit(1)