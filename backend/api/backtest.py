# backend/api/backtest.py

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from core.backtester import Backtester
from core.security import token_required
from tools.utils import log
# Oluşturduğumuz Pydantic modellerini ve hata formatlama fonksiyonunu import ediyoruz
from .schemas import BacktestRunRequest, format_pydantic_errors

backtest_bp = Blueprint('backtest_bp', __name__)

@backtest_bp.route('/run', methods=['POST'])
@token_required
def run_backtest(current_user):
    # 1. Gelen JSON verisini al
    raw_data = request.get_json()
    if not raw_data:
        return jsonify({"error": "Request body must be a valid JSON."}), 400

    try:
        # 2. Veriyi Pydantic modelimizle doğrula ve parse et
        # Eğer veri geçersizse, Pydantic burada bir 'ValidationError' fırlatacaktır.
        validated_data = BacktestRunRequest.model_validate(raw_data)
    
    except ValidationError as e:
        # 3. Doğrulama hatasını yakala ve kullanıcıya anlaşılır bir şekilde geri dön
        log(f"Backtest validation error: {e}", level='warning')
        error_details = format_pydantic_errors(e)
        return jsonify({"error": "Invalid input provided.", "details": error_details}), 400
        
    try:
        # 4. Doğrulanmış ve temizlenmiş veriyi kullan
        # .model_dump() metodu, Pydantic modelini tekrar bir dictionary'e çevirir.
        backtester = Backtester()
        results = backtester.run(
            symbol=validated_data.symbol,
            interval=validated_data.interval,
            start_date=validated_data.start_date,
            end_date=validated_data.end_date,
            preset=validated_data.preset.model_dump()
        )
        
        if results is None:
            return jsonify({"error": "Backtest failed to produce results. Check data availability for the period."}), 500
        
        # Sonuçları JSON'a çevrilebilir hale getiriyoruz.
        # Özellikle balance_history'deki pandas timestamp'leri için bu önemlidir.
        if 'balance_history' in results:
            results['balance_history'] = {str(k): v for k, v in results['balance_history'].items()}

        return jsonify(results), 200

    except Exception as e:
        # 5. Core katmanından gelebilecek beklenmedik hataları yakala
        log(f"Error during backtest run: {e}", level='error')
        return jsonify({"error": "An internal server error occurred while running the backtest."}), 500