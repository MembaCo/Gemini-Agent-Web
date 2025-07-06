Bu projede yapılan tüm önemli değişiklikler bu dosyada belgelenmektedir.

---
### [4.4.2] - 2025-07-06 - Kök Neden Analizi ve Zamanlama Düzeltmeleri

Bu sürüm, önceki versiyonlarda tespit edilen "Hayalet Pozisyon" ve senkronizasyon hatalarının altında yatan iki ana nedeni ortadan kaldırarak sisteme tam kararlılık getirmeyi hedefler.

✅ **Düzeltildi (Fixed)**
- **KRİTİK: Zaman Damgası (`recvWindow`) Hatası Giderildi:** Sunucu saati ile Binance sunucuları arasındaki olası zaman farkından kaynaklanan ve API isteklerinin reddedilmesine yol açan `-1021: Timestamp for this request is outside of the recvWindow` hatası, `ccxt`'nin zaman senkronizasyonu (`adjustForTime`) özelliği etkinleştirilerek tamamen giderildi. Bu, senkronizasyon hatalarının birincil nedenini ortadan kaldırır.
- **KRİTİK: Bağlantı Havuzu (Connection Pool) Hatası Giderildi:** Uygulamanın, özellikle yoğun anlarda, API'ye çok sayıda istek gönderdiğinde aldığı `Connection pool is full` uyarısı, bağlantı havuzu limiti artırılarak çözüldü. Bu, isteklerin başarısız olma olasılığını azaltır ve genel sistem performansını artırır.

---
### [4.4.1] - 2025-07-05 - Kritik Senkronizasyon ve Stabilite Düzeltmeleri

Bu sürüm, botun en kritik hatalarından biri olan "Hayalet Pozisyon" sorununu çözmeye ve sistemin genel çalışma kararlılığını artırmaya odaklanmıştır.

✅ **Düzeltildi (Fixed)**
- **KRİTİK: "Hayalet Pozisyon" Senkronizasyon Hatası:** Botun, anlık ağ sorunları nedeniyle borsadaki gerçek pozisyonları "hayalet" olarak algılayıp veritabanından silmesine neden olan temel senkronizasyon mantığı hatası giderildi. Pozisyon senkronizasyon fonksiyonu (`sync_positions_with_exchange`), borsadan veri almayı birkaç kez deneyen daha dayanıklı bir yapıya kavuşturuldu. Bu düzeltme, "Insufficient Funds" gibi zincirleme hataların ana nedenini ortadan kaldırır.
- **Daha Anlaşılır Hata Loglaması:** Senkronizasyon sorunları yaşandığında, loglar ve Telegram bildirimleri daha kritik ve bilgilendirici olacak şekilde güncellendi.

---
### [4.4.0] - 2025-07-04 - Gelişmiş Risk Yönetimi ve Yapay Zeka Kararlılığı

Bu sürüm, botun risk yönetimi kabiliyetlerini kökten değiştiren yeni özellikler eklerken, bir dizi kritik çalışma zamanı hatasını gidererek sistemi tamamen kararlı hale getirmeye odaklanmıştır.

🚀 **Eklendi (Added)**
- **Akıllı Zarar Azaltma (Bailout Exit):** Zarardaki pozisyonların, tam stop-loss olmadan önce gösterdiği geçici toparlanma anlarında, zararı minimize etmek amacıyla kapatılmasını sağlayan yeni bir strateji eklendi.
- **Yapay Zeka Onaylı Çıkış Kararları:** "Bailout Exit" stratejisi, isteğe bağlı olarak yapay zeka onayına sunulabilir hale getirildi. Artık bot, bir pozisyonu erken kapatmadan önce AI'a "Bu toparlanma gerçek mi, yoksa tuzak mı?" diye danışarak daha akıllı kararlar verebiliyor.
- **Dominant Sinyal Analizi:** Çoklu Zaman Aralığı (MTA) analizlerinde, hangi zaman diliminin trendinin daha güçlü olduğunu (ADX'e göre) belirleyip bu bilgiyi AI'a sunan "Dominant Sinyal" mantığı eklendi. Bu, AI'ın daha tutarlı ve kararlı tavsiyeler vermesini sağlar.
- **Detaylı Strateji Loglaması:** `position_manager` ve `scanner` modüllerindeki loglama, hangi adayın neden filtrelendiğini, bailout stratejisinin ne zaman devreye girdiğini ve AI'ın karar gerekçelerini kaydedecek şekilde zenginleştirildi.

✅ **Düzeltildi (Fixed)**
- **KRİTİK: Pozisyon Yeniden Analiz Mantığı:** "Yeniden Analiz Et" özelliğinin, yapay zekaya boş veri göndererek anlamsız yanıtlar almasına neden olan temel mantık hatası giderildi. Artık bu özellik, anlık fiyat ve güncel teknik göstergeleri toplayarak AI'a tam içerik sunmaktadır.
- **Uygulama Başlatma Hataları:** Farklı modüller (`position_manager`, `trader`, `scanner`, `telegram_bot`) arasındaki hatalı `import` çağrılarından kaynaklanan ve uygulamanın başlamasını engelleyen bir dizi `ImportError`, `NameError` ve `TypeError` hatası tamamen giderildi.
- **Önbellek (Cache) Sistemi Hatası:** Dinamik TTL (Time-To-Live) özelliğinin eklenmesi sırasında `cache_manager` modülünde oluşan ve `TypeError` hatasına yol açan uyumsuzluk düzeltildi.

🔄 **Değiştirildi (Changed)**
- **Merkezi Fiyat Önbellekleme (Caching):** Uygulama genelindeki tüm anlık fiyat sorguları (`get_price_with_cache`), API çağrılarını önemli ölçüde azaltan ve sistem performansını artıran merkezi ve esnek bir önbellek mekanizması kullanacak şekilde yeniden yapılandırıldı.

---

### [4.3.0] - 2025-06-30 - Arayüz ve Kullanıcı Deneyimi İyileştirmeleri

Bu sürüm, kullanıcı deneyimini doğrudan etkileyen ve botun kontrolünü kolaylaştıran önemli arayüz geliştirmeleri içerir.

🚀 **Eklendi (Added)**
- **Proaktif Tarama Onay Penceresi:** Proaktif Tarama sonucunda bulunan ve `auto-confirm` ayarı kapalı olan fırsatlar artık arayüzde bir onay penceresinde listelenerek kullanıcıya sunuluyor. Kullanıcılar bu pencereden istedikleri fırsatları tek tıkla işleme dönüştürebilir.
- **Kapsamlı Ayarlar Menüsü:** Proaktif Tarayıcı'nın ön filtreleme, zaman aralığı, kara/beyaz liste gibi tüm ayarları dahil olmak üzere, arka uçtaki bütün yapılandırma seçenekleri artık web arayüzündeki "Uygulama Ayarları" penceresinden yönetilebilir hale getirildi.

🔄 **Değiştirildi (Changed)**
- **Detaylı Tarama Geri Bildirimi:** Dashboard'daki "Taramayı Başlat" butonu, işlem bittiğinde artık "Tarama tamamlandı" demek yerine, kaç adayın tarandığı, kaçının ön filtreden geçtiği ve kaç fırsat bulunduğu gibi özet bilgileri içeren daha detaylı bir bildirim gösteriyor.

---

### [4.2.0] - 2025-06-30 - Tarayıcı Optimizasyonu ve Gelişmiş Loglama

Bu sürüm, API kullanımını ve maliyetleri düşürmeye yönelik akıllı optimizasyonlar ve sistemin ne yaptığını daha şeffaf hale getiren loglama mekanizmaları üzerine odaklanmıştır.

🚀 **Eklendi (Added)**
- **Canlı Olay (Event) Loglaması:** Pozisyon açma/kapama, tarayıcı başlangıç/bitiş, hata durumları ve senkronizasyon gibi tüm kritik sistem olayları artık "Canlı Sistem Olayları" panelinde gösterilmek üzere veritabanına kaydediliyor.
- **Akıllı Ön Filtreleme:** Proaktif Tarayıcı, artık tüm adayları AI'a göndermeden önce RSI ve ADX gibi temel teknik göstergelere göre bir ön eleme yaparak API kullanımını ve maliyetleri önemli ölçüde azaltıyor. Yapay zeka sadece "umut vadeden" adaylar için kullanılıyor.

---

### [4.1.0] - 2025-06-30 - Performans ve Stabilite İyileştirmeleri

Bu sürüm, uygulamanın daha akıcı ve hatasız çalışmasını sağlamak için arka plandaki performans sorunlarını ve çeşitli kütüphane uyarılarını gidermeye odaklanmıştır.

✅ **Düzeltildi (Fixed)**
- **Zamanlayıcı (Scheduler) Gecikme Uyarısı:** Proaktif tarama gibi ağır işlemlerin ana olay döngüsünü kilitlemesi engellenerek `APScheduler`'ın görevleri her zaman zamanında çalıştırması sağlandı. Bu, uygulamanın genel performansını ve tepkiselliğini artırdı.
- **`LangChainDeprecationWarning`:** `langchain` kütüphanesindeki eski fonksiyon çağrıları, modern `.invoke()` metodu ile değiştirilerek gelecekteki uyumluluk sorunları giderildi.
- **`ccxt` `fetchOpenOrders` Hatası:** Yetim emir kontrolü (`check_for_orphaned_orders`) fonksiyonunun `ccxt` kütüphanesinde bir hataya neden olması, borsa bağlantısı ayarları güncellenerek giderildi.

---

### [4.0.0] - 2025-06-30 - Kritik Hata Giderme ve Backtest Motoru Revizyonu

Bu sürüm, uygulamanın temelini oluşturan kritik hataları gidererek sistemi stabil bir platform haline getirmiştir.

✅ **Düzeltildi (Fixed)**
- **KRİTİK BAŞLANGIÇ HATASI (`ConnectionError`):** Uygulamanın başlamasına engel olan ve Python'un import mekanizmasından kaynaklanan temel bir hata giderildi. Artık tüm modüller borsa bağlantı nesnesine doğru şekilde erişiyor.
- **KRİTİK "HAYALET POZİSYON" HATASI:** Borsada açık olan bir pozisyonun, uygulama tarafından yanlışlıkla "hayalet" olarak algılanıp veritabanından silinmesine neden olan `fetch_positions` çağrısındaki hata giderildi.
- **KRİTİK BACKTEST HATASI (`KeyError`):** Backtest motorunun, anlık analiz için tasarlanmış fonksiyonları yanlış kullanarak çökmesine neden olan mantık hatası, backtester'a özel sinyal üretme mekanizması yazılarak tamamen giderildi.

🔄 **Değiştirildi (Changed)**
- **Backtest Sonuç Gösterimi:** Backtest sonuçlarının (istatistikler ve işlem listesi) arayüzde hatalı gösterilmesine neden olan veri yolu uyumsuzlukları düzeltildi.

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