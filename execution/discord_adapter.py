import requests
import logging
from datetime import datetime

class DiscordNotifier:
    def __init__(self, config):
        """
        Initializes the notifier by reaching into the 'discord' block 
        of settings.yaml and checking for environment overrides.
        """
        # Navigate the dictionary safely to find the webhook_url
        self.discord_config = config.get('discord', {})
        self.webhook_url = self.discord_config.get('webhook_url')
        self.bot_name = config.get('bot_name', 'Delphi Oracle Alpha')

        # Logic to catch un-injected GitHub Secrets or placeholders
        if self.webhook_url:
            if "${" in str(self.webhook_url) or self.webhook_url == "EMPTY":
                logging.warning("⚠️ Discord Webhook URL detected as a placeholder. Setting to None.")
                self.webhook_url = None
        
        if not self.webhook_url:
            logging.warning("❌ Discord Notifier initialized WITHOUT a valid Webhook URL.")

    def send_heartbeat(self, dashboard_data, source="GitHub Actions"):
        """
        Formats and sends the Market Scan Status dashboard to Discord.
        Expected format for dashboard_data: {'SYMBOL': {'status': 'Text'}, ...}
        """
        if not self.webhook_url:
            logging.error("Attempted to send heartbeat, but Discord Webhook URL is missing.")
            return

        scan_results = ""
        
        # Build the status list from the dashboard dictionary
        if isinstance(dashboard_data, dict):
            for symbol, data in dashboard_data.items():
                status = data.get('status', 'Scanning')
                
                # Dynamic Emoji selection for scannability
                if any(x in status.upper() for x in ["LIVE", "SIGNAL", "TAKE PROFIT", "BUY", "SELL"]): 
                    icon = "🟢"
                elif "LOCKED" in status.upper() or "ACTIVE" in status.upper(): 
                    icon = "🔒"
                elif "ERROR" in status.upper() or "FAILED" in status.upper() or "REJECTED" in status.upper(): 
                    icon = "🔴"
                else: 
                    icon = "🟦"
                
                scan_results += f"{icon} **{symbol}**: {status}\n"
        elif isinstance(dashboard_data, list):
            # Fallback for simple list summaries
            scan_results = "\n".join([f"🔹 {item}" for item in dashboard_data])

        if not scan_results:
            scan_results = "No market data captured in this cycle."

        payload = {
            "username": self.bot_name,
            "embeds": [{
                "title": f"🔮 {self.bot_name} Dashboard",
                "description": f"**Source:** `{source}`\n**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "color": 0x5865F2,  # Discord Blurple
                "fields": [
                    {
                        "name": "📊 Market Scan Status",
                        "value": scan_results,
                        "inline": False
                    }
                ],
                "footer": {"text": "TechSolute Intelligence | 2026"}
            }]
        }

        # Anti-block headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"DelphiOracle/{self.bot_name}"
        }

        try:
            logging.info(f"Dispatching Discord alert from {source}...")
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                headers=headers, 
                timeout=12
            )
            response.raise_for_status()
            logging.info("✅ Discord Dashboard updated successfully.")
        except requests.exceptions.RequestException as e:
            logging.error(f"🔴 Discord Notification Failed: {e}")

    def send_signal(self, symbol, action, risk_data, session):
        """
        Sends a high-priority trading signal alert.
        """
        if not self.webhook_url: return

        color = 0x00FF00 if "BUY" in action.upper() else 0xFF0000
        payload = {
            "username": self.bot_name,
            "embeds": [{
                "title": f"🚀 NEW SIGNAL: {symbol}",
                "color": color,
                "fields": [
                    {"name": "Action", "value": f"**{action.upper()}**", "inline": True},
                    {"name": "Session", "value": session, "inline": True},
                    {"name": "Lots", "value": str(risk_data.get('lots', '0.01')), "inline": True},
                    {"name": "Entry", "value": str(risk_data.get('entry', 'Market')), "inline": True},
                    {"name": "SL", "value": str(risk_data.get('sl', 'None')), "inline": True},
                    {"name": "TP", "value": str(risk_data.get('tp', 'None')), "inline": True}
                ],
                "footer": {"text": "Execute with caution. Check spreads on Headway."}
            }]
        }
        
        try:
            requests.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Signal broadcast failed: {e}")
