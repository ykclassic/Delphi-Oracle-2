import requests
import logging
from datetime import datetime

class DiscordNotifier:
    def __init__(self, config):
        self.webhook_url = config.get('discord_webhook')
        self.bot_name = config.get('bot_name', 'Delphi Oracle')

    def send_heartbeat(self, dashboard_data, source="VPS"):
        if not self.webhook_url: return

        scan_results = ""
        for symbol, data in dashboard_data.items():
            status = data.get('status', 'Scanning')
            # Select Emoji based on text content
            if "LIVE" in status or "SIGNAL" in status: icon = "🟢"
            elif "Locked" in status: icon = "🔒"
            elif "Error" in status: icon = "🔴"
            else: icon = "🟦"
            
            scan_results += f"{icon} **{symbol}**: {status}\n"

        payload = {
            "username": self.bot_name,
            "embeds": [{
                "title": f"🔮 {self.bot_name} Dashboard",
                "description": f"**Source:** `{source}`\n**Time:** {datetime.now().strftime('%H:%M:%S')}",
                "color": 0x00ff00,
                "fields": [{"name": "📊 Market Scan", "value": scan_results or "None"}]
            }]
        }
        requests.post(self.webhook_url, json=payload)
