import requests
import logging
from datetime import datetime

class DiscordNotifier:
    def __init__(self, config):
        self.webhook_url = config.get('discord_webhook')
        self.bot_name = config.get('bot_name', 'Delphi Oracle')

    def send_heartbeat(self, dashboard_data, source="VPS"):
        if not self.webhook_url:
            logging.warning("Discord Webhook URL is missing in config.")
            return

        scan_results = ""
        # Build the string from the dashboard dictionary
        for symbol, data in dashboard_data.items():
            status = data.get('status', 'Scanning')
            
            # Select Emoji based on text content
            if "LIVE" in status or "SIGNAL" in status: 
                icon = "🟢"
            elif "Locked" in status: 
                icon = "🔒"
            elif "Error" in status: 
                icon = "🔴"
            else: 
                icon = "🟦"
            
            scan_results += f"{icon} **{symbol}**: {status}\n"

        if not scan_results:
            scan_results = "No data available for this cycle."

        payload = {
            "username": self.bot_name,
            "embeds": [{
                "title": f"🔮 {self.bot_name} Dashboard",
                "description": f"**Source:** `{source}`\n**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "color": 0x00ff00,
                "fields": [
                    {
                        "name": "📊 Market Scan Status",
                        "value": scan_results,
                        "inline": False
                    }
                ],
                "footer": {"text": "Delphi Oracle Alpha | 2026"}
            }]
        }

        # Added headers to prevent being blocked as a bot
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DelphiOracle/2.6"
        }

        try:
            logging.info(f"Sending Discord alert from {source}...")
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                headers=headers, 
                timeout=10
            )
            response.raise_for_status()
            logging.info("Discord alert sent successfully.")
        except requests.exceptions.HTTPError as errh:
            logging.error(f"Discord HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            logging.error(f"Discord Connection Error: {errc}")
        except Exception as e:
            logging.error(f"Unexpected Discord Error: {e}")
