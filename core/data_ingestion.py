import yfinance as yf
import pandas as pd
import logging

class DataManager:
    def __init__(self, config):
        self.config = config

    def get_latest_data(self, symbol):
        try:
            # Removed the internal logic that adds '=X' here
            # We now rely on main.py to pass the correct Yahoo symbol
            logging.info(f"Fetching data for {symbol}...")
            df = yf.download(symbol, period="1mo", interval="1h", progress=False)
            
            if df is None or df.empty:
                return None
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            return df
        except Exception as e:
            logging.error(f"Data Fetch Error for {symbol}: {e}")
            return None
