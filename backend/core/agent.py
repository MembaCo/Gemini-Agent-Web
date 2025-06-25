# ==============================================================================
# File: backend/core/agent.py
# @author: Memba Co.
# ==============================================================================
import os
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from dotenv import load_dotenv

from core import app_config
from tools import get_market_price, get_technical_indicators
from tools.utils import str_to_bool

load_dotenv()
llm = None
agent_executor = None

def initialize_agent():
    """Uygulama başladığında LLM'i ve LangChain Agent'ını başlatır."""
    global llm, agent_executor
    if llm and agent_executor:
        return

    try:
        logging.info("LLM ve LangChain Agent başlatılıyor...")
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
        os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "Gemini Trading Agent")
        
        llm = ChatGoogleGenerativeAI(model=app_config.settings['GEMINI_MODEL'], temperature=0.1)
        
        agent_tools = [get_market_price, get_technical_indicators]
        prompt_template = hub.pull("hwchase17/react")
        agent = create_react_agent(llm=llm, tools=agent_tools, prompt=prompt_template)
        agent_executor = AgentExecutor(
            agent=agent, tools=agent_tools, verbose=str_to_bool(os.getenv("AGENT_VERBOSE", "True")),
            handle_parsing_errors="Lütfen JSON formatında geçerli bir yanıt ver.", max_iterations=7
        )
        logging.info("LLM ve Agent başarıyla başlatıldı.")
    except Exception as e:
        logging.critical(f"LLM veya Agent başlatılırken kritik hata oluştu: {e}", exc_info=True)
        raise e

def create_mta_analysis_prompt(symbol: str, price: float, entry_timeframe: str, entry_indicators: dict, trend_timeframe: str, trend_indicators: dict) -> str:
    """
    Multi-Timeframe Analysis (MTA) için GELİŞTİRİLMİŞ prompt oluşturur.
    Bu yeni sürüm, AI'nın sinyal güçlerini tartmasını ve trend dönüşlerini yorumlamasını teşvik eder.
    """
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
    """Tek zamanlı standart analiz için prompt oluşturur."""
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

def create_reanalysis_prompt(position: dict) -> str:
    """Mevcut bir pozisyonu yeniden değerlendirmek için prompt oluşturur."""
    symbol = position.get("symbol")
    timeframe = position.get("timeframe")
    side = position.get("side", "").upper()
    entry_price = position.get("entry_price")
    return f"""
    Sen, tecrübeli bir pozisyon yöneticisisin.
    ## Mevcut Pozisyon Bilgileri:
    - Sembol: {symbol}
    - Yön: {side}
    - Giriş Fiyatı: {entry_price}
    - Analiz Zaman Aralığı: {timeframe}
    ## Görevin:
    Bu pozisyonun mevcut durumunu teknik göstergeleri ve anlık fiyatı kullanarak yeniden değerlendir. Ardından, pozisyon için 'TUT' (Hold) veya 'KAPAT' (Close) şeklinde net bir tavsiye ver.
    Başka bir eylemde bulunma, sadece tavsiye ver.
    ## Nihai Rapor Formatı:
    Kararını ve gerekçeni içeren bir JSON nesnesi döndür.
    Örnek: {{"recommendation": "KAPAT", "reason": "Fiyat giriş seviyesinin üzerine çıktı ve RSI aşırı alım sinyali veriyor, risk yönetimi gereği kapatılmalı."}}
    """

def parse_agent_response(response: str) -> dict | None:
    """Agent'tan gelen JSON yanıtını temizler ve ayrıştırır."""
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

