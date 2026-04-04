import os
import time
import yaml
import logging
import pandas as pd
from datetime import datetime

# Conditional import for MT5 (PC only)
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

class DelphiOracle:
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
        
        mode = "GITHUB-MONITOR" if self.is_github else "PC-TRADER"
        logging.info(f"STARTUP: Delphi Oracle {mode} Active.")

    def load_config(self):
        config_path = os.path.join("config", "settings.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            return yaml.safe_load(content)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )

    def get_yahoo_symbol(self, symbol):
        """Maps internal symbols to Yahoo Finance format for GitHub runs."""
        if any(c in symbol for c in ["BTC", "ETH", "SOL"]):
            return symbol.replace("USD", "-USD")
        if "XAUUSD" in symbol: return "GC=F"
        if "XAGUSD" in symbol: return "SI=F"
        return f"{symbol}=X" if "=X" not in symbol else symbol

    def check_position_lock(self, symbol):
        """Checks if a trade is already open (PC Only)."""
        if self.is_github or not MT5_AVAILABLE:
            return False
        
        for acc in self.config.get('accounts', []):
            if acc.get('enabled'):
                if not mt5.initialize(): continue
                mt5.login(int(acc['login']), password=acc['password'], server=acc['server'])
                pos = mt5.positions_get(symbol=symbol)
                if pos: return True
        return False

    def execute_pc_trade(self, symbol, signal, risk):
        """Executes trade via MT5 (PC Only)."""
        if self.is_github or not MT5_AVAILABLE: return False
        
        for acc in self.config.get('accounts', []):
            if acc.get('enabled'):
                mt5.login(int(acc['login']), password=acc['password'], server=acc['server'])
                tick = mt5.symbol_info_tick(symbol)
                order_type = mt5.ORDER_TYPE_BUY if "BUY" in signal['action'] else mt5.ORDER_TYPE_SELL
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": float(risk['lots']),
                    "type": order_type,
                    "price": tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid,
                    "sl": float(risk['sl']),
                    "tp": float(risk['tp']),
                    "magic": 202603,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                res = mt5.order_send(request)
                return res.retcode == mt5.TRADE_RETCODE_DONE
        return False

    def run_cycle(self):
        logging.info(f"--- SCAN START: {datetime.now().strftime('%H:%M')} ---")
        dashboard = {}
        
        for symbol in self.config.get('symbols', []):
            # 1. Position Lock (PC Only)
            if self.check_position_lock(symbol):
                dashboard[symbol] = {"status": "Locked 🔒"}
                continue

            # 2. Data Fetching (GitHub uses Yahoo mapping, PC uses direct)
            fetch_symbol = self.get_yahoo_symbol(symbol) if self.is_github else symbol
            df = self.data_manager.get_latest_data(fetch_symbol)
            
            if df is None or df.empty:
                dashboard[symbol] = {"status": "Data Error 🔴"}
                continue

            # 3. Signal Generation
            regime = self.regime_detector.classify(df)
            signal = self.strategy.generate_signal(df, regime)

            if signal:
                risk = self.position_sizer.calculate(df, symbol, signal)
                if not self.is_github:
                    success = self.execute_pc_trade(symbol, signal, risk)
                    status = f"LIVE {signal['action']} 💰" if success else "Execution Fail"
                else:
                    status = f"SIGNAL: {signal['action']} 📡"
                dashboard[symbol] = {"status": status}
            else:
                dashboard[symbol] = {"status": "Scanning 🟦"}

        source = "GitHub-Cloud" if self.is_github else "Lagos-VPS"
        self.notifier.send_heartbeat(dashboard, source)
        logging.info("--- SCAN COMPLETE ---")

if __name__ == "__main__":
    bot = DelphiOracle()
    if os.getenv('GITHUB_ACTIONS') == 'true':
        bot.run_cycle()
    else:
        while True:
            bot.run_cycle()
            time.sleep(900)
