import pandas as pd
from core.data_ingestion import DataManager


class SignalMonitor:
    def __init__(self, config):
        self.config = config
        self.log_path = "logs/trade_log.csv"
        self.data_manager = DataManager(config)

    def _ensure_schema(self, df):
        required_columns = {
            "trade_id": None,
            "symbol": None,
            "regime": None,
            "signal": None,
            "entry": None,
            "sl": None,
            "tp": None,
            "entry_time": None,
            "exit_time": None,
            "exit_price": None,
            "outcome": "PENDING",
            "status": "OPEN",
            "pnl": None,
            "duration_minutes": None
        }

        column_map = {
            "Timestamp": "entry_time",
            "Symbol": "symbol",
            "Regime": "regime",
            "Signal": "signal",
            "Entry": "entry",
            "SL": "sl",
            "TP": "tp",
            "Outcome": "outcome"
        }

        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        for col, default in required_columns.items():
            if col not in df.columns:
                df[col] = default

        # 🔥 CRITICAL FIXES
        df["status"] = df["status"].fillna("OPEN")
        df["outcome"] = df["outcome"].fillna("PENDING")

        # Convert signal to string safely
        df["signal"] = df["signal"].fillna("").astype(str)

        return df

    def _normalize_datetime(self, series):
        dt = pd.to_datetime(series, errors="coerce")

        if dt.dt.tz is None:
            dt = dt.dt.tz_localize("UTC")
        else:
            dt = dt.dt.tz_convert("UTC")

        return dt

    def check_outcomes(self):
        try:
            df_logs = pd.read_csv(self.log_path)
        except FileNotFoundError:
            return []

        df_logs = self._ensure_schema(df_logs)

        df_logs["entry_time"] = self._normalize_datetime(df_logs["entry_time"])

        updates = []

        for idx, row in df_logs.iterrows():

            # Skip invalid rows early
            if row["status"] != "OPEN":
                continue

            if not isinstance(row["signal"], str) or row["signal"] == "":
                continue

            symbol = row["symbol"]
            data = self.data_manager.get_latest_data(symbol)

            if data is None or data.empty:
                continue

            data["Datetime"] = self._normalize_datetime(data["Datetime"])

            entry_time = row["entry_time"]

            future_data = data[data["Datetime"] >= entry_time]

            outcome = None
            exit_price = None
            exit_time = None

            for _, candle in future_data.iterrows():
                high = candle["High"]
                low = candle["Low"]

                # ✅ SAFE STRING CHECK
                signal = row["signal"]

                if "BUY" in signal:
                    if low <= row["sl"]:
                        outcome = "❌ STOP LOSS"
                        exit_price = row["sl"]
                        exit_time = candle["Datetime"]
                        break
                    if high >= row["tp"]:
                        outcome = "✅ TAKE PROFIT"
                        exit_price = row["tp"]
                        exit_time = candle["Datetime"]
                        break

                elif "SELL" in signal:
                    if high >= row["sl"]:
                        outcome = "❌ STOP LOSS"
                        exit_price = row["sl"]
                        exit_time = candle["Datetime"]
                        break
                    if low <= row["tp"]:
                        outcome = "✅ TAKE PROFIT"
                        exit_price = row["tp"]
                        exit_time = candle["Datetime"]
                        break

            if outcome:
                duration = (exit_time - entry_time).total_seconds() / 60

                pnl = (
                    exit_price - row["entry"]
                    if "BUY" in signal
                    else row["entry"] - exit_price
                )

                df_logs.at[idx, "outcome"] = outcome
                df_logs.at[idx, "status"] = "CLOSED"
                df_logs.at[idx, "exit_price"] = exit_price
                df_logs.at[idx, "exit_time"] = exit_time
                df_logs.at[idx, "pnl"] = pnl
                df_logs.at[idx, "duration_minutes"] = duration

                updates.append(f"{symbol}: {outcome}")

        df_logs.to_csv(self.log_path, index=False)
        return updates
