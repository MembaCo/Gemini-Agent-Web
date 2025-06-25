# ==============================================================================
# File: backend/core/cache_manager.py
# @author: Memba Co.
# ==============================================================================
# Bu modül, sık istenen veriler için basit bir bellek-içi (in-memory)
# önbellekleme mekanizması sağlar. Özellikle teknik analiz verileri gibi
# sık çekilen ama anlık değişmeyen veriler için API kullanımını azaltır.
# ==============================================================================

import time
import logging

# Önbellek verilerini ve yaşam sürelerini tutacak olan sözlükler.
_cache = {}
_cache_ttl = 180  # Saniye cinsinden önbellek yaşam süresi (TTL), örn: 3 dakika

def get(key: str):
    """
    Önbellekten bir anahtara karşılık gelen veriyi alır.
    Veri mevcutsa ve yaşam süresi (TTL) dolmamışsa veriyi döndürür.
    Aksi takdirde None döndürür.
    """
    if key not in _cache:
        return None

    data, timestamp = _cache[key]
    
    if (time.time() - timestamp) > _cache_ttl:
        # Yaşam süresi dolmuş, anahtarı önbellekten temizle
        logging.info(f"Önbellek süresi doldu: '{key}'")
        del _cache[key]
        return None
        
    logging.info(f"Önbellekten okundu: '{key}'")
    return data

def set(key: str, value: any):
    """
    Bir anahtar/değer çiftini mevcut zaman damgasıyla birlikte önbelleğe ekler.
    """
    logging.info(f"Önbelleğe yazıldı: '{key}'")
    _cache[key] = (value, time.time())