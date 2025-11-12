from binance.client import Client
from dotenv import load_dotenv
import pandas as pd, time, os, requests, datetime

# ---- configuration ----
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID", "")
SYMBOL = "BTCUSDT"
EMA_FAST, EMA_SLOW = 5, 20
QTY = 0.001
SL_RATIO, TP_RATIO = 0.005, 0.01
LEVERAGE = 10
MAX_LOSSES = 3
MAX_DRAWDOWN = 0.1
SLEEP = 30
EQUITY = 1000.0
PEAK = EQUITY
LOSSES = 0

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT: return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      data={"chat_id": TG_CHAT, "text": msg}, timeout=5)
    except Exception as e: print("TG fail:", e)

client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = "https://testnet.binancefuture.com/fapi"

def get_klines(retries=3):
    """Fetch klines with retry + longer timeout"""
    for attempt in range(retries):
        try:
            k = client.futures_klines(symbol=SYMBOL, interval="1m", limit=50)
            df = pd.DataFrame(k, columns=range(12))
            df[4] = df[4].astype(float)
            return df
        except Exception as e:
            print(f"⚠️ get_klines failed ({attempt+1}/{retries}): {e}")
            time.sleep(5)
    print("❌ Could not fetch klines after retries.")
    return pd.DataFrame(columns=[4])


def trade_sim(side, price):
    global EQUITY, LOSSES, PEAK
    if side=="BUY": exitp=price*(1+TP_RATIO); stopp=price*(1-SL_RATIO)
    else: exitp=price*(1-TP_RATIO); stopp=price*(1+SL_RATIO)
    hit = "TP" if abs(TP_RATIO)>abs(SL_RATIO) else "SL"
    pnl = (exitp-price)*LEVERAGE*(1 if side=="BUY" else -1)*100
    EQUITY += pnl; PEAK=max(PEAK,EQUITY)
    LOSSES = LOSSES+1 if pnl<0 else 0
    print(f"{datetime.datetime.now()} | {side} | {pnl:.2f} | Eq:{EQUITY:.2f}")
    send_tg(f"{side} simulated | PnL {pnl:.2f} | Eq {EQUITY:.2f}")

print("🚀 Bot started — simulated EMA with risk control")

while True:
    df=get_klines()
    emaf=df[4].ewm(span=EMA_FAST,adjust=False).mean()
    emal=df[4].ewm(span=EMA_SLOW,adjust=False).mean()
    if emaf.iloc[-2]<emal.iloc[-2] and emaf.iloc[-1]>emal.iloc[-1]:
        side="BUY"
    elif emaf.iloc[-2]>emal.iloc[-2] and emaf.iloc[-1]<emal.iloc[-1]:
        side="SELL"
    else:
        side=None
    if side:
        price=float(client.futures_symbol_ticker(symbol=SYMBOL)["price"])
        trade_sim(side,price)
        dd=(PEAK-EQUITY)/PEAK
        if LOSSES>=MAX_LOSSES or dd>=MAX_DRAWDOWN:
            send_tg("Kill switch hit. Bot stopping.")
            print("Kill switch hit. Bot stopping.")
            break
    else:
        print(datetime.datetime.now(),"| no signal | Eq:",EQUITY)
    time.sleep(SLEEP)
