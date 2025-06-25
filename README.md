# Gemini Trading Agent (Web UI & Self-Hosted)

Gemini Trading Agent, Google'ın güçlü Gemini AI modellerini kullanarak kripto para piyasalarında (Vadeli ve Spot) analiz yapan ve işlem gerçekleştiren, kendi sunucunuzda tam kontrolle çalıştırabileceğiniz gelişmiş bir bottur.

Modern web arayüzü sayesinde tüm operasyonlarınızı kolayca yönetebilir, performansınızı takip edebilir, stratejileri geriye dönük test edebilir ve botun ayarlarını anlık olarak, yeniden başlatmaya gerek kalmadan doğrudan arayüz üzerinden güncelleyebilirsiniz.

✨ **Temel Özellikler**

* **Web Tabanlı Kontrol Paneli**: React ile geliştirilmiş modern, hızlı ve duyarlı arayüz sayesinde botunuzu her yerden yönetin.
    * Anlık P&L takibi ve genel performans istatistikleri.
    * Kümülatif kâr/zararı gösteren interaktif zaman çizelgesi grafiği.
    * Aktif pozisyonları yönetme, geçmiş işlemleri inceleme ve işlem grafiklerini görüntüleme.
* **İnteraktif Fırsat Tarayıcı**: Piyasayı potansiyel fırsatlar için tarayın ve yalnızca seçtiğiniz adayları tek tıkla yapay zeka ile analiz edin. Tarama motoru, performansı en üst düzeye çıkarmak için API isteklerini paralel olarak çalıştırır.
* **Strateji Backtest Motoru**: Farklı sembol, tarih aralığı ve strateji parametreleri ile geçmişe dönük testler yaparak stratejinizin performansını ölçün. Strateji ayarlarınızı ön ayar olarak kaydedip tekrar kullanın.
* **Dinamik ve Veritabanı Tabanlı Ayarlar**: Botun tüm strateji ve risk yönetimi ayarları (Kaldıraç, Risk Yüzdesi, Kara Liste vb.) web arayüzü üzerinden anlık olarak değiştirilebilir ve kalıcı olarak veritabanında saklanır.
* **Yapay Zeka Destekli Analiz**: Google Gemini 1.5 Flash/Pro modellerini kullanarak Çoklu Zaman Aralığı (MTA) dahil olmak üzere derinlemesine piyasa analizleri yapın.
* **Gelişmiş Risk Yönetimi**:
    * **Dinamik Pozisyon Boyutlandırma**: Her işlemde sermayenizin belirli bir yüzdesini riske atar.
    * **İz Süren Zarar Durdur (Trailing Stop-Loss)**: Kârı korumak için stop-loss seviyesini otomatik olarak ayarlar.
    * **Kısmi Kâr Alma**: Belirlenen hedeflere ulaşıldığında pozisyonun bir kısmını otomatik olarak kapatır.
* **Kolay Kurulum (Self-Hosted & Umbrel)**: Docker teknolojisi sayesinde, tek bir komutla kendi sunucunuza veya Umbrel gibi kişisel sunucu platformlarına kolayca kurun.
* **Kalıcı Veritabanı Mimarisi**: Tüm aktif pozisyonlar, ayarlar ve işlem geçmişi, yeniden başlatmalarda kaybolmayan sağlam bir SQLite veritabanında saklanır.
* **Telegram Entegrasyonu**: Telegram komutları ile botunuza analiz yaptırın, pozisyonlarınızı kontrol edin ve anlık bildirimler alın.

---

🛠️ **Teknoloji Yığını**

* **Backend**: Python, FastAPI, LangChain, CCXT, Pandas-TA, APScheduler, asyncio.
* **Frontend**: React, Vite, Tailwind CSS, Chart.js, Lightweight Charts.
* **Veritabanı**: SQLite.
* **Dağıtım (Deployment)**: Docker, Docker Compose.

---

🚀 **Kurulum ve Çalıştırma**

Bu uygulama, Docker ile kolayca kurulacak şekilde tasarlanmıştır. Başlamak için bilgisayarınızda Git ve Docker Desktop'ın kurulu olması yeterlidir.

**1. Projeyi Klonlayın**
```bash
git clone [https://github.com/MembaCo/Gemini-Agent-Web.git](https://github.com/MembaCo/Gemini-Agent-Web.git)
cd Gemini-Agent-Web

2. API Anahtarlarını ve Yönetici Bilgilerini Yapılandırın

Projenin çalışması için gerekli olan bilgileri tanımlamanız gerekmektedir. backend klasörünün içindeki .env.example dosyasını kopyalayarak aynı klasör içinde .env adında yeni bir dosya oluşturun.

Oluşturduğunuz .env dosyasını bir metin editörü ile açın ve tüm alanları kendi bilgilerinizle doldurun.

# backend/.env

# --- GÜVENLİK AYARLARI (Zorunlu) ---
# Web arayüzüne giriş için kullanılacak kullanıcı adı ve şifre
# ŞİFREYİ MUTLAKA GÜÇLÜ BİR ŞEYLE DEĞİŞTİRİN!
ADMIN_USERNAME="admin"
# Aşağıdaki hash "admin" şifresine aittir. Güçlü bir şifre ile değiştirin.
# Yeni hash oluşturmak için bir bcrypt hash oluşturucu kullanın (ör: [https://bcrypt-generator.com/](https://bcrypt-generator.com/))
ADMIN_PASSWORD_HASH="$2a$12$4oKaA4GZIsOblq6F4Rft...SIZIN_OLUŞTURDUĞUNUZ_HASH"
# JWT token için gizli anahtar (karmaşık ve tahmin edilemez bir şey yazın)
SECRET_KEY="your_super_secret_key_for_jwt_tokens_change_this_please"

# --- GOOGLE AI API (Zorunlu) ---
# Google AI Studio'dan aldığınız Gemini API anahtarınız
GOOGLE_API_KEY="AIzaSy...SİZİN_GERÇEK_API_ANAHTARINIZ"

# --- BINANCE API (Zorunlu) ---
# Binance'ten oluşturduğunuz API anahtarlarınız
BINANCE_API_KEY="SİZİN_BINANCE_API_ANAHTARINIZ"
BINANCE_SECRET_KEY="SİZİN_BINANCE_GİZLİ_ANAHTARINIZ"

# --- TELEGRAM BİLDİRİMLERİ (İsteğe Bağlı) ---
# Telegram'da BotFather ile oluşturduğunuz botunuzun token'ı
TELEGRAM_BOT_TOKEN=""
# Bildirimlerin gönderileceği sohbetin (kişi veya grup) ID'si
TELEGRAM_CHAT_ID=""

# --- DİĞER AYARLAR ---
# Gerçek parayla işlem için "False" yapın
USE_TESTNET="True"
# Langchain loglaması (sorun giderme için "true" yapabilirsiniz)
LANGCHAIN_TRACING_V2="false"

3. Uygulamayı Başlatın

Tüm yapılandırmayı tamamladıktan sonra, projenin ana dizininde bir terminal açın ve tek bir komutla tüm sistemi başlatın:

docker-compose up --build -d
```-d` parametresi, uygulamanın arka planda (detached mode) çalışmasını sağlar.

**4. Arayüze Erişin**

Kurulum tamamlandığında, web tarayıcınızdan aşağıdaki adrese giderek Gemini Trading Agent'ınızın kontrol paneline ulaşabilirsiniz:

**http://localhost:8080**

Giriş ekranında, `.env` dosyasında belirlediğiniz `ADMIN_USERNAME` ve şifrenizi kullanın.

---
### ☂️ Umbrel OS Üzerine Kurulum

1.  Umbrel arayüzünüzden **App Store**'a gidin.
2.  Sağ üst köşedeki **"Install Custom App"** (Özel Uygulama Yükle) butonuna tıklayın.
3.  Açılan pencereye projenizin GitHub linkini yapıştırın:
    `https://github.com/MembaCo/Gemini-Agent-Web.git`
4.  **"Install"** butonuna tıklayın. Umbrel, `umbrel-app.yml` dosyasını okuyacak, size kurulum sırasında API anahtarlarınızı ve yönetici bilgilerinizi soracak, Docker imajını oluşturacak ve uygulamayı sizin için başlatacaktır.
5.  Yükleme tamamlandığında, Umbrel ana ekranınızda "Gemini Trading Agent" ikonunu göreceksiniz. Tıkladığınızda, doğrudan web arayüzüne yönlendirileceksiniz.

---

**@author:** Memba Co.
