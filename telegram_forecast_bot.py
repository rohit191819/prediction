"""
telegram_forecast_bot.py
Professional Futures-data Telegram bot (educational).
Analyses BTCUSDT & ETHUSDT using EMA, RSI, MACD, Bollinger Bands
on 15m / 30m / 1h / 1d timeframes.
"""

import os, pandas as pd, numpy as np
from binance.client import Client
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import ta, logging

load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TOKEN = os.getenv("TELEGRAM_TOKEN")

client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = "https://testnet.binancefuture.com/fapi"
logging.basicConfig(level=logging.INFO)

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVALS = {"15m":"15 min","30m":"30 min","1h":"1 hour","1d":"1 day"}

# ---------- indicator helpers ----------
def get_df(symbol, interval="15m", limit=150):
    data = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(data)
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
    if macd > macds: score += 1
    else: score -= 1
    if ema20 > ema50: score += 1
    else: score -= 1
    if close < df["bbl"].iloc[-1]*1.01: score += 1
    elif close > df["bbh"].iloc[-1]*0.99: score -= 1
    prob_up = (score + 4) / 8
    return prob_up

# ---------- telegram commands ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Forecast Bot ready.\nUse /forecast BTCUSDT or /forecast ETHUSDT")

async def forecast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    sym = args[0].upper() if args else "BTCUSDT"
    if sym not in SYMBOLS:
        await update.message.reply_text(f"Allowed: {', '.join(SYMBOLS)}")
        return

    text = [f"📊 Forecast for {sym} (Testnet data)"]
    for iv, label in INTERVALS.items():
        try:
            df = analyze(get_df(sym, iv))
            p = forecast_direction(df)
            arrow = "↑" if p>0.5 else "↓"
            text.append(f"{label:<6}: {arrow} {p:.2f}")
        except Exception as e:
            text.append(f"{label:<6}: ⚠️ {e}")
    await update.message.reply_text("\n".join(text))

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands: /forecast BTCUSDT | /forecast ETHUSDT")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("forecast", forecast))
    app.add_handler(CommandHandler("help", help_cmd))
    print("🚀 Forecast bot running – check Telegram")
    app.run_polling()

if __name__ == "__main__":
    main()
