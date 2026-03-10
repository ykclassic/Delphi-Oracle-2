import pandas as pd

class PositionSizer:
    def __init__(self, config):
        self.config = config
        self.account_balance = 10000  # Default starting balance
        self.risk_pct = config['risk_per_trade_percent'] / 100

    def calculate(self, df, symbol, signal_type):
        """Calculates ATR-based SL, TP, and Lot Size."""
        # ATR (Average True Range) for volatility
        atr = df['ATR'].iloc[-1]
        current_price = df['Close'].iloc[-1]
        
        # 1. Calculate Stop Loss (SL) distance based on ATR multiplier
        sl_distance = atr * self.config['default_stop_loss_atr']
        
        if "BUY" in signal_type:
            sl_price = current_price - sl_distance
            tp_price = current_price + (sl_distance * self.config['default_take_profit_ratio'])
        else:
            sl_price = current_price + sl_distance
            tp_price = current_price - (sl_distance * self.config['default_take_profit_ratio'])

        # 2. Calculate Lot Size (Risk Amount / SL Distance)
        # Note: In FX, 1 lot = 100,000 units. Calculation depends on pair (e.g., USD/JPY vs EUR/USD).
        risk_amount = self.account_balance * self.risk_pct
        
        # Simplified lot calculation (Assuming 0.0001 pip value for most pairs)
        # Professional bots would use a specific 'pip_value' map here.
        position_size = round(risk_amount / (sl_distance * 100000), 2)
        
        return {
            "entry": round(current_price, 5),
            "sl": round(sl_price, 5),
            "tp": round(tp_price, 5),
            "lots": max(position_size, 0.01) # Minimum lot is 0.01
        }
