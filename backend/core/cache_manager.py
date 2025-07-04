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

# Önbellek verilerini, zaman damgalarını ve yaşam sürelerini tutacak olan sözlük.
_cache = {}
# Varsayılan genel TTL, eğer özel bir süre belirtilmezse kullanılır.
DEFAULT_CACHE_TTL = 180

def get(key: str):
    """
    Önbellekten bir anahtara karşılık gelen veriyi alır.
    Veri mevcutsa ve yaşam süresi (TTL) dolmamışsa veriyi döndürür.
    Aksi takdirde None döndürür.
    """
    if key not in _cache:
        return None

    # --- DÜZELTME BAŞLANGICI ---
    # Artık her kaydın kendi TTL değerini de saklıyoruz.
    data, timestamp, ttl = _cache[key]
    
    # Her kaydın kendi TTL değerine göre kontrol yapılıyor.
    if (time.time() - timestamp) > ttl:
        # Yaşam süresi dolmuş, anahtarı önbellekten temizle
        logging.debug(f"Önbellek süresi doldu: '{key}'")
        del _cache[key]
        return None
    # --- DÜZELTME SONU ---
        
    logging.debug(f"Önbellekten okundu: '{key}'")
    return data

def set(key: str, value: any, ttl: int = None):
    """
    Bir anahtar/değer çiftini, belirtilen yaşam süresi (ttl) ile birlikte
    önbelleğe ekler. Eğer ttl belirtilmezse, varsayılan TTL kullanılır.
    """
    # --- DÜZELTME BAŞLANGICI ---
    # Fonksiyon artık 'ttl' adında bir argüman kabul ediyor.
    # Eğer bir ttl sağlanmazsa, varsayılan değeri kullan.
    effective_ttl = ttl if ttl is not None else DEFAULT_CACHE_TTL
    
    logging.debug(f"Önbelleğe yazıldı: '{key}' (TTL: {effective_ttl}s)")
    # Veriyle birlikte timestamp ve TTL'i de sakla.
    _cache[key] = (value, time.time(), effective_ttl)
    # --- DÜZELTME SONU ---