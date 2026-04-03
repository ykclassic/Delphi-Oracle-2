 import os
import time
import yaml
import logging
from datetime import datetime

# Import the native PC MT5 library
import MetaTrader5 as mt5

# Import your core Delphi Oracle modules
from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

class DelphiOraclePC:
    def __init__(self):
        self.setup_logging()
        self.config = self.load_config()
        
        # Initialize Core Components
        self.notifier = DiscordNotifier(self.config)
        self.data_manager = DataManager(self.config)
        self.regime_detector = RegimeDetector()
        self.strategy = TrendStrategy(self.config)
        self.news_sentry = NewsSentry(self.config)
        self.position_sizer = PositionSizer(self.config)
        
        logging.info(f"🔮 {self.config.get('bot_name', 'Delphi Oracle')} v{self.config.get('version', '1.2')} Initialized.")

    def load_config(self):
        """Loads settings with UTF-8 encoding to prevent UnicodeDecodeErrors."""
        try:
            # Explicitly setting encoding='utf-8' fixes the 'charmap' codec error
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                content = f.read()
                # Replaces ${VAR} with actual env variables if present (useful for GitHub Secrets)
                for key, value in os.environ.items():
                    content = content.replace(f"${{{key}}}", value)
                return yaml.safe_load(content)
        except FileNotFoundError:
            logging.error("❌ config/settings.yaml not found!")
            raise
        except Exception as e:
            logging.error(f"❌ Error loading config: {e}")
            raise

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler("delphi_oracle.log"), 
                logging.StreamHandler()
            ]
        )

    def connect_account(self, account_cfg):
        """Standard MT5 Login for PC."""
        if not mt5.initialize():
            logging.error("MT5 Initialize failed. Ensure MT5 Terminal is open.")
            return False
        
        authorized = mt5.login(
            int(account_cfg['login']), 
            password=account_cfg['password'], 
            server=account_cfg['server']
        )
        return authorized

    def execute_on_mt5(self, symbol, signal, risk, account_cfg):
        """Native PC Execution Logic."""
        suffix = account_cfg.get('symbol_suffix', "")
        mt5_symbol = f"{symbol}{suffix}"

        # Ensure symbol is visible
        mt5.symbol_select(mt5_symbol, True)

        order_type = mt5.ORDER_TYPE_BUY if "BUY" in signal['action'].upper() else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(mt5_symbol)
        
        if tick is None:
            logging.error(f"❌ Could not get tick info for {mt5_symbol}")
            return False

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_symbol,
            "volume": float(risk['lots']),
            "type": order_type,
            "price": price,
            "sl": float(risk['sl']),
            "tp": float(risk['tp']),
            "magic": 202603,
            "comment": f"Delphi {account_cfg['name']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"✅ Trade Successful on {account_cfg['name']}: {mt5_symbol} @ {price}")
            return True
        else:
            logging.error(f"❌ Trade Failed on {account_cfg['name']}: {result.comment} (Code: {result.retcode})")
            return False

    def run_cycle(self):
        logging.info("--- 🔎 Starting Market Scan ---")
        active_reports = []

        for symbol in self.config.get('symbols', []):
            # 1. Check News Filter
            if self.news_sentry.is_market_volatile(symbol):
                logging.info(f"Skipping {symbol} due to high-impact news.")
                continue

            # 2. Get Data & Detect Regime
            df = self.data_manager.get_latest_data(symbol)
            if df is None or df.empty:
                continue
            
            regime = self.regime_detector.classify(df)
            signal = self.strategy.generate_signal(df, regime)

            if signal:
                logging.info(f"🎯 Signal detected for {symbol}: {signal['action']}")
                risk = self.position_sizer.calculate(df, symbol, signal)
                
                # 3. Iterate through enabled accounts
                for acc in self.config.get('accounts', []):
                    if acc.get('enabled'):
                        if self.connect_account(acc):
                            success = self.execute_on_mt5(symbol, signal, risk, acc)
                            if success:
                                active_reports.append({
                                    "symbol": symbol, 
                                    "type": signal['action'], 
                                    "acc": acc['name'], 
                                    "status": "LIVE"
                                })
                            mt5.shutdown() # Switch accounts cleanly

        # 4. Discord Heartbeat
        self.notifier.send_heartbeat(active_reports, "PC-Native-Lagos")

if __name__ == "__main__":
    oracle = DelphiOraclePC()
    while True:
        try:
            oracle.run_cycle()
            # Sleep for 15 mins (900s)
            time.sleep(900)
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
            break
        except Exception as e:
            logging.error(f"CRITICAL SYSTEM ERROR: {e}")
            time.sleep(60)
