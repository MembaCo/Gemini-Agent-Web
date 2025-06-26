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
    
    # Birincil modeli listenin başına ekle ve tekrarları kaldırarak benzersiz bir liste oluştur
    ordered_models = [primary_model]
    for model in fallback_order:
        if model not in ordered_models:
            ordered_models.append(model)
    
    model_fallback_list = ordered_models
    current_model_index = 0 # Her zaman ilk modelle başla
    
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
        current_model_index = 0 # Başa dön

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


def create_mta_analysis_prompt(symbol: str, price: float, entry_timeframe: str, entry_indicators: dict, trend_timeframe: str, trend_indicators: dict) -> str:
    entry_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in entry_indicators.items()])
    trend_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in trend_indicators.items()])
    return f"""
    Sen, Çoklu Zaman Aralığı (MTA) konusunda uzmanlaşmış, tecrübeli bir trading analistisin.
    Görevin, sana sunulan iki farklı zaman aralığına ait veriyi birleştirerek kapsamlı bir analiz yapmak ve net bir ticaret kararı ('AL', 'SAT' veya 'BEKLE') vermektir.
    ## ANALİZ FELSEFEN:
    1.  **Önce Ana Trendi Anla:** '{trend_timeframe}' zaman aralığındaki verilere bakarak ana trendin yönünü ve GÜCÜNÜ (ADX değerine göre) belirle.
        - ADX < 20: Yönsüz piyasa.
        - ADX 20-25: Zayıf trend.
        - ADX > 25: Güçlü trend.
    2.  **Giriş Sinyalini Değerlendir:** '{entry_timeframe}' zaman aralığındaki sinyali ve GÜCÜNÜ (ADX ve RSI seviyelerine göre) analiz et.
        - RSI < 30 veya > 70: Güçlü aşırı alım/satım sinyali.
        - ADX > 40: Çok güçlü bir momentum göstergesi.
    3.  **Sinyalleri Birlikte Yorumla (En Önemli Adım):**
        - **Teyit Durumu:** Eğer ana trend ile giriş sinyali aynı yöndeyse (örn: 4s yükseliş, 15m AL sinyali), bu güçlü bir teyittir. Kararın net bir şekilde 'AL' veya 'SAT' olabilir.
        - **Çelişki Durumu (SENİN UZMANLIĞIN BURADA):** Eğer ana trend ile giriş sinyali arasında bir uyumsuzluk varsa, sadece 'BEKLE' deyip geçme. Sinyallerin gücünü tart.
            - **Örnek 1:** Eğer '{trend_timeframe}' trendi ZAYIF (örn: ADX=23) ama '{entry_timeframe}' sinyali ÇOK GÜÇLÜ ise (örn: ADX=50 ve RSI=19), bu bir **TREND DÖNÜŞÜ** potansiyeli olabilir. Bu durumda, ana trendin aksine bir pozisyon önerisinde bulunabilirsin ('AL' veya 'SAT'). Gerekçende bunu mutlaka belirt.
            - **Örnek 2:** Eğer her iki sinyal de zayıf veya belirsizse, o zaman 'BEKLE' kararı en doğrusudur.
    ## SAĞLANAN VERİLER:
    - Sembol: {symbol}
    - Anlık Fiyat: {price}
    ### Ana Trend Verileri ({trend_timeframe})
    {trend_indicator_text}
    ### Giriş Sinyali Verileri ({entry_timeframe})
    {entry_indicator_text}
    ## İSTENEN JSON ÇIKTI FORMATI:
    Kararını ve yukarıdaki felsefeye dayalı detaylı gerekçeni, aşağıda formatı verilen JSON çıktısı olarak sun. Başka hiçbir açıklama yapma.
    ```json
    {{
      "symbol": "{symbol}",
      "timeframe": "{entry_timeframe}",
      "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
      "reason": "MTA analizine dayalı detaylı ve nitelikli gerekçen. Sinyal güçlerinden ve olası trend dönüşünden bahset.",
      "analysis_type": "MTA",
      "trend_timeframe": "{trend_timeframe}",
      "data": {{
        "price": {price}
      }}
    }}
    ```
    """

def create_final_analysis_prompt(symbol: str, timeframe: str, price: float, indicators: dict) -> str:
    indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in indicators.items()])
    return f"""
    Sen, uzman bir trading analistisin.
    Aşağıda sana '{symbol}' adlı kripto para için '{timeframe}' zaman aralığında toplanmış veriler sunulmuştur.
    GÖREVİN: Bu verileri analiz ederek 'AL', 'SAT' veya 'BEKLE' şeklinde net bir tavsiye kararı ver.
    Kararını ve gerekçeni, aşağıda formatı verilen JSON çıktısı olarak sun. Başka hiçbir açıklama yapma.
    SAĞLANAN VERİLER:
    - Anlık Fiyat: {price}
    Teknik Göstergeler:
    {indicator_text}
    İSTENEN JSON ÇIKTI FORMATI:
    ```json
    {{
      "symbol": "{symbol}",
      "timeframe": "{timeframe}",
      "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
      "reason": "Kararının kısa ve net gerekçesi.",
      "analysis_type": "Single",
      "data": {{
        "price": {price}
      }}
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
