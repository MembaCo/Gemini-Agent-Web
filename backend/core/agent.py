# backend/core/agent.py
# @author: MembaCo.

import os
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted
from typing import Any # <--- GÜNCELLENDİ

from core import app_config

# --- Global Değişkenler ---
llm = None
model_fallback_list = []
current_model_index = 0

def _get_llm_instance(model_name: str) -> ChatGoogleGenerativeAI:
    """Belirtilen model ismi için bir ChatGoogleGenerativeAI örneği oluşturur."""
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
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY") or ""
    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2") or "false"
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

# --- YENİ BÜTÜNCÜL ANALİZ PROMPT'U ---
def create_holistic_analysis_prompt(
    symbol: str, 
    price: float, 
    timeframe: str, 
    indicators: dict, 
    news_headlines: list[str], 
    sentiment_score: float
) -> str:
    """
    Teknik, temel (haber) ve duyarlılık verilerini birleştirerek
    bütüncül bir analiz için prompt oluşturur.
    """
    indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in indicators.items()])
    news_text = "\n".join([f"- {title}" for title in news_headlines]) if news_headlines else "İlgili haber bulunamadı."
    
    sentiment_emoji = "😊" if sentiment_score > 0.2 else "😒" if sentiment_score < -0.2 else "😐"
    sentiment_text = f"{sentiment_score:.2f} {sentiment_emoji}"

    return f"""
    Sen, hem teknik hem de temel analizi birleştirebilen, piyasa duyarlılığını anlayan
    üst düzey bir finansal analistsin. Görevin, sana sunulan tüm verileri sentezleyerek
    net ve gerekçeli bir ticaret kararı ('AL', 'SAT' veya 'BEKLE') vermektir.

    ## ANALİZ ÇERÇEVESİ:
    1.  **Teknik Analiz:** RSI ve ADX gibi göstergeler piyasanın mevcut momentumunu ve trend gücünü gösterir.
    2.  **Temel Analiz (Haberler):** Son haber başlıkları, fiyatta ani hareketlere neden olabilecek veya mevcut trendi destekleyebilecek önemli gelişmeleri yansıtır.
    3.  **Duyarlılık Analizi:** Sosyal medya duyarlılığı, piyasanın genel 'hissiyatını' ve yatırımcı beklentilerini gösterir. Pozitif skorlar iyimserliği, negatif skorlar kötümserliği belirtir.

    ## SAĞLANAN VERİLER:
    - **Sembol:** {symbol}
    - **Anlık Fiyat:** {price}
    - **Zaman Aralığı:** {timeframe}

    ### 1. Teknik Göstergeler:
    {indicator_text}

    ### 2. Son Haber Başlıkları:
    {news_text}

    ### 3. Sosyal Medya Duyarlılık Skoru (-1.0 ile +1.0 arası):
    {sentiment_text}

    ## GÖREVİN:
    Bu üç veri setini birleştirerek bir sonuca var. 
    - Teknik sinyaller haberlerle destekleniyor mu?
    - Sosyal medya duyarlılığı mevcut trendle uyumlu mu, yoksa bir ayrışma mı var?
    - Sadece tek bir veriye değil, tüm resme bakarak karar ver.

    ## İSTENEN JSON ÇIKTI FORMATI:
    ```json
    {{
      "symbol": "{symbol}",
      "timeframe": "{timeframe}",
      "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
      "reason": "Kararını, teknik, temel ve duyarlılık verilerini nasıl birleştirdiğini açıklayan kısa ve net gerekçen.",
      "analysis_type": "Holistic",
      "data": {{
        "price": {price},
        "sentiment_score": {sentiment_score}
      }}
    }}
    ```
    """

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

def create_reanalysis_prompt(position: dict, current_price: float, indicators: dict) -> str:
    """
    Mevcut bir pozisyonu, GÜNCEL piyasa verileri ve İLK AÇILIŞ GEREKÇESİ ile yeniden değerlendirmek için prompt oluşturur.
    """
    symbol = position.get("symbol")
    timeframe = position.get("timeframe")
    side = "Alış (Long)" if position.get("side") == "buy" else "Satış (Short)"
    entry_price = position.get("entry_price")
    original_reason = position.get("reason", "Belirtilmemiş.")

    indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in indicators.items()])

    return f"""
    Sen, soğukkanlı ve tecrübeli bir pozisyon yöneticisisin. Görevin, zaten açık olan bir pozisyonu objektif bir şekilde yeniden değerlendirmektir.

    ## MEVCUT POZİSYON BİLGİLERİ:
    - Sembol: {symbol}
    - Yön: {side}
    - Giriş Fiyatı: {entry_price}
    - Analiz Zaman Aralığı: {timeframe}

    ## POZİSYONUN İLK AÇILIŞ GEREKÇESİ:
    Bu pozisyon ilk olarak şu düşünceyle açılmıştı: "{original_reason}"

    ## GÜNCEL PİYASA VERİLERİ:
    - Anlık Fiyat: {current_price}
    - Teknik Göstergeler ({timeframe}):
    {indicator_text}

    ## GÖREVİN:
    Yukarıdaki GÜNCEL teknik göstergeleri ve anlık fiyatı, pozisyonun İLK AÇILIŞ GEREKÇESİ ile karşılaştır.
    1.  İlk açılış gerekçesi güncel veriler ışığında hala geçerli mi?
    2.  Yoksa piyasa koşulları, orijinal stratejiyi geçersiz kılacak şekilde değişti mi?
    
    Kararın, bu değerlendirmeye göre 'TUT' (Hold) veya 'KAPAT' (Close) şeklinde olmalı. Pozisyonu sadece küçük bir zarar/kâr etti diye hemen kapatma. Sadece orijinal strateji bozulduysa kapatmayı öner.

    ## NİHAİ RAPOR FORMATI:
    Kararını ve bu kararı vermendeki en önemli teknik gerekçeyi içeren bir JSON nesnesi döndür.
    Örnek: {{"recommendation": "TUT", "reason": "İlk açılış gerekçemiz olan 4 saatlik düzeltme beklentisi devam ediyor ve RSI hala aşırı alım bölgesinde olduğu için pozisyonu tutmak mantıklıdır."}}
    """


def create_mta_analysis_prompt(symbol: str, price: float, entry_timeframe: str, entry_indicators: dict, trend_timeframe: str, trend_indicators: dict) -> str:
    entry_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in entry_indicators.items()])
    trend_indicator_text = "\n".join([f"- {key}: {value:.4f}" for key, value in trend_indicators.items()])
    
    entry_adx = entry_indicators.get('ADX', 0)
    trend_adx = trend_indicators.get('ADX', 0)
    
    if entry_adx > trend_adx:
        dominant_signal_source = entry_timeframe
        dominant_signal_type = "Giriş Sinyali"
    else:
        dominant_signal_source = trend_timeframe
        dominant_signal_type = "Ana Trend"

    return f"""
    Sen, Çoklu Zaman Aralığı (MTA) konusunda uzmanlaşmış, tecrübeli bir trading analistisin.
    Görevin, sana sunulan iki farklı zaman aralığına ait veriyi birleştirerek kapsamlı bir analiz yapmak ve net bir ticaret kararı ('AL', 'SAT' veya 'BEKLE') vermektir.

    ## ANALİZ FELSEFEN:
    1.  **Önce Dominant Sinyali Belirle:** İki zaman diliminin ADX (Trend Gücü) değerlerini karşılaştır. ADX'i yüksek olan, o anki daha baskın sinyaldir.
    2.  **Kararını Dominant Sinyale Göre Şekillendir:** Ana kararını, dominant sinyalin gösterdiği yöne göre ver.
    3.  **Diğer Sinyali Teyit/Zayıflatma İçin Kullan:** Diğer zaman dilimindeki sinyali, ana kararını güçlendiren bir teyit veya zayıflatan bir uyarı olarak yorumla.

    ## SAĞLANAN VERİLER:
    - Sembol: {symbol}
    - Anlık Fiyat: {price}

    ### Ana Trend Verileri ({trend_timeframe})
    {trend_indicator_text}

    ### Giriş Sinyali Verileri ({entry_timeframe})
    {entry_indicator_text}

    ## ÖNCELİKLİ DEĞERLENDİRME TALİMATI:
    - **Dominant Sinyal Kaynağı:** {dominant_signal_source} ({dominant_signal_type})
    - **Açıklama:** Analizini yaparken, '{dominant_signal_source}' zaman diliminden gelen sinyale daha fazla ağırlık ver. Kararını bu sinyal üzerine kur ve diğer zaman dilimini sadece destekleyici veya çürütücü bir faktör olarak kullan.

    ## İSTENEN JSON ÇIKTI FORMATI:
    ```json
    {{
      "symbol": "{symbol}",
      "timeframe": "{entry_timeframe}",
      "recommendation": "KARARIN (AL, SAT, veya BEKLE)",
      "reason": "MTA ve dominant sinyal analizine dayalı detaylı ve nitelikli gerekçen.",
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

# --- GÜNCELLENMİŞ FONKSİYON ---
def parse_agent_response(response: Any) -> dict | None:
    if not response:
        return None
    try:
        # Gelen yanıtın LangChain'in `AIMessage` objesi veya string olabileceğini varsayarak
        # .content özelliğine erişmeyi deneriz.
        content_to_parse = response.content if hasattr(response, 'content') else str(response)
        
        if "```json" in content_to_parse:
            content_to_parse = content_to_parse.split("```json")[1].split("```")[0]
        elif "```" in content_to_parse:
            content_to_parse = content_to_parse.split("```")[1].split("```")[0]
        
        return json.loads(content_to_parse.strip())
    except (json.JSONDecodeError, IndexError) as e:
        # Yanıt objesini string'e çevirerek loglamayı daha güvenli hale getirelim.
        logging.error(f"JSON ayrıştırma hatası. Gelen Yanıt: {str(response)}. Hata: {e}")
        return None