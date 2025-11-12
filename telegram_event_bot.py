"""
telegram_event_bot.py
Professional-style Telegram interface for Futures signals.
Adds inline buttons for manual BUY/SELL confirmation.
"""

import os, pandas as pd
from binance.client import Client
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import logging, datetime

# ------------- Setup -------------
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = "https://testnet.binancefuture.com/fapi"

logging.basicConfig(level=logging.INFO)

SYMBOL = "BTCUSDT"
LOGFILE = "telegram_trades.csv"

# ------------- Helpers -------------
def get_price(symbol=SYMBOL):
    try:
        return float(client.futures_symbol_ticker(symbol=symbol)["price"])
    except Exception as e:
        print("Price fetch error:", e)
        return None

def get_signal(symbol=SYMBOL):
    df = pd.DataFrame(client.futures_klines(symbol=symbol, interval="1m", limit=50))
    df[4] = df[4].astype(float)
    ema5 = df[4].ewm(span=5).mean()
    ema20 = df[4].ewm(span=20).mean()
    if ema5.iloc[-2] < ema20.iloc[-2] and ema5.iloc[-1] > ema20.iloc[-1]:
        return "BUY"
    elif ema5.iloc[-2] > ema20.iloc[-2] and ema5.iloc[-1] < ema20.iloc[-1]:
        return "SELL"
    return "NONE"

def log_decision(side, price):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a") as f:
        f.write(f"{ts},{SYMBOL},{side},{price}\n")

# ------------- Telegram Commands -------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Futures Event Bot (simulation mode)\n"
        "Commands:\n/price  /signal  /logs"
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price()
    if p:
        await update.message.reply_text(f"💰 {SYMBOL} price = {p:.2f} USDT")
    else:
        await update.message.reply_text("⚠️ Cannot fetch price right now.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sig = get_signal()
    price = get_price()
    if sig == "NONE":
        await update.message.reply_text("⏸ No new signal right now.")
        return

    text = f"🔔 {sig} signal detected for {SYMBOL} @ {price:.2f}"
    buttons = [
        [InlineKeyboardButton("BUY", callback_data="BUY"),
         InlineKeyboardButton("SELL", callback_data="SELL"),
         InlineKeyboardButton("IGNORE", callback_data="IGNORE")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    p = get_price()
    log_decision(choice, p)
    await query.edit_message_text(
        text=f"✅ You chose {choice} @ {p:.2f} USDT ({SYMBOL}) — logged."
    )

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(LOGFILE):
        await update.message.reply_text("No decisions logged yet.")
        return
    with open(LOGFILE) as f:
        lines = f.readlines()[-5:]
    await update.message.reply_text("📄 Last logs:\n" + "".join(lines))

# ------------- Main -------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CallbackQueryHandler(button))
    print("🚀 Telegram bot running (simulation/manual mode)")
    app.run_polling()

if __name__ == "__main__":
    main()
