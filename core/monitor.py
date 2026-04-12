import pandas as pd
from core.data_ingestion import DataManager


class SignalMonitor:
    def __init__(self, config):
        self.config = config
        self.log_path = "logs/trade_log.csv"
        self.data_manager = DataManager(config)

    def _ensure_schema(self, df):
        """
        Ensures dataframe has required columns (backward compatibility)
        """

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

        # Map OLD columns → NEW
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

        # Rename old columns if they exist
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        # Add missing columns
        for col, default in required_columns.items():
            if col not in df.columns:
                df[col] = default

        # Normalize casing issues
        df["status"] = df["status"].fillna("OPEN")
        df["outcome"] = df["outcome"].fillna("PENDING")

        return df

    def check_outcomes(self):
        try:
            df_logs = pd.read_csv(self.log_path)
        except FileNotFoundError:
            return []

        # 🔥 FIX: Ensure schema BEFORE processing
        df_logs = self._ensure_schema(df_logs)

        updates = []

        for idx, row in df_logs.iterrows():
            if row["status"] != "OPEN":
                continue

            symbol = row["symbol"]
            data = self.data_manager.get_latest_data(symbol)

            if data is None or data.empty:
                continue

            data["Datetime"] = pd.to_datetime(data["Datetime"])
            entry_time = pd.to_datetime(row["entry_time"])

            future_data = data[data["Datetime"] >= entry_time]

            outcome = None
            exit_price = None
            exit_time = None

            for _, candle in future_data.iterrows():
                high = candle["High"]
                low = candle["Low"]

                if "BUY" in row["signal"]:
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

                elif "SELL" in row["signal"]:
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
                    if "BUY" in row["signal"]
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
