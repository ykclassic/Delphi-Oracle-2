import os
import time
import yaml
import logging
import MetaTrader5 as mt5
from datetime import datetime

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
        self.notifier = DiscordNotifier(self.config)
        self.data_manager = DataManager(self.config)
        self.regime_detector = RegimeDetector()
        self.strategy = TrendStrategy(self.config)
        self.news_sentry = NewsSentry(self.config)
        self.position_sizer = PositionSizer(self.config)
        logging.info("🚀 Delphi Oracle VPS TRADER Active.")

    def load_config(self):
        config_path = "config/settings.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            return yaml.safe_load(content)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.FileHandler("vps_execution.log"), logging.StreamHandler()]
        )

    def mt5_connect(self, acc):
        if not mt5.initialize(): return False
        return mt5.login(int(acc['login']), password=acc['password'], server=acc['server'])

    def has_open_position(self, symbol, acc):
        if not self.mt5_connect(acc): return True
        mt5_symbol = f"{symbol}{acc.get('symbol_suffix', '')}"
        positions = mt5.positions_get(symbol=mt5_symbol)
        return len(positions) > 0 if positions is not None else False

    def execute_trade(self, symbol, signal, risk, acc):
        mt5_symbol = f"{symbol}{acc.get('symbol_suffix', '')}"
        mt5.symbol_select(mt5_symbol, True)
        tick = mt5.symbol_info_tick(mt5_symbol)
        if not tick: return False

        order_type = mt5.ORDER_TYPE_BUY if "BUY" in signal['action'].upper() else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_symbol,
            "volume": float(risk['lots']),
            "type": order_type,
            "price": tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid,
            "sl": float(risk['sl']),
            "tp": float(risk['tp']),
            "magic": 202603,
            "comment": "Delphi VPS",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def run_cycle(self):
        logging.info(f"--- 🛰️ Cycle Start: {datetime.now().strftime('%H:%M')} ---")
        
        # Dashboard tracking: { Symbol: Status_Message }
        dashboard_report = {}

        for symbol in self.config.get('symbols', []):
            # Default status
            dashboard_report[symbol] = "Scanning..."

            for acc in self.config.get('accounts', []):
                if not acc.get('enabled'): continue

                # 1. Check Lock
                if self.has_open_position(symbol, acc):
                    dashboard_report[symbol] = "Position Open 🔒"
                    continue

                # 2. Analysis
                df = self.data_manager.get_latest_data(symbol)
                if df is None or df.empty:
                    dashboard_report[symbol] = "Data Error 🔴"
                    continue
                
                regime = self.regime_detector.classify(df)
                signal = self.strategy.generate_signal(df, regime)

                if signal:
                    risk = self.position_sizer.calculate(df, symbol, signal)
                    if self.mt5_connect(acc):
                        if self.execute_trade(symbol, signal, risk, acc):
                            dashboard_report[symbol] = f"LIVE {signal['action']} 💰"
                        mt5.shutdown()

        # Send the full dashboard to Discord
        self.notifier.send_heartbeat(dashboard_report, "Lagos-VPS-Trader")

if __name__ == "__main__":
    oracle = DelphiOracleTrader()
    while True:
        try:
            oracle.run_cycle()
            time.sleep(900)
        except Exception as e:
            logging.error(f"System Error: {e}")
            time.sleep(60)
