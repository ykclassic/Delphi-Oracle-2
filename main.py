import os
import yaml
import logging
import pandas as pd
from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

def load_config():
    with open("config/settings.yaml", "r") as f:
        # Resolve environment variables for Discord Webhook
        config = yaml.safe_load(f)
        if config['discord']['webhook_url'] == "${DISCORD_WEBHOOK_URL}":
            config['discord']['webhook_url'] = os.getenv("DISCORD_WEBHOOK_URL")
        return config

def run_bot():
    # 1. Setup Logging & Config
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    config = load_config()
    
    if not config['discord']['webhook_url']:
        logging.error("DISCORD_WEBHOOK_URL not found in environment variables.")
        return

    # 2. Initialize Modules
    data_manager = DataManager(config)
    regime_detector = RegimeDetector()
    news_sentry = NewsSentry(config)
    strategy = TrendStrategy(config)
    position_sizer = PositionSizer(config)
    notifier = DiscordNotifier(config)

    # 3. Execution Flow
    for symbol in config['symbols']:
        logging.info(f"Analyzing {symbol}...")
        
        # Check News first
        if news_sentry.is_market_volatile(symbol):
            logging.warning(f"Skipping {symbol} due to high-impact news.")
            continue
            
        # Get Data
        df = data_manager.get_latest_data(symbol)
        if df is None or len(df) < 50:
            logging.warning(f"Insufficient data for {symbol}.")
            continue
            
        # Detect Regime
        regime = regime_detector.classify(df)
        logging.info(f"Current Market Regime for {symbol}: {regime}")

        # Generate Signal
        signal_type = strategy.generate_signal(df, regime)
        
        # If signal exists, calculate risk and send to Discord
        if signal_type:
            risk_data = position_sizer.calculate(df, symbol, signal_type)
            success = notifier.send_signal(symbol, signal_type, risk_data)
            if success:
                logging.info(f"Successfully sent {signal_type} signal for {symbol} to Discord.")
            else:
                logging.error(f"Failed to send signal for {symbol} to Discord.")
        else:
            logging.info(f"No signal generated for {symbol}.")

if __name__ == "__main__":
    run_bot()
