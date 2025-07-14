# tools/utils.py
# @author: Memba Co.

def str_to_bool(val: str) -> bool:
    """Metin bir değeri boolean'a çevirir."""
    val = str(val).lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"Geçersiz doğruluk değeri: {val}")

def _get_unified_symbol(symbol_input: str) -> str:
    """
    Her türlü formattaki sembol girdisini ('BTC', 'btcusdt', 'BTC/USDT')
    standart 'BASE/QUOTE' (örn: 'BTC/USDT') formatına dönüştürür.
    """
    if not isinstance(symbol_input, str):
        return "INVALID/SYMBOL"
    
    # Girdideki olası ekleri (örn: ':USDT') temizle
    base = symbol_input.upper().split(':')[0].replace('/USDT', '').replace('USDT', '')
    return f"{base}/USDT"

def _parse_symbol_timeframe_input(input_str: str) -> tuple[str, str]:
    """
    Girdiden sembol ve zaman aralığını daha esnek ve hatasız bir şekilde ayrıştırır.
    Örnek Girdiler: 'BTC/USDT,15m', 'sol 1h', 'eth'
    """
    s = str(input_str).strip()
    # Zaman aralıklarını uzunluklarına göre tersten sıralayarak daha spesifik olanların (örn: '15m')
    # daha genel olanlardan ('1m') önce kontrol edilmesini sağlarız.
    valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    for tf in sorted(valid_timeframes, key=len, reverse=True):
        if s.lower().endswith(tf):
            # Ayırıcı (boşluk, virgül vb.) olup olmadığını kontrol et
            separator_length = 1 if len(s) > len(tf) and s[-len(tf)-1] in [' ', ',', '-', '_'] else 0
            symbol_part = s[:-len(tf)-separator_length]
            # '1M' büyük harf olmalı, diğerleri küçük harf
            timeframe = tf.upper() if tf == '1M' else tf.lower()
            return _get_unified_symbol(symbol_part), timeframe
            
    # Eşleşme bulunamazsa, tüm girdiyi sembol olarak kabul et ve varsayılan zaman aralığını kullan
    return _get_unified_symbol(s), '1h'
