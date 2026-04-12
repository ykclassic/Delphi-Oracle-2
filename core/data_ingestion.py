import yfinance as yf
import pandas as pd
import logging
import time


class DataManager:
    def __init__(self, config):
        self.config = config
        self.timeframe = config.get("timeframe", "1h")
        self.cache = {}

    # =========================
    # SYMBOL MAPPING
    # =========================
    def _map_symbol(self, symbol: str) -> str:
        forex = {
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X", "AUDUSD": "AUDUSD=X",
            "USDCAD": "USDCAD=X", "USDCHF": "USDCHF=X",
            "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X",
            "EURJPY": "EURJPY=X", "GBPJPY": "GBPJPY=X"
        }

        metals = {
            "XAUUSD": "GC=F",
            "XAGUSD": "SI=F"
        }

        crypto = {
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
            "SOLUSD": "SOL-USD"
        }

        return forex.get(symbol) or metals.get(symbol) or crypto.get(symbol) or symbol

    # =========================
    # MAIN FETCH
    # =========================
    def get_latest_data(self, symbol: str):
        if symbol in self.cache:
            return self.cache[symbol]

        ticker = self._map_symbol(symbol)
        logging.info(f"Fetching data for {symbol} → {ticker}")

        for attempt in range(3):
            try:
                df = yf.download(
                    ticker,
                    period="1mo",
                    interval=self.timeframe,
                    progress=False,
                    threads=False
                )

                if df is None or df.empty:
                    logging.warning(f"Attempt {attempt+1}: Empty data for {symbol}")
                    time.sleep(2 ** attempt)
                    continue

                df = self._prepare_dataframe(df)

                self.cache[symbol] = df
                return df

            except Exception as e:
                logging.error(f"Attempt {attempt+1} failed for {symbol}: {e}")
                time.sleep(2 ** attempt)

        logging.error(f"FAILED to fetch data for {symbol}")
        return None

    # =========================
    # CRITICAL FIX LAYER
    # =========================
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 🔥 FIX 1: Flatten MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # 🔥 FIX 2: Reset index safely
        df.reset_index(inplace=True)

        # Normalize datetime column
        if "Datetime" not in df.columns:
            if "Date" in df.columns:
                df.rename(columns={"Date": "Datetime"}, inplace=True)

        # 🔥 FIX 3: Ensure Datetime exists
        if "Datetime" not in df.columns:
            raise ValueError("No Datetime column found after reset_index")

        # Convert datetime
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")

        # 🔥 FIX 4: Force UTC consistency
        if df["Datetime"].dt.tz is None:
            df["Datetime"] = df["Datetime"].dt.tz_localize("UTC")
        else:
            df["Datetime"] = df["Datetime"].dt.tz_convert("UTC")

        # 🔥 FIX 5: Force numeric safely
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                # Ensure it's 1D before conversion
                if isinstance(df[col], pd.DataFrame):
                    df[col] = df[col].iloc[:, 0]

                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Drop invalid rows
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

        # Sort properly
        df.sort_values("Datetime", inplace=True)
        df.reset_index(drop=True, inplace=True)

        return df

    # =========================
    # CACHE CONTROL
    # =========================
    def clear_cache(self):
        self.cache = {}
