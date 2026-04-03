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
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            return yaml.safe_load(content)

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    def run_cycle(self):
        logging.info(f"--- Market Scan Start: {datetime.now().strftime('%H:%M')} ---")
        active_reports = []
        raw_symbols = self.config.get('symbols', [])

        for original_symbol in raw_symbols:
            # Precise Yahoo Mapping
            if any(c in original_symbol for c in ["BTC", "ETH", "SOL"]):
                target_symbol = original_symbol.replace("USD=X", "-USD").replace("USD", "-USD")
            elif "XAGUSD" in original_symbol: target_symbol = "SI=F"
            elif "XAUUSD" in original_symbol: target_symbol = "GC=F"
            else: target_symbol = original_symbol if "=X" in original_symbol else f"{original_symbol}=X"

            logging.info(f"Analysing {original_symbol} (Yahoo: {target_symbol})...")
            df = self.data_manager.get_latest_data(target_symbol)
            
            if df is not None and not df.empty:
                regime = self.regime_detector.classify(df)
                signal = self.strategy.generate_signal(df, regime)

                if signal:
                    risk = self.position_sizer.calculate(df, original_symbol, signal)
                    # Added 'entry', 'sl', and 'tp' to prevent Discord KeyError
                    active_reports.append({
                        "symbol": original_symbol,
                        "type": signal['action'],
                        "entry": round(df['Close'].iloc[-1], 5),
                        "sl": risk.get('sl', 0),
                        "tp": risk.get('tp', 0),
                        "status": "SIGNAL"
                    })
                    logging.info(f"SIGNAL FOUND: {original_symbol} {signal['action']}")

        self.notifier.send_heartbeat(active_reports, "GitHub-Cloud" if self.is_github else "PC-Lagos")
        logging.info("--- Scan Complete ---")

if __name__ == "__main__":
    oracle = DelphiOracleGitHub()
    oracle.run_cycle() if os.getenv('GITHUB_ACTIONS') == 'true' else None
