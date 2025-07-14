# Değişiklik Günlüğü
Tüm önemli proje değişiklikleri bu dosyada belgelenmektedir.
...
---

### [4.8.0] - 2025-07-15 - Mantıksal Tutarlılık ve Kalıcı Veri Düzeltmeleri
Bu sürüm, botun temel mantığındaki en önemli çelişkilerden birini gidererek "aç-kapa" döngülerini engeller ve uygulamanın en kritik sorunlarından biri olan veri sıfırlanması problemini kalıcı olarak çözer.

**🧠 Değiştirildi (Changed)**

AI Analiz Mantığına "Hafıza" Eklendi: Bir pozisyon açıldıktan hemen sonra yapılan yeniden analizlerde, AI'ın "Risk Yöneticisi" rolüne bürünerek "Fırsat Avcısı" rolündeki kendi tavsiyesini geçersiz kılması sorunu giderildi. Artık yeniden analiz prompt'u (create_reanalysis_prompt), pozisyonun ilk açılış gerekçesini de içeriyor. Bu sayede AI, "Bu pozisyonu neden açmıştık? O gerekçe hala geçerli mi?" sorusunu sorarak çok daha tutarlı ve akıllıca kararlar veriyor.

✅ **✅ Düzeltildi (Fixed)**

KRİTİK: Veritabanı Sıfırlanma Hatası Giderildi: Uygulama (Docker konteyneri) her yeniden başlatıldığında veritabanının (trades.db) sıfırlanmasına neden olan kritik bir yol hatası düzeltildi. Veritabanı yolu artık her zaman kalıcı depolama alanını (/app/data) gösterecek şekilde sabitlendi, böylece tüm ayarlar, pozisyonlar ve işlem geçmişi kalıcı hale getirildi.

Parametre Uyumsuzluk Hataları (ValidationError): Projenin farklı yerlerinde (api/analysis.py, api/scanner.py, api/positions.py), get_technical_indicators aracına tek bir birleşik string gönderilmesinden kaynaklanan tüm ValidationError ve AttributeError: 'str' object has no attribute 'parent_run_id' hataları giderildi. Tüm fonksiyon çağrıları, artık symbol ve timeframe parametrelerini ayrı ayrı gönderecek şekilde standartlaştırıldı.

Telegram Bildirim Hatası (can't parse entities): Yapay zekanın ürettiği gerekçelerin özel karakterler (*, _ vb.) içermesi durumunda Telegram bildirimlerinin gönderilememesine neden olan hata, gönderilecek tüm metinlerin Telegram'a uygun şekilde temizlenmesiyle (escaping) çözüldü.

Proaktif Tarayıcı Teşhis Mekanizması: Proaktif tarayıcının neden aday bulamadığını anlamak için core/scanner.py dosyasına detaylı teşhis loglaması eklendi. Artık bir adayın hangi filtreye (RSI, ADX, Volatilite vb.) takıldığı loglarda açıkça belirtiliyor, bu da gelecekteki kalibrasyonları kolaylaştırıyor.

---
### [4.6.0] - 2025-07-08 - Telegram Bot Devrimi ve Kararlılık Düzeltmeleri
Bu sürüm, Telegram botunu basit bir bildirim aracından, projenin tam teşekküllü bir uzaktan kumandasına dönüştürürken, uygulamanın kendi kendine kapanmasına neden olan kritik bir arka plan hatasını gidererek tam kararlılık sağlar.

🚀 **Eklendi (Added)**

- ***Tam İnteraktif Telegram Botu:*** Telegram botu, aşağıdaki özelliklerle baştan sona yenilendi:

- ***İnteraktif Pozisyon Yönetimi:*** /pozisyonlar komutu artık her pozisyonun altına "Yeniden Analiz Et" ve "Kapat" butonları ekleyerek tek tıkla yönetim imkanı sunar.

- ***İnteraktif Ayar Sihirbazı:*** /ayar_degistir komutu ile, kullanıcıya adım adım ve butonlarla hangi ayarı değiştirmek istediğini soran bir diyalog akışı eklendi.

- ***Anlık Grafik Çizimi:*** /grafik <SEMBOL> <ARALIK> komutu ile, belirtilen paritenin anlık mum grafiğini ve temel göstergelerini doğrudan Telegram'a resim olarak gönderen bir özellik eklendi.

- ***Detaylı Raporlama:*** /rapor, /ayarlar ve /detay gibi yeni komutlarla botun performansı, ayarları ve pozisyonların açılış nedenleri gibi bilgilere anında erişim sağlandı.

- ***Panik Butonları:*** /durdur ve /baslat komutları ile LIVE_TRADING modu uzaktan anında açılıp kapatılabilir hale getirildi.

✅ **Düzeltildi (Fixed)**

KRİTİK: Sunucunun Kendi Kendine Kapanma Hatası: FastAPI (Uvicorn) ile python-telegram-bot kütüphanesi arasındaki asyncio olay döngüsü (event loop) çakışması giderildi. Bu hata, uygulamanın başladıktan kısa bir süre sonra herhangi bir hata vermeden kapanmasına neden oluyordu. Bu düzeltme ile uygulama artık kararlı bir şekilde çalışmaktadır.

trader.py reason Parametresi Hatası: Yeni bir pozisyon açılırken, AI analizinden her zaman bir "gerekçe" gelmemesi durumunda uygulamanın çökmesine neden olan hata, reason parametresine varsayılan bir değer atanarak giderildi.

Telegram PTBUserWarning Uyarısı: Konsol çıktısında görünen ve kafa karışıklığına neden olan bilgilendirme uyarısı, işlevselliği etkilemeden gizlendi.
---
### [4.5.0] - 2025-07-08 - Hızlı Kâr Alma (Scalp Exit) ve Simülasyon Modu İyileştirmeleri
- **Bu sürüm, volatil piyasalarda hızlı kâr almayı sağlayan yeni bir strateji eklerken, LIVE_TRADING kapalıyken kullanılan simülasyon modunu temelden iyileştirerek daha kararlı ve mantıklı bir test ortamı sunar.**

🚀 **Eklendi (Added)**

Hızlı Kâr Alma (Scalp Exit) Özelliği: Pozisyonların, önceden belirlenmiş bir kâr yüzdesine ulaştığında diğer kuralları beklemeden otomatik olarak kapatılmasını sağlayan yeni bir strateji eklendi. Bu özellik, özellikle volatil altcoinlerdeki ani yükselişlerden kâr elde etmek için tasarlanmıştır (USE_SCALP_EXIT, SCALP_EXIT_PROFIT_PERCENT).

Sanal Bakiye (Virtual Balance) Ayarı: Simülasyon modunda (LIVE_TRADING kapalıyken) kullanılmak üzere, arayüzden yönetilebilen bir sanal bakiye (VIRTUAL_BALANCE) ayarı eklendi. Bu sayede, test işlemleri gerçek cüzdan bakiyesinden tamamen bağımsız hale getirildi.

✅ **Düzeltildi (Fixed)**S

KRİTİK: Simülasyon Modu "Hayalet Pozisyon" Hatası: LIVE_TRADING kapalıyken, sistemin borsadaki pozisyonlarla senkronize olmaya çalışması ve bu nedenle simülasyon işlemlerini "hayalet" olarak algılayıp silmesi hatası tamamen giderildi. Artık simülasyon modunda borsa ile pozisyon senkronizasyonu yapılmamaktadır.

KRİTİK: Simülasyon Modu "Yetersiz Bakiye" Hatası: Simülasyon modunda işlem açmaya çalışırken, sistemin gerçek bakiye kontrolü yapması nedeniyle oluşan "yetersiz bakiye" hatası, yeni eklenen sanal bakiye sistemi ile çözüldü.

Arayüz Ayarlarının Yenilenme Sorunu: "Uygulama Ayarları" penceresi açıkken, sayfanın 5 saniyede bir yenilenmesi nedeniyle ayar yapmanın zorlaşması sorunu giderildi. Artık ayarlar penceresi açıkken arka plan veri yenilemesi duraklatılmaktadır.

---
### [4.4.3] - 2025-07-06 - Pozisyonların Ters Yöne Dönme Hatası Düzeltildi

Bu sürüm, stop-loss veya manuel kapatma sonrası pozisyonların yanlışlıkla ters yönde yeniden açılmasına neden olan kritik bir mantık hatasını gidermektedir.

✅ **Düzeltildi (Fixed)**
- **KRİTİK: Pozisyonların Tersine Dönme (Flip) Hatası:** Stop-loss veya manuel kapatma gibi senaryolarda gönderilen piyasa emirlerinin, pozisyonu kapatmak yerine ters yönde yeni bir pozisyon açması hatası giderildi. Tüm kapatma emirlerine, borsaya emrin sadece mevcut pozisyonu azaltabileceğini bildiren `reduceOnly: true` parametresinin eklenmesi sağlandı. Bu, botun kararlılığını temelden etkileyen bir düzeltmedir.

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

Kolay Kurulum (Self-Hosted):

Dockerfile ve docker-compose.yml dosyaları ile proje tamamen konteynerize edildi.

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