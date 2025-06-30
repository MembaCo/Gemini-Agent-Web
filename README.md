# Gemini Trading Agent (Web UI & Self-Hosted)

Gemini Trading Agent, Google'ın güçlü Gemini AI modellerini kullanarak kripto para piyasalarında (Vadeli ve Spot) analiz yapan ve işlem gerçekleştiren, kendi sunucunuzda tam kontrolle çalıştırabileceğiniz gelişmiş bir bottur.

Modern web arayüzü sayesinde tüm operasyonlarınızı kolayca yönetebilir, performansınızı takip edebilir, stratejileri geriye dönük test edebilir ve botun ayarlarını anlık olarak, yeniden başlatmaya gerek kalmadan doğrudan arayüz üzerinden güncelleyebilirsiniz.

✨ **Temel Özellikler**

* **Web Tabanlı Kontrol Paneli**: React ile geliştirilmiş modern, hızlı ve duyarlı arayüz sayesinde botunuzu her yerden yönetin.
    * Anlık P&L takibi ve genel performans istatistikleri.
    * Kümülatif kâr/zararı gösteren interaktif zaman çizelgesi grafiği.
    * Aktif pozisyonları yönetme, geçmiş işlemleri inceleme ve işlem grafiklerini görüntüleme.
    * **Canlı Olay Paneli**: Pozisyon açılışı, kapanışı, tarayıcı aktiviteleri ve sistem uyarıları gibi tüm önemli olayları anlık olarak takip edin.
* **Akıllı Fırsat Tarayıcı**: Piyasayı potansiyel fırsatlar için tarayın ve yapay zeka analizine geçmeden önce temel teknik göstergelerle **ön elemeye** tabi tutun. Bu sayede sadece en potansiyelli adaylar için AI kullanılır, API maliyetleri düşer ve kota limitlerine takılma riski azalır.
* **Strateji Backtest Motoru**: Farklı sembol, tarih aralığı ve strateji parametreleri ile geçmişe dönük testler yaparak stratejinizin performansını ölçün. Strateji ayarlarınızı ön ayar olarak kaydedip tekrar kullanın.
* **Dinamik ve Veritabanı Tabanlı Ayarlar**: Botun tüm strateji ve risk yönetimi ayarları (Kaldıraç, Risk Yüzdesi, Kara Liste, Tarayıcı Kriterleri vb.) web arayüzü üzerinden anlık olarak değiştirilebilir ve kalıcı olarak veritabanında saklanır.
* **Yapay Zeka Destekli Analiz**: Google Gemini 1.5 Flash/Pro modellerini kullanarak Çoklu Zaman Aralığı (MTA) dahil olmak üzere derinlemesine piyasa analizleri yapın. Yedek model (fallback) sistemi sayesinde bir modelin kotası dolsa bile diğer modellere otomatik geçiş yapılır.
* **Gelişmiş Risk Yönetimi**:
    * **Dinamik Pozisyon Boyutlandırma**: Her işlemde sermayenizin belirli bir yüzdesini riske atar.
    * **İz Süren Zarar Durdur (Trailing Stop-Loss)**: Kârı korumak için stop-loss seviyesini otomatik olarak ayarlar.
    * **Kısmi Kâr Alma**: Belirlenen hedeflere ulaşıldığında pozisyonun bir kısmını otomatik olarak kapatır.
* **Kolay Kurulum (Self-Hosted & Umbrel)**: Docker teknolojisi sayesinde, tek bir komutla kendi sunucunuza veya Umbrel gibi kişisel sunucu platformlarına kolayca kurun.
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