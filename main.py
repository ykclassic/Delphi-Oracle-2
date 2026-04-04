import os
import yaml
import logging
from datetime import datetime

# Core Modules
from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

class DelphiOracle:
    def __init__(self):
        self.setup_logging()
        self.is_github = os.getenv('GITHUB_ACTIONS') == 'true'
        self.config = self.load_config()
        
        # Priority: Check Environment Variable directly if config doesn't have it
        if not self.config.get('discord_webhook'):
            self.config['discord_webhook'] = os.getenv('DISCORD_WEBHOOK')
            
        self.notifier = DiscordNotifier(self.config)
        self.data_manager = DataManager(self.config)
        self.regime_detector = RegimeDetector()
        self.strategy = TrendStrategy(self.config)
        self.news_sentry = NewsSentry(self.config)
        self.position_sizer = PositionSizer(self.config)
        
        mode = "GITHUB-MONITOR" if self.is_github else "PC-TRADER"
        logging.info(f"STARTUP: Delphi Oracle {mode} Active.")

    def load_config(self):
        config_path = os.path.join("config", "settings.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Inject env vars into the YAML string
                for key, value in os.environ.items():
                    content = content.replace(f"${{{key}}}", str(value))
                return yaml.safe_load(content)
        except Exception as e:
            logging.error(f"Config mapping error: {e}")
            return {}

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )

    def get_yahoo_symbol(self, symbol):
        if any(c in symbol for c in ["BTC", "ETH", "SOL"]):
            return symbol.replace("USD", "-USD")
        if "XAUUSD" in symbol: return "GC=F"
        if "XAGUSD" in symbol: return "SI=F"
        return f"{symbol}=X" if "=X" not in symbol else symbol

    def run_cycle(self):
        logging.info(f"--- SCAN START: {datetime.now().strftime('%H:%M')} ---")
        dashboard = {}
        
        symbols = self.config.get('symbols', [
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", 
            "EURJPY", "GBPJPY", "XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "SOLUSD"
        ])

        for symbol in symbols:
            fetch_symbol = self.get_yahoo_symbol(symbol) if self.is_github else symbol
            logging.info(f"Fetching data for {fetch_symbol}...")
            
            df = self.data_manager.get_latest_data(fetch_symbol)
            
            if df is None or df.empty:
                dashboard[symbol] = {"status": "Data Error"}
                continue

            regime = self.regime_detector.classify(df)
            signal = self.strategy.generate_signal(df, regime)

            if signal:
                dashboard[symbol] = {"status": f"SIGNAL: {signal['action']}"}
            else:
                dashboard[symbol] = {"status": "Scanning"}

        source = "GitHub-Cloud" if self.is_github else "Lagos-VPS"
        self.notifier.send_heartbeat(dashboard, source)
        logging.info("--- SCAN COMPLETE ---")

if __name__ == "__main__":
    bot = DelphiOracle()
    bot.run_cycle()
