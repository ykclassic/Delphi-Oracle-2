import pandas as pd
import yfinance as yf
import joblib
import os
import logging
from sklearn.ensemble import RandomForestClassifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def prepare_features(df):
    """Extracts the same features used in the live bot."""
    data = df.copy()
    data['returns'] = data['Close'].pct_change()
    data['volatility'] = data['returns'].rolling(window=10).std()
    
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    data['target'] = (data['Close'].shift(-4) > data['Close']).astype(int)
    return data.dropna()

def retrain_models(symbols):
    """Builds a fresh ML model for the upcoming trading week."""
    logging.info("Starting Weekend Retraining Protocol...")
    os.makedirs("models", exist_ok=True)
    
    for symbol in symbols:
        try:
            logging.info(f"Fetching 60 days of fresh data for {symbol}...")
            # We use 60 days of 1-hour data to capture recent market memory
            df = yf.download(symbol, period="60d", interval="1h", progress=False)
            
            if df.empty:
                continue
                
            features = prepare_features(df)
            X = features[['returns', 'volatility', 'rsi']]
            y = features['target']
            
            model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
            model.fit(X, y)
            
            model_path = f"models/{symbol}_rf_model.pkl"
            joblib.dump(model, model_path)
            logging.info(f"✅ {symbol} model upgraded and saved to {model_path}.")
            
        except Exception as e:
            logging.error(f"Failed to retrain {symbol}: {e}")

if __name__ == "__main__":
    # Add all the symbols your bot currently trades
    target_symbols = ["EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X"]
    retrain_models(target_symbols)
