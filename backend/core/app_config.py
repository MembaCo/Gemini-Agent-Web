# core/app_config.py
# @author: Memba Co.
# Bu modül, uygulama ayarlarını veritabanından yükler ve global olarak
# erişilebilir bir sözlükte tutar.

import logging
from database import get_all_settings

# Başlangıçta boş bir sözlük olarak tanımla
settings = {}

def load_config():
    """Ayarları veritabanından yükler veya yeniden yükler."""
    global settings
    logging.info("Uygulama ayarları veritabanından yükleniyor...")
    settings = get_all_settings()
    logging.info("Uygulama ayarları başarıyla yüklendi.")

