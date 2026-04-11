import pandas as pd
import datetime
import os
import uuid

class PerformanceLogger:
    def __init__(self, file_path="logs/trade_log.csv"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        if not os.path.exists(self.file_path):
            df = pd.DataFrame(columns=[
                "trade_id",
                "symbol",
                "regime",
                "signal",
                "entry",
                "sl",
                "tp",
                "entry_time",
                "exit_time",
                "exit_price",
                "outcome",
                "status"
            ])
            df.to_csv(self.file_path, index=False)

    def log_trade(self, symbol, regime, signal, risk_data):
        """Logs ONLY valid trades."""
        trade = {
            "trade_id": str(uuid.uuid4()),
            "symbol": symbol,
            "regime": regime,
            "signal": signal,
            "entry": risk_data["entry"],
            "sl": risk_data["sl"],
            "tp": risk_data["tp"],
            "entry_time": datetime.datetime.utcnow().isoformat(),
            "exit_time": None,
            "exit_price": None,
            "outcome": "PENDING",
            "status": "OPEN"
        }

        df = pd.DataFrame([trade])
        df.to_csv(self.file_path, mode='a', header=False, index=False)
