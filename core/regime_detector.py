import numpy as np
from sklearn.mixture import GaussianMixture

class RegimeDetector:
    def __init__(self, n_regimes=3):
        self.model = GaussianMixture(n_components=n_regimes, random_state=42)

    def classify(self, df):
        """
        Classifies the current market into one of three states:
        0: Low Volatility / Ranging
        1: High Volatility / Trending
        2: Extreme Volatility / News-Driven (Avoid)
        """
        # Feature Engineering for the ML model
        returns = np.log(df['Close'] / df['Close'].shift(1)).dropna()
        volatility = returns.rolling(window=20).std().dropna()
        
        # Combine features into a matrix
        features = np.column_stack([returns.iloc[-100:], volatility.iloc[-100:]])
        
        # Fit and Predict
        self.model.fit(features)
        current_regime = self.model.predict(features)[-1]
        
        return current_regime
