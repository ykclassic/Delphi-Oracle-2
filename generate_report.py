import pandas as pd
import os
import yaml
import logging
from datetime import datetime, timedelta
from execution.discord_adapter import DiscordNotifier

def load_config():
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)
    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config['discord']['webhook_url'] = webhook_env
    return config

def generate_weekly_summary():
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    notifier = DiscordNotifier(config)
    log_path = "logs/trade_log.csv"

    if not os.path.exists(log_path):
        logging.error("No log file found. Run the bot first to generate data.")
        return

    try:
        df = pd.read_csv(log_path)
        # Filter for signals only (ignore 'None' rows)
        df_signals = df[df['Signal'] != 'None'].copy()
        
        if df_signals.empty:
            notifier.send_heartbeat(["No trades executed this week. Quality filter was high."], "Weekly Summary 📊")
            return

        # 1. Basic Stats
        total_trades = len(df_signals)
        wins = len(df_signals[df_signals['Outcome'].str.contains("TAKE PROFIT", na=False)])
        losses = len(df_signals[df_signals['Outcome'].str.contains("STOP LOSS", na=False)])
        pending = len(df_signals[df_signals['Outcome'] == "Pending"])
        
        win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0

        # 2. Regime Performance (Quality Check)
        # Counts which regime produced the most signals
        regime_counts = df_signals['Regime'].value_counts().to_dict()
        regime_names = {0: "Range 🟦", 1: "Trend 🟩", 2: "Chaos 🟧"}
        
        regime_summary = [f"{regime_names.get(k, k)}: {v} signals" for k, v in regime_counts.items()]

        # 3. Construct Message
        report = [
            f"🗓 **Period:** Last 7 Days",
            f"🔢 **Total Signals:** {total_trades}",
            f"✅ **Wins:** {wins}",
            f"❌ **Losses:** {losses}",
            f"⏳ **Pending:** {pending}",
            f"📈 **Win Rate:** {win_rate:.1f}%",
            "\n**Regime Distribution:**",
            *regime_summary,
            f"\n**Strategy:** Quality Over Quantity"
        ]

        notifier.send_heartbeat(report, "🏆 WEEKLY PERFORMANCE REPORT")
        logging.info("Weekly report sent to Discord.")

    except Exception as e:
        logging.error(f"Failed to generate report: {e}")

if __name__ == "__main__":
    generate_weekly_summary()
