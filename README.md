Gemini Trading Agent (Web UI & Self-Hosted)
Gemini Trading Agent, Google'ın güçlü Gemini AI modellerini kullanarak kripto para piyasalarında (Vadeli ve Spot) analiz yapan ve işlem gerçekleştiren, kendi sunucunuzda tam kontrolle çalıştırabileceğiniz gelişmiş bir bottur.

Modern web arayüzü sayesinde tüm operasyonlarınızı kolayca yönetebilir, performansınızı takip edebilir ve botun stratejisini anlık olarak, yeniden başlatmaya gerek kalmadan doğrudan veritabanı üzerinden güncelleyebilirsiniz.

✨ Temel Özellikler
Web Tabanlı Kontrol Paneli: React ile geliştirilmiş modern, hızlı ve duyarlı arayüz sayesinde botunuzu her yerden yönetin.

Dinamik ve Veritabanı Tabanlı Ayarlar: Botun tüm strateji ve risk yönetimi ayarları (LEVERAGE, RISK_PER_TRADE_PERCENT, BLACKLIST vb.) artık web arayüzündeki "Uygulama Ayarları" modalı üzerinden, sunucuyu yeniden başlatmaya gerek kalmadan anlık olarak değiştirilebilir ve kalıcı olarak veritabanında saklanır.

Kolay Kurulum (Self-Hosted & Umbrel): Docker teknolojisi sayesinde, tek bir komutla kendi sunucunuza veya Umbrel gibi kişisel sunucu platformlarına kolayca kurun.

Yapay Zeka Destekli Analiz: Google Gemini modellerini kullanarak Çoklu Zaman Aralığı (MTA) dahil olmak üzere derinlemesine piyasa analizleri yapın.

Gelişmiş Risk Yönetimi:

Dinamik Pozisyon Boyutlandırma: Her işlemde sermayenizin belirli bir yüzdesini riske atar.

İz Süren Zarar Durdur (Trailing Stop-Loss): Kârı korumak için stop-loss seviyesini otomatik olarak ayarlar.

Kısmi Kâr Alma: Belirlenen hedeflere ulaşıldığında pozisyonun bir kısmını otomatik olarak kapatır.

Proaktif Fırsat Avcısı: Piyasayı sizin için sürekli tarar, potansiyel alım/satım fırsatlarını tespit eder ve size bildirir veya otomatik olarak işlem açar.

Kalıcı Veritabanı Mimarisi: Tüm aktif pozisyonlar, ayarlar ve işlem geçmişi, yeniden başlatmalarda kaybolmayan sağlam bir SQLite veritabanında saklanır.

Telegram Entegrasyonu: Telegram komutları ile botunuza analiz yaptırın, pozisyonlarınızı kontrol edin ve anlık bildirimler alın.

🛠️ Teknoloji Yığını
Backend: Python, FastAPI, LangChain, CCXT, Pandas-TA

Frontend: React, Vite, Tailwind CSS, Chart.js

Veritabanı: SQLite

Dağıtım (Deployment): Docker, Docker Compose

🚀 Kurulum ve Çalıştırma
Bu uygulama, Docker ile kolayca kurulacak şekilde tasarlanmıştır. Başlamak için bilgisayarınızda Git ve Docker Desktop'ın kurulu olması yeterlidir.

1. Projeyi Klonlayın
git clone https://github.com/MembaCo/Gemini-Agent-Web.git
cd Gemini-Agent-Web

2. API Anahtarlarını Yapılandırın (En Önemli Adım)
Projenin çalışması için gerekli olan API anahtarlarını tanımlamanız gerekmektedir.

backend klasörünün içindeki .env.example dosyasını kopyalayarak aynı klasör içinde .env adında yeni bir dosya oluşturun.

Oluşturduğunuz .env dosyasını bir metin editörü ile açın ve kendi API anahtarlarınızla doldurun.

# backend/.env

# Google Gemini API Anahtarı (Zorunlu)
GOOGLE_API_KEY="AIzaSy...SİZİN_GERÇEK_API_ANAHTARINIZ"

# Binance API Anahtarları (Zorunlu)
BINANCE_API_KEY="SİZİN_BİNANCE_API_ANAHTARINIZ"
BINANCE_SECRET_KEY="SİZİN_BİNANCE_GİZLİ_ANAHTARINIZ"

# Telegram Bildirim Ayarları (İsteğe Bağlı)
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""

# Diğer Ayarlar
USE_TESTNET="True" # Gerçek parayla işlem için "False" yapın
AGENT_VERBOSE="True"

3. Uygulamayı Başlatın
Tüm yapılandırmayı tamamladıktan sonra, projenin ana dizininde bir terminal açın ve tek bir komutla tüm sistemi başlatın:

docker-compose up --build -d
```-d` parametresi, uygulamanın arka planda (detached mode) çalışmasını sağlar.

#### 4. Arayüze Erişin

Kurulum tamamlandığında, web tarayıcınızdan aşağıdaki adrese giderek Gemini Trading Agent'ınızın kontrol paneline ulaşabilirsiniz:

**http://localhost:8080**

### ☂️ Umbrel OS Üzerine Kurulum

1.  Umbrel arayüzünüzden **App Store**'a gidin.
2.  Sağ üst köşedeki **"Install Custom App"** (Özel Uygulama Yükle) butonuna tıklayın.
3.  Açılan pencereye projenizin GitHub linkini yapıştırın:
    `https://github.com/MembaCo/Gemini-Agent-Web.git`
4.  **"Install"** butonuna tıklayın. Umbrel, `umbrel-app.yml` dosyasını okuyacak, size API anahtarlarınızı soracak, Docker imajını oluşturacak ve uygulamayı sizin için başlatacaktır.
5.  Yükleme tamamlandığında, Umbrel ana ekranınızda "Gemini Trading Agent" ikonunu göreceksiniz. Tıkladığınızda, doğrudan web arayüzüne yönlendirileceksiniz.

---

**@author:** Memba Co.