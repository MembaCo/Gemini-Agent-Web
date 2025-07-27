# backend/tools/market_sentiment.py
# @author: MembaCo.

import os
import logging
import requests # <--- YENİ: CryptoPanic için eklendi
import tweepy
from textblob import TextBlob
from newsapi import NewsApiClient
from core import app_config, cache_manager

# --- API Anahtarlarını Ortam Değişkenlerinden Oku ---
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY") # <--- YENİ: CryptoPanic API anahtarı

# Tweepy v2 istemcisini (client) başlat
try:
    if TWITTER_BEARER_TOKEN:
        twitter_client = tweepy.Client(TWITTER_BEARER_TOKEN)
    else:
        twitter_client = None
        logging.warning("Twitter Bearer Token bulunamadı. Duyarlılık analizi devre dışı.")
except Exception as e:
    twitter_client = None
    logging.error(f"Twitter istemcisi başlatılırken hata: {e}")

# NewsAPI İstemcisini Başlat
try:
    if NEWSAPI_API_KEY:
        newsapi_client = NewsApiClient(api_key=NEWSAPI_API_KEY)
    else:
        newsapi_client = None
        logging.warning("NewsAPI anahtarı bulunamadı. Alternatif haber kaynağı devre dışı.")
except Exception as e:
    newsapi_client = None
    logging.error(f"NewsAPI istemcisi başlatılırken hata: {e}")


def get_newsapi_headlines(symbol: str, limit: int = 5) -> list[str]:
    """NewsAPI kullanarak haber başlıklarını çeker."""
    if not newsapi_client: return []
    try:
        base_symbol = symbol.split('/')[0]
        q = f'"{base_symbol}" OR "{symbol}" AND (crypto OR cryptocurrency OR bitcoin OR blockchain)'
        response = newsapi_client.get_everything(q=q, language='en', sort_by='publishedAt', page_size=limit)
        if response.get('status') == 'ok' and response.get('articles'):
            titles = [article['title'] for article in response['articles']]
            logging.info(f"NewsAPI'dan {symbol} için {len(titles)} adet haber başlığı başarıyla çekildi.")
            return titles
        return []
    except Exception as e:
        logging.error(f"NewsAPI'dan {symbol} için haberler alınırken hata: {e}")
        return []

# --- YENİ: CryptoPanic Haber Fonksiyonu ---
def get_cryptopanic_headlines(symbol: str, limit: int = 5) -> list[str]:
    """CryptoPanic API'sini kullanarak haber başlıklarını çeker."""
    if not CRYPTOPANIC_API_KEY: return []
    try:
        base_symbol = symbol.split('/')[0]
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&currencies={base_symbol}&public=true"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('results'):
            titles = [item['title'] for item in data['results'][:limit]]
            logging.info(f"CryptoPanic'ten {symbol} için {len(titles)} adet haber başlığı çekildi.")
            return titles
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"{symbol} için CryptoPanic haberleri alınırken hata oluştu: {e}")
        return []

# --- GÜNCELLENDİ: Ana fonksiyon artık ayarları kontrol ediyor ---
def get_latest_crypto_news(symbol: str, limit: int = 5) -> list[str]:
    """
    Ayarlarda aktif olan haber kaynaklarından en son haber başlıklarını çeker.
    """
    all_headlines = []

    if app_config.settings.get("USE_NEWSAPI"):
        all_headlines.extend(get_newsapi_headlines(symbol, limit))
    
    # --- GÜNCELLENDİ: Yeni ayar anahtarı kullanılıyor ---
    if app_config.settings.get("USE_CRYPTOPANIC_NEWS"):
        all_headlines.extend(get_cryptopanic_headlines(symbol, limit))

    if not all_headlines:
        return ["Aktif kaynaklardan ilgili haber bulunamadı."]
        
    return list(dict.fromkeys(all_headlines))


def get_twitter_sentiment(symbol: str, tweet_count: int = 30) -> dict:
    # ... (Bu fonksiyon aynı kalıyor)
    if not app_config.settings.get("PROACTIVE_SCAN_USE_SENTIMENT"):
        return {"score": 0.0, "subjectivity": 0.0}
    
    cache_key = f"sentiment_{symbol}"
    cached_result = cache_manager.get(cache_key)
    if cached_result:
        return cached_result
        
    if not twitter_client:
        return {"score": 0.0, "subjectivity": 0.0, "error": "Twitter istemcisi yapılandırılmamış."}

    try:
        base_symbol = symbol.split('/')[0]
        query = f'"{base_symbol}" OR "${base_symbol}" -is:retweet lang:en'
        
        response = twitter_client.search_recent_tweets(
            query=query,
            max_results=max(10, min(100, tweet_count)),
            tweet_fields=["text"]
        )
        
        tweets = response.data if response and hasattr(response, 'data') and response.data else []
        if not tweets:
            logging.warning(f"{symbol} için Twitter'da ilgili tweet bulunamadı.")
            result = {"score": 0.0, "subjectivity": 0.0}
            cache_manager.set(cache_key, result, ttl=600)
            return result

        total_polarity = 0
        total_subjectivity = 0
        
        for tweet in tweets:
            analysis = TextBlob(tweet.text)
            total_polarity += analysis.sentiment.polarity
            total_subjectivity += analysis.sentiment.subjectivity
            
        avg_polarity = total_polarity / len(tweets) if tweets else 0
        avg_subjectivity = total_subjectivity / len(tweets) if tweets else 0
        
        logging.info(f"{symbol} için {len(tweets)} tweet analiz edildi. Ortalama Duyarlılık: {avg_polarity:.2f}")
        
        result = {"score": round(avg_polarity, 2), "subjectivity": round(avg_subjectivity, 2)}
        cache_manager.set(cache_key, result, ttl=600)
        return result

    except tweepy.TweepyException as e:
        logging.error(f"Twitter API hatası ({symbol}): {e}")
        result = {"score": 0.0, "subjectivity": 0.0, "error": f"Twitter API Hatası: {str(e)}"}
        cache_manager.set(cache_key, result, ttl=120) 
        return result
    except Exception as e:
        logging.error(f"{symbol} için duyarlılık analizi sırasında genel hata: {e}")
        return {"score": 0.0, "subjectivity": 0.0, "error": str(e)}