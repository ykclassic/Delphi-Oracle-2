import yfinance as yf
import pandas as pd
import logging
import time


class DataManager:
    def __init__(self, config):
        self.config = config
        self.timeframe = config.get("timeframe", "1h")

    def _format_symbol(self, symbol: str) -> str:
        """
        Converts broker symbols → Yahoo Finance format
        """

        # Forex pairs → EURUSD=X
        forex_pairs = [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
            "USDCAD", "USDCHF", "NZDUSD",
            "EURGBP", "EURJPY", "GBPJPY"
        ]

        if symbol in forex_pairs:
            return f"{symbol}=X"

        # Gold
        if symbol == "XAUUSD":
            return "GC=F"

        # Silver
        if symbol == "XAGUSD":
            return "SI=F"

        # Default fallback
        return symbol

    def get_latest_data(self, symbol):
        """
        Fetch OHLCV data safely
        """
        ticker_str = self._format_symbol(symbol)

        logging.info(f"Fetching data for {symbol} → {ticker_str}")

        for attempt in range(3):
            try:
                ticker = yf.Ticker(ticker_str)

                data = ticker.history(
                    period="1mo",
                    interval=self.timeframe
                )

                if data is not None and not data.empty:
                    data = data.reset_index()

                    # Normalize column naming
                    if "Date" in data.columns:
                        data.rename(columns={"Date": "Datetime"}, inplace=True)

                    return data

                logging.warning(f"Attempt {attempt+1}: Empty data for {symbol}")

            except Exception as e:
                logging.error(f"Attempt {attempt+1} failed for {symbol}: {e}")
                time.sleep(2)

        logging.error(f"FAILED to fetch data for {symbol}")
        return None
