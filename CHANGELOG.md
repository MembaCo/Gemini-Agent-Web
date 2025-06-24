Değişiklik Günlüğü
Bu projede yapılan tüm önemli değişiklikler bu dosyada belgelenmektedir.

[3.0.0] - 2025-06-24 - Web Arayüzü & Docker
Bu sürüm, projeyi komut satırı tabanlı bir uygulamadan, web arayüzü ile yönetilen, kendi kendine barındırılabilen (self-hosted) tam kapsamlı bir platforma dönüştüren en büyük mimari değişikliği içerir.

🚀 Eklendi (Added)
Tam Fonksiyonel Web Arayüzü (React):

Anlık performans metriklerini gösteren interaktif bir dashboard.

Canlı PNL (Kâr/Zarar) grafiği.

Aktif pozisyonları ve tüm işlem geçmişini görüntüleme.

Proaktif piyasa taramasını manuel olarak tetikleme.

Veritabanı Tabanlı Dinamik Ayarlar:

Tüm bot yapılandırması (LEVERAGE, RISK_PER_TRADE_PERCENT, BLACKLIST vb.) artık config.py yerine veritabanında saklanmaktadır.

Ayarlar, web arayüzündeki "Uygulama Ayarları" modalı üzerinden, sunucuyu yeniden başlatmaya gerek kalmadan anlık olarak değiştirilebilir.

Docker & Umbrel Desteği:

Dockerfile ve docker-compose.yml dosyaları ile proje tamamen konteynerize edildi.

umbrel-app.yml manifestosu ile Umbrel App Store'a özel uygulama olarak tek tıkla kurulabilir hale getirildi.

Modern API Altyapısı (FastAPI):

Tüm bot işlevleri, modern ve hızlı bir FastAPI sunucusu üzerinden RESTful API olarak sunulmaktadır.

🔄 Değiştirildi (Changed)
MİMARİ DEVRİM: Proje, tek bir Python script'inden, birbirinden bağımsız çalışan Backend (API) ve Frontend (UI) servislerine sahip modern bir client-server mimarisine tamamen geçirildi.

Proje Yapısı: Kod tabanı, backend ve frontend olmak üzere iki ana klasöre ayrıldı. Backend içerisinde mantıksal katmanlar (api, core, tools, database) oluşturuldu.

🗑️ Kaldırıldı (Removed)
Eski komut satırı tabanlı menü (main.py içindeki while True döngüsü).

Eski Flask tabanlı basit dashboard (dashboard/ klasörü).

Statik ayar dosyası (config.py).

[2.0.0] - (Dahili Geliştirme Sürümü) - API Geçişi
Bu versiyon, konsol uygulamasından web tabanlı yapıya geçişin ara aşamasını temsil eder.

🚀 Eklendi (Added)
FastAPI Entegrasyonu: Projenin çekirdeğine FastAPI web çatısı eklenerek, bot fonksiyonları API endpoint'leri olarak sunulmaya başlandı.

Çekirdek Modüller: İş mantığı, core (agent, trader, scanner) ve api klasörleri oluşturularak modüler hale getirildi.

[1.6.1] - 2025-06-13 - Stabilizasyon ve Hata Düzeltmeleri
✅ Düzeltildi (Fixed)
KRİTİK HATA (AttributeError): Yanlışlıkla silinen ATR_MULTIPLIER_SL parametresi geri eklenerek, yeni pozisyon açarken programın çökmesine neden olan hata giderildi.

Web Arayüzü (Dashboard): P&L grafiğindeki görsel hatalar ve senkronizasyon mantığındaki istatistiksel tutarsızlıklar düzeltildi.

Sembol Standardizasyonu: Hatalı sembol formatlarını (HMSTRUSDT/USDT) engelleyen daha sağlam bir ayrıştırma mantığı getirildi.

🚀 Eklendi (Added)
Kısmi Kâr Alma Stratejisi: Fiyat belirli bir hedefe ulaştığında pozisyonun bir kısmını kapatıp, kalan pozisyonun stop-loss seviyesini giriş fiyatına çeken gelişmiş kâr yönetimi özelliği eklendi.

[1.3.0] - 2025-06-11 - Veritabanı ve Risk Yönetimi
🔄 Değiştirildi (Changed)
MİMARİ DEĞİŞİKLİK (JSON -> SQLite): Tüm pozisyon yönetimi, geçici JSON dosyalarından, kalıcı ve sağlam bir SQLite veritabanına (trades.db) taşındı. database.py modülü oluşturuldu.

🚀 Eklendi (Added)
Dinamik Pozisyon Büyüklüğü: Bot artık toplam portföyün belirli bir yüzdesini (RISK_PER_TRADE_PERCENT) riske atarak pozisyon büyüklüğünü dinamik olarak hesaplıyor.

İz Süren Zarar Durdur (Trailing Stop-Loss): Kâra geçen pozisyonlarda kârı kilitleme özelliği eklendi.

İşlem Geçmişi: Kapanan tüm işlemler, gelecekteki analizler için PNL bilgisiyle birlikte veritabanına kaydedilmeye başlandı.

[1.0.0] - 2025-06-11 - İlk Sürüm
Projenin başlangıcı: Google Gemini ve LangChain kullanılarak komut satırı üzerinden çalışan ilk versiyon.

Temel teknik analiz ve alım/satım özellikleri.

Proaktif piyasa tarama (En Çok Yükselenler/Düşenler).