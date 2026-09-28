import time
import os
import threading
import pandas as pd
import requests
from flask import Flask

# ==========================================
# SERVIDOR WEB FLASK (Mantiene Replit despierto)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot MACD NEAR/USDT activo y escuchando 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# CONFIGURACIÓN SEGURA Y PRIVADA
# ==========================================
SYMBOL = "NEARUSDT"
TIMEFRAMES = ["15m", "1h"]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

last_alerted_candle = {tf: None for tf in TIMEFRAMES}

def send_telegram(message):
    """Envía notificación directa a Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"Respuesta Telegram: {res.status_code}")
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def check_macd_for_timeframe(interval):
    """Consulta los datos públicos de Binance (Servidor Vision) y calcula el MACD"""
    global last_alerted_candle

    url = f"https://data-api.binance.vision/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit=50"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"[{interval}] Error API Binance: HTTP {response.status_code}")
            return
        res = response.json()
    except Exception as e:
        print(f"[{interval}] Error de conexión: {e}")
        return

    # Estructurar velas
    df = pd.DataFrame(res, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])
    df['close'] = df['close'].astype(float)

    # Cálculo MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    # Evaluamos la última vela CERRADA por completo
    candle_time = df['open_time'].iloc[-2]

    if last_alerted_candle[interval] == candle_time:
        return

    prev_macd = macd_line.iloc[-3]
    prev_signal = signal_line.iloc[-3]
    curr_macd = macd_line.iloc[-2]
    curr_signal = signal_line.iloc[-2]
    close_price = df['close'].iloc[-2]

    # Condición de Cruce Alcista
    is_bullish_cross = (prev_macd <= prev_signal) and (curr_macd > curr_signal)

    if is_bullish_cross:
        msg = (
            f"🚨 *ALERTA MACD ALCISTA - {SYMBOL}* 🚨\n\n"
            f"⏱️ *Temporalidad:* `{interval}`\n"
            f"📈 *Cruce Alcista Confirmado*\n"
            f"💵 *Precio Cierre Vela:* `${close_price:.3f}`\n"
            f"📊 *Línea MACD:* `{curr_macd:.4f}`\n"
            f"📊 *Línea Signal:* `{curr_signal:.4f}`\n\n"
            f"👉 Revisa el gráfico en Binance para analizar tu entrada LONG."
        )
        print(f"[{interval}] ¡CRUCE ALCISTA DETECTADO! Enviando alerta...")
        send_telegram(msg)
        last_alerted_candle[interval] = candle_time
    else:
        print(f"[{interval}] Vela cerrada analizada: Sin cruce alcista.")

def bot_loop():
    print("🚀 Bot Monitor MACD (15m y 1h) iniciado correctamente...")
    send_telegram("✅ *Bot Monitor MACD 24/7 activado en tu servidor.*")
    while True:
        for tf in TIMEFRAMES:
            check_macd_for_timeframe(tf)
            time.sleep(2)
        time.sleep(30)

if __name__ == "__main__":
    # Iniciar servidor web Flask en segundo plano
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Iniciar bucle principal del bot
    bot_loop()