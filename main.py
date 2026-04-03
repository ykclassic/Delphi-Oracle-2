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
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()] 
        )

    def run_cycle(self):
        logging.info(f"--- Market Scan Start: {datetime.now().strftime('%H:%M')} ---")
        active_reports = []

        # List of symbols from config
        raw_symbols = self.config.get('symbols', [])

        for original_symbol in raw_symbols:
            # --- SYMBOL MAPPING LOGIC ---
            # 1. Handle Crypto (No =X)
            if any(crypto in original_symbol for crypto in ["BTC", "ETH", "SOL", "BNB"]):
                target_symbol = original_symbol.replace("USD=X", "-USD").replace("USD", "-USD")
            # 2. Handle Silver
            elif "XAGUSD" in original_symbol:
                target_symbol = "SI=F"
            # 3. Handle Gold
            elif "XAUUSD" in original_symbol:
                target_symbol = "GC=F"
            # 4. Default Forex (Ensure =X exists)
            else:
                target_symbol = original_symbol if "=X" in original_symbol else f"{original_symbol}=X"

            logging.info(f"Analysing {original_symbol} (Yahoo: {target_symbol})...")
            
            # Fetch data using the corrected target_symbol
            df = self.data_manager.get_latest_data(target_symbol)
            
            if df is not None and not df.empty:
                regime = self.regime_detector.classify(df)
                signal = self.strategy.generate_signal(df, regime)

                if signal:
                    risk = self.position_sizer.calculate(df, original_symbol, signal)
                    logging.info(f"SIGNAL FOUND: {original_symbol} {signal['action']}")
                    active_reports.append({
                        "symbol": original_symbol, 
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
