Harika bir fikir. README.md dosyası, bir projenin vitrinidir ve potansiyel kullanıcılar veya geliştiriciler için ilk temas noktasıdır. Mevcut dosyanız zaten projenin özelliklerini güzel bir şekilde özetliyor ancak özellikle kurulum, yapılandırma ve kullanım adımlarını detaylandırarak çok daha kullanıcı dostu ve eksiksiz hale getirebiliriz.

Aşağıda, projenizin mevcut yapısını ve dosyalarını (docker-compose.yml, .env gereksinimleri, check_binance_keys.py vb.) dikkate alarak hazırladığım, eksikleri giderilmiş ve yeniden yapılandırılmış README.md dosyasını markdown formatında bulabilirsiniz.

Gemini Trading Agent (Web UI & Self-Hosted)
Gemini Trading Agent, Google'ın güçlü Gemini AI modellerini kullanarak kripto para piyasalarında (Vadeli ve Spot) analiz yapan ve işlem gerçekleştiren, kendi sunucunuzda tam kontrolle çalıştırabileceğiniz gelişmiş bir bottur.

Modern web arayüzü sayesinde tüm operasyonlarınızı kolayca yönetebilir, performansınızı takip edebilir, stratejileri geriye dönük test edebilir ve botun ayarlarını anlık olarak, yeniden başlatmaya gerek kalmadan doğrudan arayüz üzerinden güncelleyebilirsiniz.

✨ Temel Özellikler

Web Tabanlı Kontrol Paneli: React ile geliştirilmiş modern, hızlı ve duyarlı arayüz sayesinde botunuzu her yerden yönetin.

Anlık P&L takibi ve genel performans istatistikleri.

Kümülatif kâr/zararı gösteren interaktif zaman çizelgesi grafiği.

Aktif pozisyonları yönetme, geçmiş işlemleri inceleme ve işlem grafiklerini görüntüleme.

Canlı Olay Paneli: Pozisyon açılışı, kapanışı, tarayıcı aktiviteleri ve sistem uyarıları gibi tüm önemli olayları anlık olarak takip edin.

Akıllı Fırsat Tarayıcı: Piyasayı potansiyel fırsatlar için tarayın ve yapay zeka analizine geçmeden önce temel teknik göstergelerle ön elemeye tabi tutun. Bu sayede sadece en potansiyelli adaylar için AI kullanılır, API maliyetleri düşer ve kota limitlerine takılma riski azalır.

Strateji Backtest Motoru: Farklı sembol, tarih aralığı ve strateji parametreleri ile geçmişe dönük testler yaparak stratejinizin performansını ölçün. Strateji ayarlarınızı ön ayar olarak kaydedip tekrar kullanın.

Dinamik ve Veritabanı Tabanlı Ayarlar: Botun tüm strateji ve risk yönetimi ayarları (Kaldıraç, Risk Yüzdesi, Kara Liste, Tarayıcı Kriterleri vb.) web arayüzü üzerinden anlık olarak değiştirilebilir ve kalıcı olarak veritabanında saklanır.

Yapay Zeka Destekli Analiz: Google Gemini 1.5 Flash/Pro modellerini kullanarak Çoklu Zaman Aralığı (MTA) dahil olmak üzere derinlemesine piyasa analizleri yapın. Yedek model (fallback) sistemi sayesinde bir modelin kotası dolsa bile diğer modellere otomatik geçiş yapılır.

Gelişmiş Risk Yönetimi:

Dinamik Pozisyon Boyutlandırma: Her işlemde sermayenizin belirli bir yüzdesini riske atar.

İz Süren Zarar Durdur (Trailing Stop-Loss): Kârı korumak için stop-loss seviyesini otomatik olarak ayarlar.

Kısmi Kâr Alma: Belirlenen hedeflere ulaşıldığında pozisyonun bir kısmını otomatik olarak kapatır.

Kolay Kurulum (Self-Hosted & Umbrel): Docker teknolojisi sayesinde, tek bir komutla kendi sunucunuza veya Umbrel gibi kişisel sunucu platformlarına kolayca kurun.

Telegram Entegrasyonu: Telegram komutları ile botunuza analiz yaptırın, pozisyonlarınızı kontrol edin ve anlık bildirimler alın.

🛠️ Teknoloji Yığını

Backend: Python, FastAPI, LangChain, CCXT, Pandas-TA, APScheduler, asyncio.

Frontend: React, Vite, Tailwind CSS, Chart.js, Lightweight Charts.

Veritabanı: SQLite.

Dağıtım (Deployment): Docker, Docker Compose.

🚀 Kurulum ve Çalıştırma

Bu uygulama, Docker ile kolayca kurulacak şekilde tasarlanmıştır. Başlamak için bilgisayarınızda Git ve Docker Desktop'ın kurulu olması yeterlidir.

1. Projeyi Klonlayın

Bash

git clone https://github.com/MembaCo/Gemini-Agent-Web.git
cd Gemini-Agent-Web
2. Ortam Değişkenlerini Ayarlayın

Uygulamanın çalışması için gerekli olan API anahtarlarını ve diğer gizli bilgileri içeren bir ortam değişkenleri dosyası oluşturmanız gerekmektedir.

backend/ dizini içinde .env.example adında bir dosya oluşturup .env olarak kopyalayın veya doğrudan backend/.env adında yeni bir dosya oluşturun.

Bu dosyayı aşağıdaki gibi doldurun:

Kod snippet'i

# Binance API Anahtarları (ZORUNLU)
# Vadeli İşlemler (Futures) için okuma ve işlem yapma izni olmalıdır.
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
BINANCE_SECRET_KEY="YOUR_BINANCE_SECRET_KEY"

# Google AI API Anahtarı (ZORUNLU)
# https://aistudio.google.com/app/apikey adresinden alınabilir.
GOOGLE_API_KEY="YOUR_GOOGLE_AI_API_KEY"

# Web Arayüzü Giriş Bilgileri (ZORUNLU)
ADMIN_USERNAME="admin"
# Aşağıdaki komutla kendi güvenli şifrenizi oluşturun:
# python3 backend/hash_password.py 'sizin_guvenli_sifreniz'
ADMIN_PASSWORD_HASH="$2b$12$....YOUR_GENERATED_PASSWORD_HASH_HERE...."

# JWT Token için Gizli Anahtar (ZORUNLU)
# Herhangi bir rastgele karmaşık dize olabilir.
SECRET_KEY="your_super_secret_key_for_jwt_tokens"

# Telegram Bildirimleri (İsteğe Bağlı)
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"

# Testnet Kullanımı (İsteğe Bağlı)
# Gerçek para yerine test ortamını kullanmak için True yapın.
USE_TESTNET=False

# LangChain Tracing (İsteğe Bağlı - Geliştiriciler için)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=""
3. Uygulamayı Çalıştırın

Tüm yapılandırmaları tamamladıktan sonra, projenin ana dizininde aşağıdaki komutu çalıştırarak uygulamayı başlatın:

Bash

docker-compose up --build
Bu komut, gerekli Docker imajlarını oluşturacak ve hem backend (API sunucusu) hem de frontend (web arayüzü) servislerini başlatacaktır.

🖥️ Kullanım

Uygulama başarıyla başladıktan sonra, web tarayıcınızdan http://localhost:8080 adresine gidin.

.env dosyasında belirlediğiniz ADMIN_USERNAME ve şifreniz ile giriş yapın.

Dashboard üzerinden botun genel durumunu izleyebilir, Fırsat Tarayıcı ile yeni analizler yapabilir veya Backtesting motoru ile stratejilerinizi test edebilirsiniz.

Tüm bot ayarlarını, sağ üst köşedeki Ayarlar (⚙️) ikonuna tıklayarak açılan pencereden anlık olarak değiştirebilirsiniz.

📂 Proje Yapısı

Projenin ana dizinleri ve görevleri şunlardır:

/backend: Python ile yazılmış FastAPI sunucusunu ve tüm bot mantığını içerir.

/api: Web arayüzünün iletişim kurduğu API endpoint'lerini barındırır.

/core: Agent, strateji, pozisyon yönetimi gibi ana iş mantığını içerir.

/tools: Borsa bağlantısı, gösterge hesaplama gibi yardımcı araçları içerir.

/database: Veritabanı oluşturma ve yönetme fonksiyonlarını içerir.

/frontend: React ile yazılmış web arayüzü kodlarını içerir.

/data: SQLite veritabanı dosyası (trades.db) gibi kalıcı verilerin saklandığı klasördür.

docker-compose.yml: Backend ve frontend servislerini birlikte çalıştırmak için gerekli yapılandırmayı içerir.

⚠️ Risk Uyarısı

Bu proje, finansal piyasalarda işlem yapmak için kullanılan bir araçtır. Kripto para ticareti, doğası gereği yüksek riskler içerir ve sermayenizin bir kısmını veya tamamını kaybetmenize neden olabilir. Bu yazılım tarafından yapılan analizler veya açılan pozisyonlar hiçbir şekilde yatırım tavsiyesi değildir. Yazılımı kullanırken tüm sorumluluk kullanıcıya aittir. LIVE_TRADING ayarını aktifleştirmeden önce risklerin tamamen farkında olduğunuzdan emin olun.

🤝 Katkıda Bulunma

Projeye katkıda bulunmak isterseniz, lütfen bir "issue" açarak veya "pull request" göndererek iletişime geçin. Her türlü fikir ve geliştirme önerisine açığız!

📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Daha fazla bilgi için LICENSE dosyasına bakın.