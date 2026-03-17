import pandas as pd
import ta
from strategies.base_strategy import BaseStrategy

class TrendStrategy(BaseStrategy):
    def generate_signal(self, df, regime):
        # 1. Calculate Standard Indicators
        df['ema_fast'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['ema_slow'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
        
        bb = ta.volatility.BollingerBands(df['Close'], window=20)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        
        # ATR is critical for our SL/TP math
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Pull Risk Params from settings.yaml (with fallbacks)
        sl_multiplier = self.config.get('default_stop_loss_atr', 1.5)
        tp_ratio = self.config.get('default_take_profit_ratio', 2.0)

        signal_type = None
        
        # 2. Logic Selection
        # --- REGIME 1: TRENDING ---
        if regime == 1:
            if prev_row['ema_fast'] <= prev_row['ema_slow'] and last_row['ema_fast'] > last_row['ema_slow']:
                if last_row['rsi'] > 50:
                    signal_type = "BUY (Trend)"
            
            elif prev_row['ema_fast'] >= prev_row['ema_slow'] and last_row['ema_fast'] < last_row['ema_slow']:
                if last_row['rsi'] < 50:
                    signal_type = "SELL (Trend)"

        # --- REGIME 0: RANGING ---
        elif regime == 0:
            if last_row['Close'] <= last_row['bb_lower'] and last_row['rsi'] < 35:
                signal_type = "BUY (Mean Reversion)"
            
            elif last_row['Close'] >= last_row['bb_upper'] and last_row['rsi'] > 65:
                signal_type = "SELL (Mean Reversion)"

        # 3. If a signal exists, calculate the Risk Data
        if signal_type:
            entry_price = last_row['Close']
            atr_val = last_row['ATR']
            sl_dist = atr_val * sl_multiplier
            
            if "BUY" in signal_type:
                sl = entry_price - sl_dist
                tp = entry_price + (sl_dist * tp_ratio)
            else: # SELL
                sl = entry_price + sl_dist
                tp = entry_price - (sl_dist * tp_ratio)

            # Return a structured dictionary for the Notifier and Execution modules
            return {
                "action": signal_type,
                "entry": round(entry_price, 5),
                "sl": round(sl, 5),
                "tp": round(tp, 5)
            }

        return None
