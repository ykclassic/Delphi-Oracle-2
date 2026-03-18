import os
import yaml
import logging
import datetime
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
    
    # Resolve Discord Webhook from GitHub Secrets
    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config['discord']['webhook_url'] = webhook_env
    return config

def run_bot():
    # 1. Initialize System & Logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("--- Delphi Oracle v1.1: Quality Engine Starting ---")
    
    config = load_config()
    if not config['discord'].get('webhook_url'):
        logging.error("Missing DISCORD_WEBHOOK_URL. Bot cannot send alerts.")
        return

    # 2. Module Instantiation
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
    
    # 3. Main Execution Loop
    for symbol in config['symbols']:
        logging.info(f"Analyzing {symbol}...")
        
        # A. News Filter (High Impact Protection)
        if news_sentry.is_market_volatile(symbol):
            logging.warning(f"Skipping {symbol}: High-impact news detected.")
            summary_results.append(f"⚪ {symbol}: News Sentry Block")
            continue
            
        # B. Data Acquisition (Retry Logic handled in DataManager)
        df = data_manager.get_latest_data(symbol)
        if df is None or len(df) < 50:
            logging.warning(f"Insufficient data for {symbol}.")
            summary_results.append(f"🔴 {symbol}: Data Fetch Error")
            continue
            
        # C. Market Intelligence (Regime Analysis)
        # 0=Range, 1=Trend, 2=Chaos
        regime = regime_detector.classify(df)
        regime_map = {0: "🟦 Range", 1: "🟩 Trend", 2: "🟧 Chaos"}
        logging.info(f"{symbol} detected in {regime_map.get(regime)} regime.")

        # D. Signal Generation
        signal_type = strategy.generate_signal(df, regime)
        
        # E. Quality Control: Spread & Position Sizing
        if signal_type:
            # Calculate Risk & Check Spread Quality
            risk_data = position_sizer.calculate(df, symbol, signal_type)
            
            if risk_data:
                # Execution: Send Alert & Log Data
                notifier.send_signal(symbol, signal_data['action'], risk_data, current_session)
                perf_logger.log_scan(symbol, regime, signal_type, risk_data)
                summary_results.append(f"🔥 {symbol}: {signal_type} SENT")
                logging.info(f"Signal confirmed and sent for {symbol}.")
            else:
                # Signal rejected by Spread Guard (Quality Check)
                summary_results.append(f"🚫 {symbol}: Rejected (Low Quality/High Spread)")
                logging.warning(f"Signal rejected for {symbol} due to poor Risk/Reward (Spread).")
        else:
            # No technical setup found
            summary_results.append(f"{regime_map.get(regime)} {symbol}: Scanning...")

    # 4. Final Heartbeat Update
    notifier.send_heartbeat(summary_results, current_session)
    
    # 5. Friday Weekly Report Logic
    # If today is Friday and it's the last hour of the trading week (21:00 UTC)
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() == 4 and now.hour == 21:
        logging.info("Generating Weekly Performance Report...")
        generate_weekly_report(perf_logger, notifier)

    logging.info("--- Scan Cycle Complete ---")

def generate_weekly_report(logger, notifier):
    """Calculates weekly P&L stats and sends to Discord."""
    try:
        df = pd.read_csv(logger.file_path)
        # Filter for last 7 days and successful outcomes
        # (This is a simplified summary logic)
        total_signals = len(df[df['Signal'] != 'None'])
        wins = len(df[df['Outcome'] == '✅ TAKE PROFIT'])
        losses = len(df[df['Outcome'] == '❌ STOP LOSS'])
        
        report = [
            f"**Total Signals:** {total_signals}",
            f"**Wins:** {wins} ✅",
            f"**Losses:** {losses} ❌",
            f"**Win Rate:** {(wins/max(1, wins+losses))*100:.1f}%"
        ]
        
        # We can use the notifier's heartbeat style for the report
        notifier.send_heartbeat(report, "WEEKLY PERFORMANCE SUMMARY 📊")
    except Exception as e:
        logging.error(f"Report generation failed: {e}")

if __name__ == "__main__":
    run_bot()
