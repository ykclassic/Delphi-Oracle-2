import MetaTrader5 as mt5
import yaml
import os
import sys
import requests
from datetime import datetime

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_audit_report(self, results):
        """Sends a formatted embed to Discord with the account statuses."""
        embed = {
            "title": "🔮 Delphi Oracle: Account Connection Audit",
            "color": 0x7289da,  # Professional Blurple
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [],
            "footer": {"text": "System Architecture: Oracle Cloud / VPSWala"}
        }

        for name, status, details in results:
            indicator = "✅" if status == "Connected" else "❌"
            embed["fields"].append({
                "name": f"{indicator} {name}",
                "value": f"**Status:** {status}\n**Details:** {details}",
                "inline": False
            })

        payload = {"embeds": [embed]}
        try:
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            print(f"⚠️ Discord Alert Failed: {e}")

def load_config(config_path="settings.yaml"):
    if not os.path.exists(config_path):
        print(f"❌ Critical Error: {config_path} not found.")
        sys.exit(1)
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def verify_all_accounts():
    config = load_config()
    accounts = config.get("accounts", [])
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    notifier = DiscordNotifier(webhook) if webhook else None
    
    if not mt5.initialize():
        print("❌ MT5 Initialization failed.")
        sys.exit(1)

    audit_results = []
    all_success = True

    for acc in accounts:
        if not acc.get("enabled"):
            audit_results.append((acc['name'], "Skipped", "Disabled in settings.yaml"))
            continue

        login_id = int(acc["login"])
        srv = acc["server"]
        # Fetching the password from the environment variable named in YAML
        env_var_name = acc["password"].replace("${", "").replace("}", "")
        pwd = os.getenv(env_var_name)

        authorized = mt5.login(login=login_id, password=pwd, server=srv)
        
        if authorized:
            info = mt5.account_info()
            detail_str = f"Equity: {info.equity} {info.currency} | Lev: 1:{info.leverage}"
            audit_results.append((acc['name'], "Connected", detail_str))
        else:
            err = f"Error: {mt5.last_error()}"
            audit_results.append((acc['name'], "FAILED", err))
            all_success = False

    # Send the final report to Discord
    if notifier:
        notifier.send_audit_report(audit_results)

    mt5.shutdown()

    if not all_success:
        sys.exit(1)

if __name__ == "__main__":
    verify_all_accounts()
