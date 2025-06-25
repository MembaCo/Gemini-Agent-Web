# backend/api/schemas.py

from pydantic import BaseModel, Field, conint, constr
from typing import Dict, Any, Optional

# Pydantic'in doğrulama hatalarını daha temiz bir formata çeviren yardımcı fonksiyon
def format_pydantic_errors(error):
    """Formats Pydantic's ValidationError into a user-friendly dictionary."""
    return {err['loc'][0]: err['msg'] for err in error.errors()}

# Backtest isteği için gönderilecek 'preset' objesinin modelini tanımlıyoruz.
# Bu sayede iç içe geçmiş yapıları bile kolayca doğrulayabiliriz.
class BacktestPreset(BaseModel):
    name: constr(min_length=1)  # constr: string için kısıtlama
    ma_short: Optional[conint(gt=0)] = None  # conint: integer için kısıtlama (0'dan büyük)
    ma_long: Optional[conint(gt=0)] = None
    rsi_period: Optional[conint(gt=0)] = None
    rsi_overbought: Optional[conint(gt=0, lt=100)] = None # 0-100 arası
    rsi_oversold: Optional[conint(gt=0, lt=100)] = None
    
    # İsteğe bağlı olarak başka anahtar-değer çiftlerine izin ver
    class Config:
        extra = 'allow'

# /backtest/run endpoint'ine gelecek olan ana istek modelini tanımlıyoruz.
class BacktestRunRequest(BaseModel):
    symbol: constr(min_length=3)  # Sembol en az 3 karakter olmalı
    interval: constr(min_length=2) # Zaman aralığı en az 2 karakter olmalı
    start_date: constr(pattern=r'^\d{4}-\d{2}-\d{2}$') # YYYY-MM-DD formatını zorunlu kıl
    end_date: constr(pattern=r'^\d{4}-\d{2}-\d{2}$')   # YYYY-MM-DD formatını zorunlu kıl
    preset: BacktestPreset