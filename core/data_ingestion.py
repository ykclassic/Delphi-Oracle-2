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
        Converts internal symbols → Yahoo Finance format
        """

        # Forex pairs
        forex_pairs = {
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
            "USDCAD", "USDCHF", "NZDUSD",
            "EURGBP", "EURJPY", "GBPJPY"
        }

        # Crypto mapping
        crypto_map = {
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "SOLUSD": "SOL-USD"
        }

        # Metals
        metals_map = {
            "XAUUSD": "GC=F",
            "XAGUSD": "SI=F"
        }

        if symbol in forex_pairs:
            return f"{symbol}=X"

        if symbol in crypto_map:
            return crypto_map[symbol]

        if symbol in metals_map:
            return metals_map[symbol]

        # If already formatted (safety)
        if "=" in symbol or "-" in symbol:
            return symbol

        # Fallback (log it explicitly)
        logging.warning(f"Unknown symbol format: {symbol}, using raw")
        return symbol

    def get_latest_data(self, symbol):
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

                    # Normalize datetime column
                    if "Date" in data.columns:
                        data.rename(columns={"Date": "Datetime"}, inplace=True)
                    if "Datetime" not in data.columns:
                        data.rename(columns={data.columns[0]: "Datetime"}, inplace=True)

                    # Ensure sorted
                    data = data.sort_values("Datetime")

                    return data

                logging.warning(f"Attempt {attempt + 1}: Empty data for {symbol}")

            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                time.sleep(2)

        logging.error(f"FAILED to fetch data for {symbol}")
        return None
