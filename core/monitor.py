import pandas as pd
from core.data_ingestion import DataManager

class SignalMonitor:
    def __init__(self, config):
        self.config = config
        self.log_path = "logs/trade_log.csv"
        self.data_manager = DataManager(config)

    def check_outcomes(self):
        try:
            df_logs = pd.read_csv(self.log_path)
        except FileNotFoundError:
            return []

        updates = []

        for idx, row in df_logs.iterrows():
            if row["status"] != "OPEN":
                continue

            symbol = row["symbol"]
            data = self.data_manager.get_latest_data(symbol)

            if data is None or data.empty:
                continue

            data['Datetime'] = pd.to_datetime(data['Datetime'])
            entry_time = pd.to_datetime(row["entry_time"])

            # 🔥 CRITICAL FIX: Only use candles AFTER entry
            future_data = data[data['Datetime'] >= entry_time]

            outcome = None
            exit_price = None
            exit_time = None

            for _, candle in future_data.iterrows():
                high = candle["High"]
                low = candle["Low"]

                # 🔥 Correct order: SL first (conservative)
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
                df_logs.at[idx, "outcome"] = outcome
                df_logs.at[idx, "status"] = "CLOSED"
                df_logs.at[idx, "exit_price"] = exit_price
                df_logs.at[idx, "exit_time"] = exit_time

                updates.append(f"{symbol}: {outcome}")

        df_logs.to_csv(self.log_path, index=False)
        return updates
