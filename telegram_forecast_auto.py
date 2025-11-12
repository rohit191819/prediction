"""
telegram_forecast_auto.py
Forecast bot that automatically sends BTCUSDT & ETHUSDT outlooks every 30 minutes,
and replies to /forecast commands on demand.
Educational only – no live trading.
"""

import os, pandas as pd, numpy as np, ta, logging, datetime
from binance.client import Client
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from telegram.ext import JobQueue

# ---------- setup ----------
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # where auto updates go

client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = "https://testnet.binancefuture.com/fapi"
logging.basicConfig(level=logging.INFO)

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVALS = {"15m":"15 min","30m":"30 min","1h":"1 h","1d":"1 d"}

# ---------- indicator logic ----------
def get_df(symbol, interval="15m", limit=150):
    raw = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(raw)
    df.columns = ["t","o","h","l","c","v","ct","qa","tr","tb","tq","i"]
    df["c"] = df["c"].astype(float)
    return df

def analyze(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["c"]).rsi()
    macd = ta.trend.MACD(df["c"])
    df["macd"], df["macds"] = macd.macd(), macd.macd_signal()
    df["ema20"] = df["c"].ewm(span=20).mean()
    df["ema50"] = df["c"].ewm(span=50).mean()
    bb = ta.volatility.BollingerBands(df["c"])
    df["bbh"], df["bbl"] = bb.bollinger_hband(), bb.bollinger_lband()
    return df

def forecast_direction(df):
    rsi, macd, macds, ema20, ema50, close = df.iloc[-1][["rsi","macd","macds","ema20","ema50","c"]]
    score = 0
    if rsi < 30: score += 1
    elif rsi > 70: score -= 1
    score += 1 if macd > macds else -1
    score += 1 if ema20 > ema50 else -1
    if close < df["bbl"].iloc[-1]*1.01: score += 1
    elif close > df["bbh"].iloc[-1]*0.99: score -= 1
    prob_up = (score + 4) / 8
    return prob_up

def build_forecast(sym):
    lines = [f"📊 Forecast for {sym}"]
    for iv,label in INTERVALS.items():
        try:
            df = analyze(get_df(sym, iv))
            p = forecast_direction(df)
            arrow = "↑" if p>0.5 else "↓"
            lines.append(f"{label:<5}: {arrow} {p:.2f}")
        except Exception as e:
            lines.append(f"{label:<5}: ⚠️ {e}")
    return "\n".join(lines)

# ---------- Telegram handlers ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Forecast Bot active.\nUse /forecast BTCUSDT or /forecast ETHUSDT")

async def forecast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sym = ctx.args[0].upper() if ctx.args else "BTCUSDT"
    if sym not in SYMBOLS:
        await update.message.reply_text(f"Allowed symbols: {', '.join(SYMBOLS)}")
        return
    text = build_forecast(sym)
    await update.message.reply_text(text)

# ---------- auto job ----------
async def auto_forecast(ctx: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = [f"🕒 {now} | Auto forecast update"]
    for s in SYMBOLS:
        msg.append(build_forecast(s))
        msg.append("")  # blank line
    text = "\n".join(msg)
    try:
        await ctx.bot.send_message(chat_id=CHAT_ID, text=text)
        logging.info("Auto forecast sent.")
    except Exception as e:
        logging.error(f"Auto forecast send failed: {e}")

# ---------- main ----------
def main():
    app = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('forecast', forecast))

    jobq = app.job_queue
    jobq.run_repeating(auto_forecast, interval=1800, first=10)

    print('🚀 Forecast bot running with 30-min auto updates.')
    app.run_polling()


if __name__ == '__main__':
    main()