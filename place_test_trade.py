from binance.client import Client
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = Client(api_key, api_secret, testnet=True)
client.API_URL = 'https://testnet.binancefuture.com/fapi'

symbol = "BTCUSDT"
leverage = 10
qty = 0.001

# Set leverage
resp = client.futures_change_leverage(symbol=symbol, leverage=leverage)
print("✅ Leverage set:", resp)

# Place a market BUY order
order = client.futures_create_order(
    symbol=symbol,
    side="BUY",
    type="MARKET",
    quantity=qty
)
print("✅ Order placed successfully!")
print(order)
