import os
import yaml
import requests
from core.monitor import SignalMonitor

def load_config():
    with open("config/settings.yaml", "r") as f:
        config = yaml.safe_load(f)
    webhook_env = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_env:
        config['discord']['webhook_url'] = webhook_env
    return config

def run_monitor():
    config = load_config()
    monitor = SignalMonitor(config)
    
    # Check for hits
    updates = monitor.check_outcomes()
    
    # Notify Discord if something happened
    if updates and config['discord']['webhook_url']:
        payload = {
            "embeds": [{
                "title": "📈 Trade Result Update",
                "description": "\n".join(updates),
                "color": 3447003, # Blue
                "footer": {"text": "Delphi Oracle Monitor"}
            }]
        }
        requests.post(config['discord']['webhook_url'], json=payload)
        print(f"Sent {len(updates)} updates to Discord.")
    else:
        print("No trade outcomes to report.")

if __name__ == "__main__":
    run_monitor()
