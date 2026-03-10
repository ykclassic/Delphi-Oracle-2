import os
import yaml
import logging
from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from core.logger import PerformanceLogger
from core.session_manager import SessionManager
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

def load_config():
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)
    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config['discord']['webhook_url'] = webhook_env
    return config

def run_bot():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    config = load_config()
    
    # Initialize Modules
    data_manager = DataManager(config)
    regime_detector = RegimeDetector()
    perf_logger = PerformanceLogger()
    news_sentry = NewsSentry(config)
    session_manager = SessionManager()
    strategy = TrendStrategy(config)
    position_sizer = PositionSizer(config)
    notifier = DiscordNotifier(config)

    summary_results = []
    current_session = session_manager.get_current_session()

    for symbol in config['symbols']:
        # 1. News Check
        if news_sentry.is_market_volatile(symbol):
            summary_results.append(f"⚪ {symbol}: News Block")
            continue
            
        # 2. Data Acquisition
        df = data_manager.get_latest_data(symbol)
        if df is None or len(df) < 50:
            summary_results.append(f"🔴 {symbol}: Data Error")
            continue
            
        # 3. Market Analysis
        regime = regime_detector.classify(df)
        signal_type = strategy.generate_signal(df, regime)
        
        # 4. Signal & Logging
        risk_data = None
        if signal_type:
            risk_data = position_sizer.calculate(df, symbol, signal_type)
            notifier.send_signal(symbol, signal_type, risk_data, current_session)
            summary_results.append(f"🔥 {symbol}: {signal_type}")
        else:
            regime_map = {0: "🟦 Range", 1: "🟩 Trend", 2: "🟧 Chaos"}
            summary_results.append(f"{regime_map.get(regime)} {symbol}")

        perf_logger.log_scan(symbol, regime, signal_type, risk_data)

    # 5. Final Heartbeat with Session Info
    notifier.send_heartbeat(summary_results, current_session)
    logging.info(f"Scan complete for {current_session} session.")

if __name__ == "__main__":
    run_bot()
