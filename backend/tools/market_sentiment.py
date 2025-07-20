# backend/tools/market_sentiment.py
# @author: MembaCo.

import os
import logging
import cryptocompare
import tweepy
from textblob import TextBlob

# --- API Anahtarlarını Ortam Değişkenlerinden Oku ---
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

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


def get_latest_crypto_news(symbol: str, limit: int = 5) -> list[str]:
    """
    CryptoCompare API'sini kullanarak belirtilen kripto varlık için en son
    haber başlıklarını çeker.

    Args:
        symbol (str): Haberleri alınacak sembol (örn: 'BTC').
        limit (int): Çekilecek maksimum haber başlığı sayısı.

    Returns:
        list[str]: Haber başlıklarının bir listesi.
    """
    if not CRYPTOCOMPARE_API_KEY:
        logging.warning("CryptoCompare API anahtarı bulunamadı. Haber verisi çekilemiyor.")
        return ["CryptoCompare API anahtarı yapılandırılmamış."]

    try:
        cryptocompare.cryptocompare._set_api_key_parameter(CRYPTOCOMPARE_API_KEY)
        base_symbol = symbol.split('/')[0]
        news_list = cryptocompare.get_latest_news(base_symbol)
        
        if not news_list:
            return ["İlgili haber bulunamadı."]
            
        titles = [item.get('title', 'Başlık bulunamadı') for item in news_list[:limit]]
        return titles if titles else ["İlgili haber bulunamadı."]
        
    except Exception as e:
        logging.error(f"{symbol} için haberler alınırken hata oluştu: {e}")
        return [f"Haber API hatası: {str(e)}"]


def get_twitter_sentiment(symbol: str, tweet_count: int = 30) -> dict:
    """
    Belirtilen sembol için Twitter'dan son tweet'leri çeker ve TextBlob
    kullanarak bir duyarlılık skoru hesaplar.

    Args:
        symbol (str): Duyarlılık analizi yapılacak sembol (örn: 'BTC').
        tweet_count (int): Analiz için çekilecek tweet sayısı.

    Returns:
        dict: 'score' ve 'subjectivity' içeren bir sözlük.
    """
    if not twitter_client:
        return {"score": 0.0, "subjectivity": 0.0, "error": "Twitter istemcisi yapılandırılmamış."}

    try:
        base_symbol = symbol.split('/')[0]
        # Twitter'da arama yapmak için sorgu oluştur (örn: "$BTC -is:retweet lang:en")
        query = f'"{base_symbol}" OR "${base_symbol}" -is:retweet lang:en'
        
        # Twitter API'sinden tweet'leri çek
        response = twitter_client.search_recent_tweets(
            query=query,
            max_results=max(10, min(100, tweet_count)), # API limitleri 10-100 arası
            tweet_fields=["text"]
        )
        
        tweets = response.data
        if not tweets:
            logging.warning(f"{symbol} için Twitter'da ilgili tweet bulunamadı.")
            return {"score": 0.0, "subjectivity": 0.0}

        total_polarity = 0
        total_subjectivity = 0
        
        for tweet in tweets:
            analysis = TextBlob(tweet.text)
            total_polarity += analysis.sentiment.polarity
            total_subjectivity += analysis.sentiment.subjectivity
            
        # Ortalama skorları hesapla
        avg_polarity = total_polarity / len(tweets)
        avg_subjectivity = total_subjectivity / len(tweets)
        
        logging.info(f"{symbol} için {len(tweets)} tweet analiz edildi. Ortalama Duyarlılık: {avg_polarity:.2f}")
        
        return {"score": round(avg_polarity, 2), "subjectivity": round(avg_subjectivity, 2)}

    except tweepy.errors.TweepyException as e:
        logging.error(f"Twitter API hatası ({symbol}): {e}")
        return {"score": 0.0, "subjectivity": 0.0, "error": f"Twitter API Hatası: {str(e)}"}
    except Exception as e:
        logging.error(f"{symbol} için duyarlılık analizi sırasında genel hata: {e}")
        return {"score": 0.0, "subjectivity": 0.0, "error": str(e)}