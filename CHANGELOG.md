Değişiklik Günlüğü
Bu projede yapılan tüm önemli değişiklikler bu dosyada belgelenmektedir.

[3.3.0] - 2025-06-25 - Tarayıcı Performans Optimizasyonu
Bu sürüm, interaktif fırsat tarayıcısının hem backend mantığını hem de frontend kullanıcı deneyimini önemli ölçüde iyileştirmeye odaklanmıştır.

🚀 Eklendi (Added)

Aşamalı Yükleme Göstergesi: Fırsat Tarayıcı sayfasındaki yükleme animasyonu artık "Piyasa verileri çekiliyor...", "Filtre uygulanıyor..." gibi aşamalı geri bildirimler sunarak kullanıcı deneyimini iyileştirir.

🔄 Değiştirildi (Changed)

Paralel API İstekleri: Fırsat Tarayıcı'nın backend mantığı (core/scanner.py), taranacak her sembol için API isteklerini sıralı yapmak yerine, Python'un asyncio kütüphanesi ile eşzamanlı (paralel) olarak yapacak şekilde tamamen yeniden yazıldı. Bu değişiklik, tarama süresini dramatik bir şekilde kısaltmıştır.

[3.2.1] - 2025-06-24 - Stabilite ve Docker Düzeltmeleri
Bu sürüm, Docker ortamında karşılaşılan kritik başlatma hatalarını ve kütüphane uyumsuzluklarını gidererek, Umbrel ve diğer self-host platformlarında stabil bir çalışma deneyimi sunmaya odaklanmıştır.

✅ Düzeltildi (Fixed)

Docker Başlatma Hatası (ImportError): pandas-ta kütüphanesinin, numpy kütüphanesinin yeni sürümleriyle uyumsuz olmasından kaynaklanan ImportError: cannot import name 'NaN' from 'numpy' hatası, requirements.txt dosyasında numpy versiyonu sabitlenerek (numpy==1.26.4) giderildi.

React Build Hatası (Export Error): ScannerPage.jsx'in ihtiyaç duyduğu AnalysisResultModal bileşeninin DashboardPage.jsx'ten export edilmemesi nedeniyle oluşan build hatası düzeltildi.

PNL Hesaplama Uyumsuzluğu: Kapatılan işlemlerdeki PNL hesaplamasının, borsanın gösterdiği değerle tam uyumlu olması için, anlık fiyat yerine emrin borsada gerçekleştiği ortalama fiyatı (fill_price) kullanan yeni bir mantık entegre edildi.

Pozisyon Kapatma API Hatası (405 Method Not Allowed): "BTC/USDT" gibi / karakteri içeren sembollerin pozisyon kapatma isteğinde API'nin hata vermesi, API rotası {symbol:path} olarak güncellenerek düzeltildi.

API Kota Yönetimi: Proaktif tarayıcı, Google AI API kullanım kotası aşıldığında (ResourceExhausted hatası) taramayı otomatik olarak durduracak ve durumu bildirecek şekilde daha dayanıklı hale getirildi.

[3.0.0] - 2025-06-24 - Web Arayüzü & Docker
Bu sürüm, projeyi komut satırı tabanlı bir uygulamadan, web arayüzü ile yönetilen, kendi kendine barındırılabilen (self-hosted) tam kapsamlı bir platforma dönüştüren en büyük mimari değişikliği içerir.

🚀 Eklendi (Added)

Tam Fonksiyonel Web Arayüzü (React):

Anlık performans metriklerini gösteren interaktif bir dashboard.

Canlı PNL (Kâr/Zarar) grafiği.

Aktif pozisyonları ve tüm işlem geçmişini görüntüleme.

Proaktif piyasa taramasını manuel olarak tetikleme.

Veritabanı Tabanlı Dinamik Ayarlar:

Tüm bot yapılandırması (LEVERAGE, RISK_PER_TRADE_PERCENT, BLACKLIST vb.) artık veritabanında saklanmaktadır.

Ayarlar, web arayüzündeki "Uygulama Ayarları" modalı üzerinden, sunucuyu yeniden başlatmaya gerek kalmadan anlık olarak değiştirilebilir.

Kolay Kurulum (Self-Hosted & Umbrel):

Dockerfile ve docker-compose.yml dosyaları ile proje tamamen konteynerize edildi.

umbrel-app.yml manifestosu ile Umbrel App Store'a özel uygulama olarak tek tıkla kurulabilir hale getirildi.

Modern API Altyapısı (FastAPI):

Tüm bot işlevleri, modern ve hızlı bir FastAPI sunucusu üzerinden RESTful API olarak sunulmaktadır.

🔄 Değiştirildi (Changed)

MİMARİ DEVRİM: Proje, tek bir Python script'inden, birbirinden bağımsız çalışan Backend (API) ve Frontend (UI) servislerine sahip modern bir client-server mimarisine tamamen geçirildi.

Proje Yapısı: Kod tabanı, backend ve frontend olmak üzere iki ana klasöre ayrıldı. Backend içerisinde mantıksal katmanlar (api, core, tools, database) oluşturuldu.

🗑️ Kaldırıldı (Removed)

Eski komut satırı tabanlı menü.

Statik ayar dosyası (config.py).

[1.6.1] - 2025-06-13 - Stabilizasyon ve Hata Düzeltmeleri
✅ Düzeltildi (Fixed)

KRİTİK HATA (AttributeError): Yanlışlıkla silinen ATR_MULTIPLIER_SL parametresi geri eklenerek, yeni pozisyon açarken programın çökmesine neden olan hata giderildi.

🚀 Eklendi (Added)

Kısmi Kâr Alma Stratejisi: Fiyat belirli bir hedefe ulaştığında pozisyonun bir kısmını kapatıp, kalan pozisyonun stop-loss seviyesini giriş fiyatına çeken gelişmiş kâr yönetimi özelliği eklendi.

[1.3.0] - 2025-06-11 - Veritabanı ve Risk Yönetimi
🔄 Değiştirildi (Changed)

MİMARİ DEĞİŞİKLİK (JSON -> SQLite): Tüm pozisyon yönetimi, geçici JSON dosyalarından, kalıcı ve sağlam bir SQLite veritabanına (trades.db) taşındı.

🚀 Eklendi (Added)

Dinamik Pozisyon Büyüklüğü: Bot artık toplam portföyün belirli bir yüzdesini (RISK_PER_TRADE_PERCENT) riske atarak pozisyon büyüklüğünü dinamik olarak hesaplıyor.

İz Süren Zarar Durdur (Trailing Stop-Loss): Kâra geçen pozisyonlarda kârı kilitleme özelliği eklendi.

İşlem Geçmişi: Kapanan tüm işlemler, gelecekteki analizler için PNL bilgisiyle birlikte veritabanına kaydedilmeye başlandı.

[1.0.0] - 2025-06-11 - İlk Sürüm
Projenin başlangıcı: Google Gemini ve LangChain kullanılarak komut satırı üzerinden çalışan ilk versiyon.

Temel teknik analiz ve alım/satım özellikleri.

Proaktif piyasa tarama (En Çok Yükselenler/Düşenler).