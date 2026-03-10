import pandas as pd
import logging
import datetime
from core.data_ingestion import DataManager

class SignalMonitor:
    def __init__(self, config):
        self.config = config
        self.log_path = "logs/trade_log.csv"
        self.data_manager = DataManager(config)

    def check_outcomes(self):
        """Checks active trades in logs against current market prices."""
        try:
            df_logs = pd.read_csv(self.log_path)
        except FileNotFoundError:
            return []

        # We only care about trades that don't have an 'Outcome' yet
        if 'Outcome' not in df_logs.columns:
            df_logs['Outcome'] = 'Pending'

        results = []
        for index, row in df_logs.iterrows():
            if row['Outcome'] != 'Pending' or row['Signal'] == 'None':
                continue

            symbol = row['Symbol']
            price_data = self.data_manager.get_latest_data(symbol)
            if price_data is None: continue

            # Get the highest and lowest prices since the signal was generated
            curr_high = price_data['High'].max()
            curr_low = price_data['Low'].min()
            curr_close = price_data['Close'].iloc[-1]
            
            outcome = "Pending"
            # Logic for BUY Signals
            if "BUY" in row['Signal']:
                if curr_high >= row['TP']: outcome = "✅ TAKE PROFIT"
                elif curr_low <= row['SL']: outcome = "❌ STOP LOSS"
            
            # Logic for SELL Signals
            elif "SELL" in row['Signal']:
                if curr_low <= row['TP']: outcome = "✅ TAKE PROFIT"
                elif curr_high >= row['SL']: outcome = "❌ STOP LOSS"

            if outcome != "Pending":
                df_logs.at[index, 'Outcome'] = outcome
                results.append(f"🔔 **{symbol} Update:** {outcome} at {curr_close}")

        df_logs.to_csv(self.log_path, index=False)
        return results
