# backend/core/agent.py
# @author: Memba Co.

import os
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted

from core import app_config

# --- Global Değişkenler ---
llm = None
model_fallback_list = []
current_model_index = 0

def _get_llm_instance(model_name: str) -> ChatGoogleGenerativeAI:
    """Belirtilen model ismi için bir ChatGoogleGenerativeAI örneği oluşturur."""
    # DÜZELTME: Kullanımdan kaldırılan 'convert_system_message_to_human' parametresi kaldırıldı.
    return ChatGoogleGenerativeAI(model=model_name, temperature=0.1)

def _initialize_model_list_and_llm():
    """
    Ayarlardan model listesini oluşturur ve ilk LLM örneğini başlatır.
    """
    global llm, model_fallback_list, current_model_index
    
    primary_model = app_config.settings.get('GEMINI_MODEL', 'gemini-1.5-flash')
    fallback_order = app_config.settings.get('GEMINI_MODEL_FALLBACK_ORDER', [])
    
    ordered_models = [primary_model]
    for model in fallback_order:
        if model not in ordered_models:
            ordered_models.append(model)
    
    model_fallback_list = ordered_models
    current_model_index = 0
    
    if not model_fallback_list:
        logging.critical("Kullanılacak hiçbir Gemini modeli belirtilmemiş. Lütfen ayarları kontrol edin.")
        llm = None
        return

    try:
        current_model_name = model_fallback_list[current_model_index]
        llm = _get_llm_instance(current_model_name)
        logging.info(f"AI Agent başarıyla başlatıldı. Aktif model: {current_model_name}")
        logging.info(f"Model deneme sırası: {' -> '.join(model_fallback_list)}")
    except Exception as e:
        logging.critical(f"{model_fallback_list[0]} modeli başlatılırken kritik hata: {e}", exc_info=True)
        llm = None

def switch_to_next_model():
    """
    Sıradaki modele geçer. Eğer liste bittiyse, başa döner ama kritik bir log atar.
    """
    global llm, current_model_index

    current_model_index += 1
    if current_model_index >= len(model_fallback_list):
        logging.error("Tüm Gemini modellerinin kotaları tükendi. Tarama geçici olarak durduruldu. Listenin başına dönülüyor.")
        current_model_index = 0

    next_model_name = model_fallback_list[current_model_index]
    logging.warning(f"Kota aşıldı! Bir sonraki modele geçiliyor: {next_model_name}")
    
    try:
        llm = _get_llm_instance(next_model_name)
        logging.info(f"AI Agent, yeni aktif modelle güncellendi: {next_model_name}")
        return True
    except Exception as e:
        logging.error(f"{next_model_name} modeline geçilirken hata: {e}", exc_info=True)
        llm = None
        return False

def initialize_agent():
    """Uygulama başladığında veya ayarlar değiştiğinde LLM'i başlatır/yeniden başlatır."""
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "Gemini Trading Agent")
    _initialize_model_list_and_llm()

def llm_invoke_with_fallback(prompt: str):
    """
    LLM'i çağırır ve kota hatası durumunda otomatik olarak model değiştirip tekrar dener.
    """
    if not llm:
        raise Exception("LLM örneği başlatılamadı. Lütfen yapılandırmayı kontrol edin.")

    max_retries = len(model_fallback_list)
    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt)
        except ResourceExhausted as e:
            logging.warning(f"Kota hatası ({model_fallback_list[current_model_index]}): {e}")
            if attempt < max_retries - 1:
                switched = switch_to_next_model()
                if not switched:
                    raise Exception("Tüm modellere geçiş denendi ancak LLM başlatılamadı.")
            else:
                logging.critical("Tüm modellerin kotaları denendi ve hepsi başarısız oldu.")
                raise e
        except Exception as e:
            logging.error(f"LLM çağrısı sırasında beklenmedik hata: {e}", exc_info=True)
            raise e
    
    raise Exception("Tüm modeller denendi ancak LLM çağrısı başarılı olamadı.")

def create_bailout_reanalysis_prompt(position: dict, current_price: float, pnl_percentage: float, indicators: dict) -> str:
    """Zarardaki bir pozisyonun toparlanma anında kapatılıp kapatılmamasını sorgulamak için prompt oluşturur."""
    side = "Alış (Long)" if position['side'] == "buy" else "Satış (Short)"
    extremum_price_label = "Gördüğü En Düşük Fiyat" if position['side'] == "buy" else "Gördüğü En Yüksek Fiyat"
    indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in indicators.items()])

    return f"""
    Sen, soğukkanlı ve tecrübeli bir risk yöneticisisin. Görevin, zarardaki bir pozisyon için kritik bir anda çıkış kararı vermek.

    ## DURUM ANALİZİ:
    - **Pozisyon:** {position['symbol']} / {side}
    - **Giriş Fiyatı:** {position['entry_price']}
    - **Mevcut Durum:** Pozisyon şu anda %{pnl_percentage:.2f} zararda.
    - **Önemli Gözlem:** Pozisyon, {extremum_price_label} olan {position['extremum_price']} seviyesine kadar geriledikten sonra bir toparlanma göstererek anlık {current_price} fiyatına ulaştı. Bu, zararı azaltmak için bir fırsat olabilir, ancak aynı zamanda daha büyük bir toparlanmanın başlangıcı da olabilir.

    ## GÜNCEL TEKNİK VERİLER ({position['timeframe']}):
    {indicator_text}

    ## GÖREVİN:
    Yukarıdaki verileri analiz ederek, bu pozisyon için ŞİMDİ verilecek en mantıklı karar nedir?
    - **TUT:** Eğer toparlanmanın devam etme potansiyeli yüksekse ve erken çıkış bir fırsat maliyeti yaratacaksa bu kararı ver.
    - **KAPAT:** Eğer bu yükselişin geçici bir tepki ("dead cat bounce") olduğunu ve düşüşün/yükselişin (pozisyon yönüne göre) devam edeceğini düşünüyorsan, zararı burada kesmek için bu kararı ver.

    ## İSTENEN JSON ÇIKTI FORMATI:
    Sadece "TUT" veya "KAPAT" kararını ve tek cümlelik gerekçeni içeren bir JSON nesnesi döndür.
    ```json
    {{
      "recommendation": "KARARIN (TUT veya KAPAT)",
      "reason": "Kararının dayandığı en önemli teknik gerekçe."
    }}
    ```
    """

def create_reanalysis_prompt(position: dict) -> str:
    """Mevcut bir pozisyonu yeniden değerlendirmek için prompt oluşturur."""
    # Bu fonksiyon, LangChain Agent'ından bağımsız olduğu için LangChain araçlarını çağırmaz.
    # Bu nedenle, `get_technical_indicators` gibi araçları doğrudan çağırmaz.
    # Bunun yerine, LangChain'in `llm.invoke` metodu ile kullanılacak bir metin istemi oluşturur.
    symbol = position.get("symbol")
    timeframe = position.get("timeframe")
    side = position.get("side", "").upper()
    entry_price = position.get("entry_price")
    
    # Not: Bu prompt, AI'nın daha iyi bir karar vermesi için gerekli teknik verileri
    # içermelidir. Ancak, bu fonksiyonun kendisi bu verileri çekmez. Verilerin
    # bu fonksiyonu çağıran yer (örn. api/positions.py) tarafından sağlanması ve
    # prompt'a eklenmesi daha modüler bir yaklaşım olurdu.
    # Şimdilik, eski `agent` yapısındaki gibi sadece temel pozisyon bilgilerini kullanıyoruz.
    return f"""
    Sen, tecrübeli bir pozisyon yöneticisisin.
    ## Mevcut Pozisyon Bilgileri:
    - Sembol: {symbol}
    - Yön: {side}
    - Giriş Fiyatı: {entry_price}
    - Analiz Zaman Aralığı: {timeframe}

    ## Görevin:
    Bu pozisyonun GÜNCEL durumu hakkında net bir tavsiye ver. Teknik göstergeleri ve anlık fiyatı kullanarak pozisyonun devam edip etmemesi gerektiğini değerlendir. Kararın 'TUT' (Hold) veya 'KAPAT' (Close) şeklinde olmalı.

    ## Nihai Rapor Formatı:
    Kararını ve gerekçeni içeren bir JSON nesnesi döndür.
    Örnek: {{"recommendation": "KAPAT", "reason": "Fiyat giriş seviyesinin üzerine çıktı ve RSI aşırı alım sinyali veriyor, risk yönetimi gereği kapatılmalı."}}
    """


def create_mta_analysis_prompt(symbol: str, price: float, entry_timeframe: str, entry_indicators: dict, trend_timeframe: str, trend_indicators: dict) -> str:
    entry_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in entry_indicators.items()])
    trend_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in trend_indicators.items()])
    return f"""
    Sen, Çoklu Zaman Aralığı (MTA) konusunda uzmanlaşmış, tecrübeli bir trading analistisin.
    Görevin, sana sunulan iki farklı zaman aralığına ait veriyi birleştirerek kapsamlı bir analiz yapmak ve net bir ticaret kararı ('AL', 'SAT' veya 'BEKLE') vermektir.
    ## ANALİZ FELSEFEN:
    1.  **Önce Ana Trendi Anla:** '{trend_timeframe}' zaman aralığındaki verilere bakarak ana trendin yönünü ve GÜCÜNÜ (ADX değerine göre) belirle.
    2.  **Giriş Sinyalini Değerlendir:** '{entry_timeframe}' zaman aralığındaki sinyali ve GÜCÜNÜ (ADX ve RSI seviyelerine göre) analiz et.
    3.  **Sinyalleri Birlikte Yorumla (En Önemli Adım):**
        - **Teyit Durumu:** Eğer ana trend ile giriş sinyali aynı yöndeyse, bu güçlü bir teyittir.
        - **Çelişki Durumu:** Eğer ana trend ile giriş sinyali arasında bir uyumsuzluk varsa, sinyallerin gücünü tart.
    
    ## SAĞLANAN VERİLER:
    - Sembol: {symbol}
    - Anlık Fiyat: {price}
    ### Ana Trend Verileri ({trend_timeframe})
    {trend_indicator_text}
    ### Giriş Sinyali Verileri ({entry_timeframe})
    {entry_indicator_text}
    ## İSTENEN JSON ÇIKTI FORMATI:
    ```json
    {{
      "symbol": "{symbol}",
      "timeframe": "{entry_timeframe}",
      "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
      "reason": "MTA analizine dayalı detaylı ve nitelikli gerekçen.",
      "analysis_type": "MTA",
      "trend_timeframe": "{trend_timeframe}",
      "data": {{"price": {price}}}
    }}
    ```
    """

def create_final_analysis_prompt(symbol: str, timeframe: str, price: float, indicators: dict) -> str:
    indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in indicators.items()])
    return f"""
    Sen, uzman bir trading analistisin.
    GÖREVİN: Verileri analiz ederek 'AL', 'SAT' veya 'BEKLE' kararı ver.
    SAĞLANAN VERİLER:
    - Sembol: {symbol}
    - Zaman Aralığı: {timeframe}
    - Anlık Fiyat: {price}
    - Teknik Göstergeler:
    {indicator_text}
    İSTENEN JSON ÇIKTI FORMATI:
    ```json
    {{
      "symbol": "{symbol}",
      "timeframe": "{timeframe}",
      "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
      "reason": "Kararının kısa ve net gerekçesi.",
      "analysis_type": "Single",
      "data": {{"price": {price}}}
    }}
    ```
    """

def parse_agent_response(response: str) -> dict | None:
    if not response or not isinstance(response, str):
        return None
    try:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return json.loads(response.strip())
    except (json.JSONDecodeError, IndexError):
        logging.error(f"JSON ayrıştırma hatası. Gelen Yanıt: {response}")
        return None
