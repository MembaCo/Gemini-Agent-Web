# backend/api/schemas.py

from pydantic import BaseModel, Field
from typing import Optional

# Pydantic'in doğrulama hatalarını daha temiz bir formata çeviren yardımcı fonksiyon
def format_pydantic_errors(error):
    """Formats Pydantic's ValidationError into a user-friendly dictionary."""
    return {err['loc'][0]: err['msg'] for err in error.errors()}

# Backtest isteği için gönderilecek 'preset' objesinin modelini tanımlıyoruz.
# Bu sayede iç içe geçmiş yapıları bile kolayca doğrulayabiliriz.
class BacktestPreset(BaseModel):
    name: str = Field(min_length=1)
    ma_short: Optional[int] = Field(default=None, gt=0)
    ma_long: Optional[int] = Field(default=None, gt=0)
    rsi_period: Optional[int] = Field(default=None, gt=0)
    rsi_overbought: Optional[int] = Field(default=None, gt=0, lt=100)
    rsi_oversold: Optional[int] = Field(default=None, gt=0, lt=100)
    
    # YENİ: Backtest'e özel risk yüzdesi eklendi
    RISK_PER_TRADE_PERCENT: Optional[float] = Field(default=None, gt=0, description="Percentage of balance to risk per trade for this backtest.")

    # İsteğe bağlı olarak başka anahtar-değer çiftlerine izin ver
    class Config:
        extra = 'allow'

# /backtest/run endpoint'ine gelecek olan ana istek modelini tanımlıyoruz.
class BacktestRunRequest(BaseModel):
    symbol: str = Field(min_length=3)
    interval: str = Field(min_length=2)
    start_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    preset: BacktestPreset