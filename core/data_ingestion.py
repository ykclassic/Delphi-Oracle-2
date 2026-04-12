import yfinance as yf
import pandas as pd
import logging
import time


class DataManager:
    """
    Institutional-grade Data Manager

    Features:
    - Symbol normalization (Forex, Metals, Crypto)
    - In-memory caching (1 fetch per symbol per cycle)
    - Retry with exponential backoff
    - UTC datetime normalization
    - Schema standardization
    """

    def __init__(self, config):
        self.config = config
        self.timeframe = config.get("timeframe", "1h")
        self.cache = {}  # 🔥 Critical: Prevent duplicate fetches

    # =========================
    # SYMBOL MAPPING ENGINE
    # =========================
    def _map_symbol(self, symbol: str) -> str:
        """
        Maps internal symbols → Yahoo Finance tickers
        """

        # Forex pairs
        forex_map = {
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X",
            "AUDUSD": "AUDUSD=X",
            "USDCAD": "USDCAD=X",
            "USDCHF": "USDCHF=X",
            "NZDUSD": "NZDUSD=X",
            "EURGBP": "EURGBP=X",
            "EURJPY": "EURJPY=X",
            "GBPJPY": "GBPJPY=X",
        }

        # Metals (use futures for reliability)
        metals_map = {
            "XAUUSD": "GC=F",   # Gold
            "XAGUSD": "SI=F",   # Silver
        }

        # Crypto
        crypto_map = {
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "SOLUSD": "SOL-USD",
        }

        if symbol in forex_map:
            return forex_map[symbol]
        if symbol in metals_map:
            return metals_map[symbol]
        if symbol in crypto_map:
            return crypto_map[symbol]

        # Fallback (attempt generic Yahoo format)
        return symbol

    # =========================
    # DATA FETCH ENGINE
    # =========================
    def get_latest_data(self, symbol: str) -> pd.DataFrame | None:
        """
        Fetch OHLCV data with:
        - caching
        - retry logic
        - schema normalization
        """

        # 🔥 CACHE HIT (major performance optimization)
        if symbol in self.cache:
            logging.debug(f"[CACHE HIT] {symbol}")
            return self.cache[symbol]

        ticker = self._map_symbol(symbol)
        logging.info(f"Fetching data for {symbol} → {ticker}")

        max_retries = 3
        backoff = 2

        for attempt in range(max_retries):
            try:
                df = yf.download(
                    ticker,
                    period="1mo",
                    interval=self.timeframe,
                    progress=False,
                    threads=False  # safer in CI
                )

                # ❌ No data
                if df is None or df.empty:
                    logging.warning(f"Attempt {attempt+1}: Empty data for {symbol}")
                    time.sleep(backoff ** attempt)
                    continue

                df = self._standardize_dataframe(df)

                # 🔥 STORE IN CACHE
                self.cache[symbol] = df

                return df

            except Exception as e:
                logging.error(f"Attempt {attempt+1} failed for {symbol}: {e}")
                time.sleep(backoff ** attempt)

        logging.error(f"FAILED to fetch data for {symbol}")
        return None

    # =========================
    # DATA STANDARDIZATION
    # =========================
    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures consistent structure across all assets
        Output columns:
        Datetime, Open, High, Low, Close, Volume
        """

        df = df.copy()

        # Reset index → bring datetime into column
        df.reset_index(inplace=True)

        # Normalize datetime column name
        if "Datetime" not in df.columns:
            if "Date" in df.columns:
                df.rename(columns={"Date": "Datetime"}, inplace=True)

        # Convert to datetime
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")

        # 🔥 CRITICAL FIX: Normalize timezone
        if df["Datetime"].dt.tz is None:
            df["Datetime"] = df["Datetime"].dt.tz_localize("UTC")
        else:
            df["Datetime"] = df["Datetime"].dt.tz_convert("UTC")

        # Ensure numeric columns
        numeric_cols = ["Open", "High", "Low", "Close", "Volume"]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Drop bad rows
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

        # Sort chronologically
        df.sort_values("Datetime", inplace=True)

        # Reset index cleanly
        df.reset_index(drop=True, inplace=True)

        return df

    # =========================
    # CACHE CONTROL (OPTIONAL)
    # =========================
    def clear_cache(self):
        """Clears in-memory cache (useful between cycles if needed)"""
        self.cache = {}

    def get_cached_symbols(self):
        """Returns list of cached symbols (debugging/monitoring)"""
        return list(self.cache.keys())
