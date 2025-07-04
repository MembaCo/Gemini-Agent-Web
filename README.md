# ♊ Gemini Trading Agent (Web UI & Self-Hosted)

**Gemini Trading Agent**, Google'ın güçlü Gemini AI modellerini kullanarak kripto para piyasalarında (Vadeli & Spot) gelişmiş analizler yapan ve işlem gerçekleştiren, tamamen kendi sunucunuzda çalıştırabileceğiniz modern bir bottur.

Kullanıcı dostu ve modern **web arayüzü** sayesinde tüm operasyonlarınızı kolayca yönetebilir, performansınızı anlık takip edebilir, stratejileri geriye dönük test edebilir ve bot ayarlarını hızlıca güncelleyebilirsiniz.

---

## ✨ Temel Özellikler

### 🖥️ Web Tabanlı Kontrol Paneli
- **React** ile geliştirilmiş hızlı ve duyarlı arayüz
- Anlık P&L takibi ve genel performans istatistikleri
- Kümülatif kâr/zararı gösteren **interaktif zaman çizelgesi**
- Aktif pozisyonları yönetme, geçmiş işlemleri inceleme & işlem grafiklerini görüntüleme

### 📢 Canlı Olay Paneli
- Pozisyon açılışı, kapanışı, tarayıcı aktiviteleri ve sistem uyarıları gibi tüm önemli olayları anlık olarak takip edin

### 🤖 Akıllı Fırsat Tarayıcı
- **Gelişmiş Filtreleme:** Temel teknik göstergeler (RSI, ADX), **volatilite (ATR)** ve **hacim** filtreleriyle ön eleme yaparak sadece en potansiyelli adaylarda yapay zeka analizini devreye alır.
- **Maliyet Tasarrufu:** Akıllı filtreleme sayesinde gereksiz API çağrılarını ve maliyetleri önemli ölçüde azaltır.

### 📈 Strateji Backtest Motoru
- Farklı sembol, tarih aralığı & parametrelerle geçmişe dönük test
- Strateji ayarlarını ön ayar olarak kaydedip tekrar kullanılabilir

### ⚙️ Dinamik ve Veritabanı Tabanlı Ayarlar
- Tüm strateji & risk yönetimi ayarlarını (Kaldıraç, Risk Yüzdesi, Kara Liste, **Bailout Stratejisi** vb.) arayüzden anlık güncelleyin.
- Tüm ayarlar kalıcı olarak veritabanında saklanır.

### 🧠 Yapay Zeka Destekli Analiz
- **Google Gemini 1.5 Flash/Pro** ile derinlemesine piyasa analizleri.
- **Dominant Sinyal Analizi:** Çoklu Zaman Aralığı (MTA) analizlerinde, trendi daha güçlü olan zaman dilimini otomatik belirleyerek AI'ı yönlendirir ve daha tutarlı kararlar alınmasını sağlar.
- **Yedek Model Sistemi:** Model kotası dolarsa otomatik diğer modele geçiş.

### 🛡️ Gelişmiş Risk Yönetimi
- **Dinamik Pozisyon Boyutlandırma:** Her işlemde sermayenin belirli bir yüzdesi riske edilir.
- **Akıllı Zarar Azaltma (Bailout Exit):** Zarardaki bir pozisyonun, stop-loss olmadan önce gösterdiği geçici toparlanma anında, **isteğe bağlı yapay zeka onayı** ile kapatılarak kayıpların minimize edilmesini sağlar.
- **İz Süren Zarar Durdur (Trailing Stop-Loss)**
- **Kısmi Kâr Alma:** Hedefe ulaşıldığında pozisyonun bir kısmını otomatik kapatır.

### 🐳 Kolay Kurulum (Self-Hosted & Umbrel)
- **Docker** ile tek komutla kendi sunucunuza veya **Umbrel** gibi platformlara kurulum.

### 💬 Telegram Entegrasyonu
- Telegram komutları ile botu kontrol etme, analiz alma ve anlık bildirimler.

---

## 🖼️ Ekran Görüntüleri

<div align="center">

<img src="./screenshots/gallery-1.png" width="300" alt="Image of a phone showing the App">
<img src="./screenshots/gallery-2.png" width="300" alt="Image of a phone showing the App">
<img src="./screenshots/gallery-3.png" width="300" alt="Image of a phone showing the App">
</div>

---

## 🛠️ Teknoloji Yığını

| Katman      | Teknoloji                                      |
| ----------- | ---------------------------------------------- |
| Backend     | Python, FastAPI, LangChain, CCXT, Pandas-TA, APScheduler, asyncio |
| Frontend    | React, Vite, Tailwind CSS, Chart.js, Lightweight Charts |
| Veritabanı  | SQLite                                        |
| Dağıtım     | Docker, Docker Compose                         |

---

## 🚀 Kurulum ve Çalıştırma

**Başlamak için bilgisayarınızda [Git](https://git-scm.com/) ve [Docker Desktop](https://www.docker.com/products/docker-desktop/) kurulu olmalıdır.**

### 1. Projeyi Klonlayın

```bash
git clone https://github.com/MembaCo/Gemini-Agent-Web.git
cd Gemini-Agent-Web
```

### 2. Ortam Değişkenlerini Ayarlayın

`backend/` dizininde `.env.example` dosyasını kopyalayın veya yeni bir `.env` dosyası oluşturun:

```bash
cp backend/.env.example backend/.env
```

`.env` dosyasını aşağıdaki gibi doldurun:

```env
# ZORUNLU AYARLAR
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
BINANCE_SECRET_KEY="YOUR_BINANCE_SECRET_KEY"
GOOGLE_API_KEY="YOUR_GOOGLE_AI_API_KEY"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD_HASH="$2b$12$....YOUR_GENERATED_PASSWORD_HASH_HERE...."
SECRET_KEY="your_super_secret_key_for_jwt_tokens"

# İSTEĞE BAĞLI AYARLAR
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
USE_TESTNET=False
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=""
```

> Güvenli şifre hash’i oluşturmak için:
> ```bash
> python3 backend/hash_password.py 'sizin_guvenli_sifreniz'
> ```

### 3. Uygulamayı Çalıştırın

```bash
docker-compose up --build
```

Bu komut ile backend (API sunucusu) ve frontend (web arayüzü) başlatılır.

---

## 🖥️ Kullanım

1. Tarayıcınızdan [http://localhost:8080](http://localhost:8080) adresine gidin.
2. `.env` dosyasında belirlediğiniz **ADMIN_USERNAME** ve şifreniz ile giriş yapın.
3. Dashboard üzerinden botu izleyin, analiz yapın veya backtest işlemlerini başlatın.
4. Tüm bot ayarlarını sağ üstteki **Ayarlar (⚙️)** ikonundan anlık olarak değiştirebilirsiniz.

---

## 📂 Proje Yapısı

```
Gemini-Agent-Web/
├── backend/        # Python FastAPI sunucusu ve bot mantığı
│   ├── api/        # API endpoint'leri
│   ├── core/       # Agent, strateji, pozisyon yönetimi
│   ├── tools/      # Borsa bağlantısı, gösterge hesaplama vb.
│   ├── database/   # Veritabanı fonksiyonları
│   └── .env        # Ortam değişkenleri dosyası
├── frontend/       # React tabanlı web arayüzü
├── data/           # Kalıcı veriler (ör: trades.db SQLite)
├── docker-compose.yml
└── README.md
```

---

## ⚠️ Risk Uyarısı

> **Uyarı:** Bu yazılım finansal piyasalarda işlem yapmak için geliştirilmiştir. Kripto para ticareti yüksek risk içerir ve sermayenizin bir kısmını veya tamamını kaybetmenize neden olabilir. Yazılım tarafından yapılan analizler veya işlemler yatırım tavsiyesi değildir. Tüm sorumluluk kullanıcıya aittir. Canlı işlem açmadan önce riskleri anladığınızdan emin olun.

---

## 🤝 Katkıda Bulunma

Katkı yapmak ister misiniz?  
Bir [issue](https://github.com/MembaCo/Gemini-Agent-Web/issues) açabilir veya pull request gönderebilirsiniz. Her türlü öneri ve geliştirmeye açığız!

---

## 📄 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---