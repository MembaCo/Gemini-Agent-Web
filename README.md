# Gemini Trading Agent v1.8.0

![Versiyon](https://img.shields.io/badge/versiyon-1.8.0-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-blueviolet) ![Status](https://img.shields.io/badge/status-stabil-green)

Google'ın güçlü Gemini yapay zeka modellerini ve LangChain framework'ünü kullanarak kripto para piyasalarında işlem yapan, çok yönlü bir trading botu. Bu bot; teknik, duyarlılık ve temel analiz yeteneklerini birleştirerek piyasaları bütünsel bir yaklaşımla değerlendirir. Gelişmiş risk yönetimi ve kalıcı veritabanı mimarisine sahiptir.

## Temel Özellikler

- **Çok Yönlü Yapay Zeka Analizi:** Google Gemini modellerini kullanarak piyasaları üç farklı boyutta analiz eder:
  - **Teknik Analiz:** Fiyat grafikleri üzerinden Çoklu Zaman Aralığı (MTA) analizi yaparak trendleri ve giriş noktalarını belirler.
  - **Duyarlılık Analizi:** Fonlama oranları (Funding Rates) ve emir defteri derinliği (Order Book Depth) gibi verilerle anlık piyasa iştahını ölçer.
  - **Temel Analiz (Haber Duyarlılığı):** CryptoPanic API'si üzerinden en son haberleri okur. Piyasayı olumsuz etkileyebilecek (FUD, hack vb.) haberler durumunda, riskli işlemlerden kaçınır.
- **Gelişmiş Risk Yönetimi:**
    - **Dinamik Pozisyon Boyutlandırma:** Sermayenin belirli bir yüzdesini riske atarak işlem büyüklüğünü dinamik olarak hesaplar.
    - **ATR Tabanlı SL/TP:** Piyasa volatilitesine göre Stop-Loss ve Take-Profit seviyelerini dinamik olarak belirler.
    - **İz Süren Zarar Durdur (Trailing Stop-Loss):** Kâra geçen pozisyonlarda kârı kilitlemek için stop-loss seviyesini otomatik olarak ayarlar.
    - **Kısmi Kâr Alma (Partial Take-Profit):** 1R hedefine ulaşıldığında pozisyonun bir kısmını kapatarak kârı realize eder ve riski sıfırlar.
- **İnteraktif Telegram Kontrolü:**
    - **Detaylı Durum Raporu:** `/status` komutu ile borsadaki ve bot tarafından yönetilen tüm pozisyonların anlık PNL durumunu görme.
    - **Uzaktan Analiz ve Tarama:** `/analiz` ve `/tara` komutları ile botun analiz ve fırsat avcısı modüllerini tetikleme.
    - **Pozisyon Yönetimi:** `/pozisyonlar` komutu ile aktif pozisyonları listeleme, yeniden analiz etme ve **doğrudan Telegram üzerinden pozisyon kapatma**.
- **Kalıcı ve Sağlam Veritabanı Mimarisi:**
    - **SQLite Entegrasyonu:** Anlık pozisyonları ve tüm işlem geçmişini, yeniden başlatmalarda kaybolmayan sağlam bir SQLite veritabanında saklar.
    - **İşlem Geçmişi:** Kapanan her işlemin PNL ve kapanış durumu gibi detaylarını gelecekteki analizler için kaydeder.
- **İki Farklı Tarama Modu:**
    - **Manuel Analiz:** İstediğiniz bir kripto parayı anlık olarak analiz edip işlem açma.
    - **Proaktif Tarama (Fırsat Avcısı):** Binance'in "En Çok Yükselenler/Düşenler" listesini ve beyaz listenizi periyodik olarak tarayarak otomatik işlem fırsatları bulma.
- **Esnek Konfigürasyon:** Tüm strateji, risk ve API ayarlarının `config.py` üzerinden kolayca yönetilmesi.
- **Canlı ve Simülasyon Modu:** Gerçek parayla işlem yapmadan önce stratejilerinizi test edebilmeniz için güvenli simülasyon modu.
- **Web Arayüzü:** Botun performansını ve işlem geçmişini görselleştiren basit bir web panosu.

## Kullanılan Teknolojiler

- **Python 3.10+**
- **LangChain & LangChain Google GenAI:** Yapay zeka ajanı oluşturma ve LLM entegrasyonu.
- **Google Gemini API:** Analiz ve karar verme süreçleri için.
- **CCXT:** Binance ve diğer borsalarla standartlaştırılmış iletişim için.
- **Pandas & Pandas-TA:** Finansal verileri işlemek ve teknik analiz göstergelerini hesaplamak için.
- **python-telegram-bot v22+:** Asenkron Telegram botu işlevselliği için.
- **SQLite3:** Pozisyon ve işlem geçmişi verilerini saklamak için.
- **Flask:** Web arayüzü için.
- **Dotenv:** API anahtarları gibi hassas bilgileri güvenli bir şekilde yönetmek için.

## Kurulum

1.  **Projeyi Klonlayın:**
    ```bash
    git clone [https://github.com/membaco/gemini-trading-agent.git](https://github.com/membaco/gemini-trading-agent.git)
    cd gemini-trading-agent
    ```

2.  **Gerekli Kütüphaneleri Yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **API Anahtarlarını Ayarlayın:**
    Proje dizinindeki `.env.example` dosyasını kopyalayarak `.env` adında yeni bir dosya oluşturun ve kendi API anahtarlarınızla doldurun.
    ```dotenv
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
    BINANCE_SECRET_KEY="YOUR_BINANCE_SECRET_KEY"
    CRYPTOPANIC_API_KEY="YOUR_CRYPTOPANIC_API_KEY"
    
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
    # ... diğer ayarlar
    ```

4.  **Botu Yapılandırın:**
    `config.py` dosyasını açarak strateji ve risk yönetimi ayarlarınızı (kaldıraç, risk yüzdesi, MTA, Trailing SL vb.) kendinize göre düzenleyin.
    **ÖNEMLİ:** Bota alışana kadar `LIVE_TRADING` ayarını mutlaka `False` olarak bırakın!

## Kullanım

Tüm ayarları tamamladıktan sonra botu aşağıdaki komutla başlatabilirsiniz:

```bash
python main.py
