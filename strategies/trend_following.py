import pandas as pd
import ta # Technical Analysis Library

class AlphaStrategy(BaseStrategy):
    def generate_signal(self, df, regime):
        # 1. Calculate Standard Indicators
        # Exponential Moving Averages (EMA)
        df['ema_fast'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['ema_slow'] = ta.trend.ema_indicator(df['Close'], window=50)
        
        # RSI for overbought/oversold
        df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
        
        # Bollinger Bands for volatility/mean reversion
        bb = ta.volatility.BollingerBands(df['Close'], window=20)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()

        # Get latest values
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        # 2. Logic Selection based on Phase 2 Regime
        
        # REGIME 1: TRENDING (Momentum Logic)
        if regime == 1:
            # Bullish: Fast EMA crosses above Slow EMA + RSI > 50
            if prev_row['ema_fast'] <= prev_row['ema_slow'] and last_row['ema_fast'] > last_row['ema_slow']:
                if last_row['rsi'] > 50:
                    return "BUY (Trend)"
            
            # Bearish: Fast EMA crosses below Slow EMA + RSI < 50
            if prev_row['ema_fast'] >= prev_row['ema_slow'] and last_row['ema_fast'] < last_row['ema_slow']:
                if last_row['rsi'] < 50:
                    return "SELL (Trend)"

        # REGIME 0: RANGING (Mean Reversion Logic)
        elif regime == 0:
            # Bullish: Price touches lower Bollinger Band + RSI < 35 (Oversold)
            if last_row['Close'] <= last_row['bb_lower'] and last_row['rsi'] < 35:
                return "BUY (Mean Reversion)"
            
            # Bearish: Price touches upper Bollinger Band + RSI > 65 (Overbought)
            if last_row['Close'] >= last_row['bb_upper'] and last_row['rsi'] > 65:
                return "SELL (Mean Reversion)"

        return None # No high-probability signal found
