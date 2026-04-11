import pandas as pd
import os
import yaml
import logging
from execution.discord_adapter import DiscordNotifier


def load_config():
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)

    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config["discord"]["webhook_url"] = webhook_env

    return config


def generate_weekly_summary():
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    notifier = DiscordNotifier(config)

    log_path = "logs/trade_log.csv"

    if not os.path.exists(log_path):
        return

    df = pd.read_csv(log_path)

    df = df[df["status"] == "CLOSED"]

    if df.empty:
        notifier.send_heartbeat(["No closed trades"], "Weekly Report")
        return

    total = len(df)
    wins = len(df[df["outcome"] == "✅ TAKE PROFIT"])
    losses = len(df[df["outcome"] == "❌ STOP LOSS"])

    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) else 0

    avg_pnl = df["pnl"].mean()

    report = [
        f"Total Trades: {total}",
        f"Wins: {wins}",
        f"Losses: {losses}",
        f"Win Rate: {win_rate:.2f}%",
        f"Avg PnL: {avg_pnl:.5f}"
    ]

    notifier.send_heartbeat(report, "Weekly Performance")


if __name__ == "__main__":
    generate_weekly_summary()
