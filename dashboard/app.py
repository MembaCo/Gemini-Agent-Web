# dashboard/app.py
# @author: Memba Co.

from flask import Flask, render_template, jsonify, request
import database
import json

# Bu fonksiyon, ana uygulama mantığını içeren bot_actions sözlüğünü alarak
# Flask uygulamasını oluşturur. Bu yapıya "Application Factory" denir.
def create_app(bot_actions: dict):
    app = Flask(__name__)
    
    # bot_actions sözlüğünü Flask'ın uygulama contexte'ine ekliyoruz.
    # Böylece her request'te bu fonksiyonlara erişebiliriz.
    app.config['BOT_ACTIONS'] = bot_actions

    @app.route('/')
    def index():
        """Ana Pano sayfasını render eder."""
        # Bu kısımda veritabanından veri çekip ana sayfaya gönderebilirsiniz.
        # Örneğin: işlem geçmişi, PNL istatistikleri vb.
        # return render_template('index.html', trade_history=database.get_trade_history())
        return "Gemini Trading Agent Web Arayüzü" # Şimdilik basit bir mesaj

    # --- API ENDPOINTS (Web arayüzünün beyni) ---
    
    @app.route('/api/status')
    def api_status():
        """Anlık pozisyon durumunu JSON formatında döner."""
        get_status_func = app.config['BOT_ACTIONS'].get('get_status')
        if not get_status_func:
            return jsonify({"error": "Status function not available"}), 500
            
        # HTML formatlı çıktıyı sade metine çevirelim (isteğe bağlı)
        status_html = get_status_func()
        status_text = status_html.replace('<b>', '').replace('</b>', '')
        
        return jsonify({"status_text": status_text})

    @app.route('/api/positions')
    def api_get_positions():
        """Veritabanında yönetilen tüm pozisyonları JSON olarak döner."""
        positions = database.get_all_positions()
        return jsonify(positions)

    @app.route('/api/analyze', methods=['POST'])
    def api_analyze():
        """Yeni bir sembol analizi tetikler."""
        data = request.json
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', '15m')
        
        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400
        
        analyze_func = app.config['BOT_ACTIONS'].get('analyze')
        analysis_result = analyze_func(
            symbol=symbol,
            entry_tf=timeframe,
            use_mta=True # veya config'den oku
        )
        
        if not analysis_result:
            return jsonify({"error": "Analysis failed"}), 500
        
        return jsonify(analysis_result)

    @app.route('/api/positions/<symbol>/reanalyze', methods=['POST'])
    def api_reanalyze(symbol):
        """Belirli bir pozisyonu yeniden analiz eder."""
        reanalyze_func = app.config['BOT_ACTIONS'].get('reanalyze')
        position = next((p for p in database.get_all_positions() if p['symbol'] == symbol), None)
        
        if not position:
            return jsonify({"error": "Position not found"}), 404
            
        report_json_str = reanalyze_func(position)
        report_data = json.loads(report_json_str)
        
        return jsonify(report_data)
        
    @app.route('/api/positions/<symbol>/close', methods=['POST'])
    def api_close_position(symbol):
        """Belirli bir pozisyonu kapatır."""
        close_func = app.config['BOT_ACTIONS'].get('close')
        position = next((p for p in database.get_all_positions() if p['symbol'] == symbol), None)

        if not position:
            return jsonify({"error": "Position not found"}), 404
            
        result_message = close_func(
            position,
            from_auto=True,
            close_reason="WEB_MANUAL",
            send_notification=True
        )
        
        return jsonify({"message": result_message})
        
    return app