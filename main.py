import os
import time
import yaml
import logging
from datetime import datetime

# Conditional import for MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

class DelphiOracleGitHub:
    def __init__(self):
        self.setup_logging()
        self.is_github = os.getenv('GITHUB_ACTIONS') == 'true'
        self.config = self.load_config()
        
        self.notifier = DiscordNotifier(self.config)
        self.data_manager = DataManager(self.config)
        self.regime_detector = RegimeDetector()
        self.strategy = TrendStrategy(self.config)
        self.news_sentry = NewsSentry(self.config)
        self.position_sizer = PositionSizer(self.config)
        
        # Removed emojis from string to prevent UnicodeEncodeError in Windows CMD
        mode = "GITHUB-MONITOR" if self.is_github else "LOCAL-TRADER"
        logging.info(f"Initialised: {self.config.get('bot_name')} in {mode} mode.")

    def load_config(self):
        config_path = os.path.join("config", "settings.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
                for key, value in os.environ.items():
                    content = content.replace(f"${{{key}}}", value)
                return yaml.safe_load(content)
        except Exception as e:
            logging.error(f"Config Error: {e}")
            raise

    def setup_logging(self):
        # Explicitly set the encoding for the FileHandler to utf-8
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()] 
        )

    def run_cycle(self):
        logging.info(f"--- Market Scan Start: {datetime.now().strftime('%H:%M')} ---")
        active_reports = []

        # Fix Yahoo Finance Symbols before fetching
        raw_symbols = self.config.get('symbols', [])
        corrected_symbols = []
        for s in raw_symbols:
            if "XAGUSD" in s: corrected_symbols.append("SI=F") # Silver
            elif "BTCUSD" in s: corrected_symbols.append("BTC-USD")
            elif "ETHUSD" in s: corrected_symbols.append("ETH-USD")
            elif "SOLUSD" in s: corrected_symbols.append("SOL-USD")
            else: corrected_symbols.append(s)

        for symbol in corrected_symbols:
            logging.info(f"Analysing {symbol}...")
            df = self.data_manager.get_latest_data(symbol)
            
            if df is not None and not df.empty:
                regime = self.regime_detector.classify(df)
                signal = self.strategy.generate_signal(df, regime)

                if signal:
                    risk = self.position_sizer.calculate(df, symbol, signal)
                    logging.info(f"SIGNAL FOUND: {symbol} {signal['action']}")
                    active_reports.append({
                        "symbol": symbol, 
                        "type": signal['action'], 
                        "acc": "SIMULATION" if self.is_github else "LIVE",
                        "status": "SIGNAL"
                    })

        self.notifier.send_heartbeat(active_reports, "GitHub-Cloud" if self.is_github else "PC-Lagos")
        logging.info("--- Scan Complete ---")

if __name__ == "__main__":
    oracle = DelphiOracleGitHub()
    if os.getenv('GITHUB_ACTIONS') == 'true':
        oracle.run_cycle()
    else:
        while True:
            oracle.run_cycle()
            time.sleep(900)
