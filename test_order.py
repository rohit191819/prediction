from binance.client import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

# Connect to Binance Futures TESTNET
client = Client(api_key, api_secret, testnet=True)
client.API_URL = 'https://testnet.binancefuture.com/fapi'

# Get the latest price for BTCUSDT Futures
ticker = client.futures_symbol_ticker(symbol="BTCUSDT")
print("✅ Connected to Binance Futures TESTNET")
print("BTCUSDT price:", ticker["price"])
