import logging

class PositionSizer:
    def __init__(self, config):
        self.config = config
        self.risk_pct = config.get('risk_per_trade_percent', 1.0)
        # Max allowable spread as a percentage of the total target
        self.max_spread_cost_pct = 0.15 # 15% max

    def calculate(self, df, symbol, signal_data):
        """
        Final Audit: Converts NumPy types, checks Spread Guard, and prepares Risk Packet.
        'signal_data' now comes from the strategy containing {action, entry, sl, tp}
        """
        try:
            # 1. Extract and Clean NumPy types to standard Python floats
            # This fixes the 'np.float64' bug in your Discord screenshot
            entry = float(signal_data['entry'])
            sl = float(signal_data['sl'])
            tp = float(signal_data['tp'])
            action = signal_data['action']

            # 2. Quality Filter: The Spread Guard
            # Uses your existing estimation logic
            estimated_spread = self._estimate_spread(symbol)
            potential_profit = abs(tp - entry)
            
            # Prevent Division by Zero if data is corrupted
            if potential_profit == 0:
                logging.error(f"CRITICAL: Potential profit for {symbol} is zero. Check strategy logic.")
                return None

            if (estimated_spread / potential_profit) > self.max_spread_cost_pct:
                logging.warning(f"🛡️ QUALITY ALERT: Spread on {symbol} too high for target. Aborting.")
                return None 

            # 3. Final Risk Packet
            # Rounding to 5 decimals for Forex (3 for JPY/Gold)
            precision = 3 if any(x in symbol for x in ["JPY", "XAU", "XAG"]) else 5
            
            return {
                "entry": round(entry, precision),
                "sl": round(sl, precision),
                "tp": round(tp, precision),
                "action": action,
                "spread_cost_pct": round((estimated_spread / potential_profit) * 100, 2)
            }

        except Exception as e:
            logging.error(f"Error in PositionSizer: {e}")
            return None

    def _estimate_spread(self, symbol):
        """Estimates typical spreads for 2026 market conditions."""
        spreads = {
            "EURUSD": 0.00012, "GBPUSD": 0.00018, 
            "USDJPY": 0.012, "EURJPY": 0.018, "GBPJPY": 0.025,
            "XAUUSD": 0.35, "XAGUSD": 0.025,  # Added Silver
            "BTCUSD": 15.0, "ETHUSD": 1.2,    # Added Crypto estimates
            "SOLUSD": 0.05
        }
        return spreads.get(symbol, 0.0002)
