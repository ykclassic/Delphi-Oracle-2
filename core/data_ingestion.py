import yfinance as yf
import pandas as pd
import logging

class DataManager:
    def __init__(self, config):
        self.config = config
        self.timeframe = config['timeframe']

    def get_latest_data(self, symbol):
        """Fetches OHLCV data for a given symbol."""
        try:
            # For FX, yfinance uses 'EURUSD=X' format
            ticker = f"{symbol}=X" if "=" not in symbol else symbol
            data = yf.download(ticker, period="1mo", interval=self.timeframe, progress=False)
            
            if data.empty:
                logging.error(f"No data found for {symbol}")
                return None
            
            # Clean column names for consistency
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            return data
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {e}")
            return None
