import requests
import datetime

class DiscordNotifier:
    def __init__(self, config):
        self.webhook_url = config['discord']['webhook_url']

    def send_signal(self, symbol, signal_type, risk_data):
        """Sends a professionally formatted Embed to Discord."""
        color = 3066993 if "BUY" in signal_type else 15158332 # Green for Buy, Red for Sell
        
        payload = {
            "username": "Gemini Alpha 2026",
            "embeds": [{
                "title": f"🚀 NEW SIGNAL: {symbol}",
                "description": f"**Action:** {signal_type}\n**Timeframe:** 1H",
                "color": color,
                "fields": [
                    {"name": "Entry", "value": f"{risk_data['entry']}", "inline": True},
                    {"name": "Stop Loss", "value": f"{risk_data['sl']}", "inline": True},
                    {"name": "Take Profit", "value": f"{risk_data['tp']}", "inline": True},
                    {"name": "Risk/Position", "value": f"{risk_data['lots']} Lots", "inline": False}
                ],
                "footer": {"text": f"Generated at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"}
            }]
        }
        
        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 204
