import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

class RegimeDetector:
    def __init__(self, n_regimes=3):
        self.model = GaussianMixture(n_components=n_regimes, random_state=42, n_init=10)

    def classify(self, df):
        """
        Refined classification using normalized volatility and momentum.
        """
        # 1. Feature Engineering
        returns = np.log(df['Close'] / df['Close'].shift(1)).fillna(0)
        volatility = returns.rolling(window=14).std().fillna(0)
        range_pct = (df['High'] - df['Low']) / df['Close']
        
        # 2. Prepare Feature Matrix (Last 200 periods for context)
        features = np.column_stack([
            returns.tail(200).values, 
            volatility.tail(200).values,
            range_pct.tail(200).values
        ])
        
        # 3. Fit and Predict
        self.model.fit(features)
        regimes = self.model.predict(features)
        current_regime = regimes[-1]
        
        # 4. Map the ML output to logical categories
        # We sort by volatility so 0=Low, 1=Medium, 2=High
        # (This is a simplified mapping for stability)
        mean_vols = [features[regimes == i, 1].mean() for i in range(3)]
        sorted_regimes = np.argsort(mean_vols)
        
        # Return: 0 (Range), 1 (Trend), 2 (Chaos)
        if current_regime == sorted_regimes[0]: return 0
        if current_regime == sorted_regimes[1]: return 1
        return 2
