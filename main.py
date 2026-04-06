import os
import time
import yaml
import logging
import pandas as pd
from datetime import datetime, timezone

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
        
        # Priority: Check Environment Variable for Discord Webhook
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
                for key, value in os.environ.items():
                    content = content.replace(f"${{{key}}}", str(value))
                return yaml.safe_load(content)
        except Exception as e:
            logging.error(f"Config mapping error: {e}")
            return {"symbols": ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"]}

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

    def generate_weekly_report(self):
        """Analyzes trade_log.csv and sends a performance summary to Discord."""
        log_path = "trade_log.csv"
        if not os.path.exists(log_path):
            logging.warning("Weekly Report skipped: trade_log.csv not found.")
            return

        try:
            df = pd.read_csv(log_path)
            # Ensure Timestamp is datetime
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Filter for the last 7 days
            one_week_ago = datetime.now() - pd.Timedelta(days=7)
            weekly_df = df[df['Timestamp'] > one_week_ago]
            
            # Calculate Stats
            total_signals = len(weekly_df[weekly_df['Signal'].notna()])
            wins = len(weekly_df[weekly_df['Outcome'].str.contains('TAKE PROFIT', na=False)])
            losses = len(weekly_df[weekly_df['Outcome'].str.contains('STOP LOSS', na=False)])
            win_rate = (wins / max(1, wins + losses)) * 100

            report_data = {
                "Total Signals": f"{total_signals}",
                "Wins ✅": f"{wins}",
                "Losses ❌": f"{losses}",
                "Win Rate 📈": f"{win_rate:.1f}%"
            }

            logging.info("Sending Weekly Performance Report to Discord...")
            # We use a custom source name to trigger a different visual style in the notifier
            self.notifier.send_heartbeat(
                {k: {"status": v} for k, v in report_data.items()}, 
                source="WEEKLY PERFORMANCE SUMMARY 📊"
            )
        except Exception as e:
            logging.error(f"Failed to generate weekly report: {e}")

    def run_cycle(self):
        now = datetime.now(timezone.utc)
        logging.info(f"--- SCAN START: {now.strftime('%H:%M')} UTC ---")
        dashboard = {}
        
        symbols = self.config.get('symbols', [])

        for symbol in symbols:
            fetch_symbol = self.get_yahoo_symbol(symbol) if self.is_github else symbol
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
        
        # --- WEEKLY REPORT TRIGGER ---
        # Trigger on Friday (weekday 4) at 21:00 UTC
        if now.weekday() == 4 and now.hour == 21:
            self.generate_weekly_report()

        logging.info("--- SCAN COMPLETE ---")

if __name__ == "__main__":
    bot = DelphiOracle()
    # Continuous loop for PC, single run for GitHub
    if os.getenv('GITHUB_ACTIONS') == 'true':
        bot.run_cycle()
    else:
        while True:
            try:
                bot.run_cycle()
                time.sleep(900)
            except Exception as e:
                logging.error(f"Cycle Error: {e}")
                time.sleep(60)
