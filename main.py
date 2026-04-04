import os
import time
import yaml
import logging
import MetaTrader5 as mt5
from datetime import datetime

# Core Delphi Oracle Modules
from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

class DelphiOracleTrader:
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
        
        # Use plain text to avoid Windows Encoding Errors
        logging.info("STARTUP: Delphi Oracle VPS TRADER Active.")
        logging.info("MODE: Single-Position Lock Enabled.")

    def load_config(self):
        """Loads settings and injects Environment Variables."""
        config_path = "config/settings.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
                for key, value in os.environ.items():
                    content = content.replace(f"${{{key}}}", value)
                return yaml.safe_load(content)
        except Exception as e:
            logging.error(f"Config Load Failure: {e}")
            raise

    def setup_logging(self):
        """Standard logging without emojis for Windows compatibility."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler("vps_execution.log"),
                logging.StreamHandler()
            ]
        )

    def mt5_connect(self, acc):
        """Maintains connection to the Headway MT5 Terminal."""
        if not mt5.initialize():
            return False
        
        authorized = mt5.login(
            int(acc['login']), 
            password=acc['password'], 
            server=acc['server']
        )
        return authorized

    def has_open_position(self, symbol, acc):
        """Checks if a position for this symbol is already open."""
        if not self.mt5_connect(acc):
            return True # Fail-safe: don't trade if we can't verify positions
            
        mt5_symbol = f"{symbol}{acc.get('symbol_suffix', '')}"
        positions = mt5.positions_get(symbol=mt5_symbol)
        
        return len(positions) > 0 if positions is not None else False

    def execute_trade(self, symbol, signal, risk, acc):
        """Sends the live Market Order to the Headway Server."""
        mt5_symbol = f"{symbol}{acc.get('symbol_suffix', '')}"
        mt5.symbol_select(mt5_symbol, True)
        
        tick = mt5.symbol_info_tick(mt5_symbol)
        if tick is None:
            return False

        order_type = mt5.ORDER_TYPE_BUY if "BUY" in signal['action'].upper() else mt5.ORDER_TYPE_SELL
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
            "comment": f"Delphi {acc['name']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def run_cycle(self):
        logging.info(f"--- SCAN START: {datetime.now().strftime('%H:%M')} ---")
        dashboard_report = {}
        symbols = self.config.get('symbols', [])

        for symbol in symbols:
            # Default state
            dashboard_report[symbol] = "Scanning"

            for acc in self.config.get('accounts', []):
                if not acc.get('enabled'):
                    continue

                # 1. Lock Check
                if self.has_open_position(symbol, acc):
                    dashboard_report[symbol] = "Position Open (Locked)"
                    continue

                # 2. Data Ingestion
                df = self.data_manager.get_latest_data(symbol)
                if df is None or df.empty:
                    dashboard_report[symbol] = "Data Fetch Error"
                    continue
                
                # 3. Strategy Engine
                regime = self.regime_detector.classify(df)
                signal = self.strategy.generate_signal(df, regime)

                if signal:
                    risk = self.position_sizer.calculate(df, symbol, signal)
                    if self.mt5_connect(acc):
                        success = self.execute_trade(symbol, signal, risk, acc)
                        if success:
                            dashboard_report[symbol] = f"LIVE {signal['action']}"
                            logging.info(f"TRADE PLACED: {symbol} {signal['action']}")
                        mt5.shutdown()

        # Update Discord
        self.notifier.send_heartbeat(dashboard_report, "Lagos-VPS")
        logging.info("--- SCAN COMPLETE ---")

if __name__ == "__main__":
    oracle = DelphiOracleTrader()
    # If running on GitHub Actions, run once. Otherwise, loop.
    if os.getenv('GITHUB_ACTIONS') == 'true':
        oracle.run_cycle()
    else:
        while True:
            try:
                oracle.run_cycle()
                time.sleep(900) # 15-minute interval
            except Exception as e:
                logging.error(f"RUNTIME ERROR: {e}")
                time.sleep(60)
