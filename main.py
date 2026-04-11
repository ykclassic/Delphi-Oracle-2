import os
import yaml
import logging
import datetime

from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from core.logger import PerformanceLogger
from core.session_manager import SessionManager
from core.monitor import SignalMonitor

from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer

from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier


def load_config():
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)

    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config["discord"]["webhook_url"] = webhook_env

    return config


def run_bot():
    logging.basicConfig(level=logging.INFO)
    logging.info("=== Gemini Forex Alpha Starting ===")

    config = load_config()

    data_manager = DataManager(config)
    regime_detector = RegimeDetector()
    logger = PerformanceLogger()
    monitor = SignalMonitor(config)

    news_sentry = NewsSentry(config)
    session_manager = SessionManager()
    strategy = TrendStrategy(config)
    position_sizer = PositionSizer(config)
    notifier = DiscordNotifier(config)

    current_session = session_manager.get_current_session()
    summary = []

    for symbol in config["symbols"]:
        logging.info(f"Analyzing {symbol}")

        if news_sentry.is_market_volatile(symbol):
            summary.append(f"{symbol}: News Block")
            continue

        df = data_manager.get_latest_data(symbol)
        if df is None or len(df) < 50:
            summary.append(f"{symbol}: Data Error")
            continue

        regime = regime_detector.classify(df)

        signal = strategy.generate_signal(df, regime)

        if signal:
            risk = position_sizer.calculate(df, symbol, signal)

            if risk:
                notifier.send_signal(symbol, signal, risk, current_session)
                logger.log_trade(symbol, regime, signal, risk)
                summary.append(f"{symbol}: {signal}")
            else:
                summary.append(f"{symbol}: Rejected (Spread)")
        else:
            summary.append(f"{symbol}: No Signal")

    # 🔥 CRITICAL: Evaluate trades AFTER scan
    updates = monitor.check_outcomes()

    if updates:
        notifier.send_heartbeat(updates, current_session)

    notifier.send_heartbeat(summary, current_session)

    logging.info("=== Cycle Complete ===")


if __name__ == "__main__":
    run_bot()
