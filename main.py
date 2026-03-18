import os
import yaml
import logging
import datetime
import pandas as pd
from core.data_ingestion import DataManager
from core.regime_detector import RegimeDetector
from core.logger import PerformanceLogger
from core.session_manager import SessionManager
from risk_management.news_sentry import NewsSentry
from risk_management.position_sizer import PositionSizer
from strategies.trend_following import TrendStrategy
from execution.discord_adapter import DiscordNotifier

def load_config():
    """Loads configuration and resolves environment secrets."""
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config['discord']['webhook_url'] = webhook_env
    return config

def run_bot():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("--- 🔮 Delphi Oracle v1.1: Quality Engine Starting ---")
    
    config = load_config()
    if not config['discord'].get('webhook_url'):
        logging.error("Missing DISCORD_WEBHOOK_URL.")
        return

    # Module Instantiation
    data_manager = DataManager(config)
    regime_detector = RegimeDetector()
    perf_logger = PerformanceLogger()
    news_sentry = NewsSentry(config)
    session_manager = SessionManager()
    strategy = TrendStrategy(config)
    position_sizer = PositionSizer(config)
    notifier = DiscordNotifier(config)

    active_setups = []
    current_session = session_manager.get_current_session()
    
    for symbol in config['symbols']:
        logging.info(f"Analyzing {symbol}...")
        
        # A. News Filter
        if news_sentry.is_market_volatile(symbol):
            logging.warning(f"Skipping {symbol}: News Sentry Block")
            active_setups.append({
                "symbol": symbol, "type": "News Block", "status": "⚪", 
                "entry": "N/A", "sl": "N/A", "tp": "N/A"
            })
            continue
            
        # B. Data Acquisition
        df = data_manager.get_latest_data(symbol)
        if df is None or len(df) < 50:
            logging.warning(f"Insufficient data for {symbol}.")
            active_setups.append({
                "symbol": symbol, "type": "Data Fetch Error", "status": "🔴", 
                "entry": "N/A", "sl": "N/A", "tp": "N/A"
            })
            continue
            
        # C. Market Intelligence
        regime = regime_detector.classify(df)
        regime_labels = {0: "Range", 1: "Trend", 2: "Chaos"}
        regime_icons = {0: "🟦", 1: "🟩", 2: "🟧"}
        current_regime_label = regime_labels.get(regime, "Unknown")
        current_icon = regime_icons.get(regime, "❓")

        # D. Signal Generation
        signal_data = strategy.generate_signal(df, regime)
        
        if signal_data:
            # E. Quality Control & Position Sizing
            risk_data = position_sizer.calculate(df, symbol, signal_data)
            
            if risk_data:
                # 🚀 Send HIGH PRIORITY individual signal alert
                notifier.send_signal(symbol, signal_data['action'], risk_data, current_session)
                perf_logger.log_scan(symbol, regime, signal_data['action'], risk_data)
                
                active_setups.append({
                    "symbol": symbol, "type": signal_data['action'], "status": "🔥",
                    "entry": risk_data['entry'], "sl": risk_data['sl'], "tp": risk_data['tp']
                })
            else:
                active_setups.append({
                    "symbol": symbol, "type": "Spread High/Rejected", "status": "🚫",
                    "entry": "N/A", "sl": "N/A", "tp": "N/A"
                })
        else:
            # No setup found: Default Scanning Mode
            active_setups.append({
                "symbol": symbol, "type": f"{current_regime_label}: Scanning...", "status": current_icon,
                "entry": "N/A", "sl": "N/A", "tp": "N/A"
            })

    # 4. Final Heartbeat Update (Unified dictionary list)
    notifier.send_heartbeat(active_setups, current_session)
    
    # 5. Weekly Report Logic
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() == 4 and now.hour == 21:
        generate_weekly_report(perf_logger, notifier)

    logging.info("--- Scan Cycle Complete ---")

def generate_weekly_report(logger, notifier):
    try:
        df = pd.read_csv(logger.file_path)
        total_signals = len(df[df['Signal'] != 'None'])
        wins = len(df[df['Outcome'] == '✅ TAKE PROFIT'])
        losses = len(df[df['Outcome'] == '❌ STOP LOSS'])
        win_rate = (wins/max(1, wins+losses))*100
        
        report = [
            f"**Total Signals:** {total_signals}",
            f"**Wins:** {wins} ✅",
            f"**Losses:** {losses} ❌",
            f"**Win Rate:** {win_rate:.1f}%"
        ]
        notifier.send_heartbeat_simple(report, "WEEKLY PERFORMANCE SUMMARY 📊")
    except Exception as e:
        logging.error(f"Report failed: {e}")

if __name__ == "__main__":
    run_bot()
