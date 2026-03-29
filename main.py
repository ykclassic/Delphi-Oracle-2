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
        self.config = self.load_config()
        self.setup_logging()
        self.notifier = DiscordNotifier(self.config)
        self.data_manager = DataManager(self.config)
        self.regime_detector = RegimeDetector()
        self.strategy = TrendStrategy(self.config)
        self.news_sentry = NewsSentry(self.config)
        self.position_sizer = PositionSizer(self.config)
        
        logging.info(f"🔮 {self.config['bot_name']} v{self.config['version']} Initialized.")

    def load_config(self):
        with open("config/settings.yaml", "r") as f:
            # Replaces ${VAR} with actual env variables if present
            content = f.read()
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            return yaml.safe_load(content)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.FileHandler("delphi_oracle.log"), logging.StreamHandler()]
        )

    def connect_account(self, account_cfg):
        """Standard MT5 Login for PC."""
        if not mt5.initialize():
            logging.error("MT5 Initialize failed.")
            return False
        
        authorized = mt5.login(
            int(account_cfg['login']), 
            password=account_cfg['password'], 
            server=account_cfg['server']
        )
        return authorized

    def execute_on_mt5(self, symbol, signal, risk, account_cfg):
        """Native PC Execution Logic."""
        # Handle Symbol Suffix (e.g., EURUSD -> EURUSD.c)
        suffix = account_cfg.get('symbol_suffix', "")
        mt5_symbol = f"{symbol}{suffix}"

        order_type = mt5.ORDER_TYPE_BUY if "BUY" in signal['action'] else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(mt5_symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(mt5_symbol).bid

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
            logging.info(f"✅ Trade Successful on {account_cfg['name']}: {mt5_symbol}")
            return True
        else:
            logging.error(f"❌ Trade Failed on {account_cfg['name']}: {result.comment}")
            return False

    def run_cycle(self):
        logging.info("--- Starting Market Scan ---")
        active_reports = []

        for symbol in self.config['symbols']:
            # 1. Check News
            if self.news_sentry.is_market_volatile(symbol):
                continue

            # 2. Get Data & Detect Regime
            df = self.data_manager.get_latest_data(symbol)
            if df is None: continue
            
            regime = self.regime_detector.classify(df)
            signal = self.strategy.generate_signal(df, regime)

            if signal:
                risk = self.position_sizer.calculate(df, symbol, signal)
                
                # 3. Iterate through enabled accounts
                for acc in self.config['accounts']:
                    if acc['enabled']:
                        if self.connect_account(acc):
                            success = self.execute_on_mt5(symbol, signal, risk, acc)
                            if success:
                                active_reports.append({
                                    "symbol": symbol, "type": signal['action'], 
                                    "acc": acc['name'], "status": "LIVE"
                                })
                        mt5.shutdown() # Close connection to switch accounts if needed

        # 4. Discord Heartbeat
        self.notifier.send_heartbeat(active_reports, "PC-Native-Lagos")

if __name__ == "__main__":
    oracle = DelphiOraclePC()
    while True:
        try:
            oracle.run_cycle()
            # Sleep for 15 mins (900s) for H1/M15 strategies
            time.sleep(900)
        except Exception as e:
            logging.error(f"Critical System Error: {e}")
            time.sleep(60)
