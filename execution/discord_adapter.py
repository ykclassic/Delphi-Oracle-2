import requests
import datetime
import os

class DiscordNotifier:
    def __init__(self, config):
        # Resolve webhook from config or environment
        raw_url = config['discord'].get('webhook_url', '')
        if "${" in str(raw_url):
            env_var = raw_url.replace("${", "").replace("}", "")
            self.webhook_url = os.getenv(env_var)
        else:
            self.webhook_url = raw_url

    def send_signal(self, symbol, signal_action, risk_data, session):
        """Sends a high-priority trade signal alert."""
        color = 3066993 if "BUY" in str(signal_action) else 15158332
        
        payload = {
            "embeds": [{
                "title": f"🚀 NEW SIGNAL: {symbol}",
                "description": f"**Action:** {signal_action}\n**Session:** {session}",
                "color": color,
                "fields": [
                    {"name": "Entry", "value": f"`{risk_data['entry']}`", "inline": True},
                    {"name": "Stop Loss", "value": f"`{risk_data['sl']}`", "inline": True},
                    {"name": "Take Profit", "value": f"`{risk_data['tp']}`", "inline": True}
                ],
                "footer": {"text": f"Delphi Oracle v1.1 | {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')} UTC"}
            }]
        }
        self._post(payload)

    def send_heartbeat(self, active_signals, session):
        """Sends heartbeat with formatted price levels and status icons."""
        color = 9807270 
        formatted_lines = []
        
        for sig in active_signals:
            icon = sig.get('status', '🟦')
            symbol = sig.get('symbol', 'Unknown')
            action_type = sig.get('type', 'Scanning...')
            
            if sig['entry'] != "N/A":
                # Detailed view for actual trades
                line = (f"{icon} **{symbol}**: {action_type}\n"
                        f"└ `ENT: {sig['entry']}` | `SL: {sig['sl']}` | `TP: {sig['tp']}`")
            else:
                # Simple view for scanning or errors
                line = f"{icon} **{symbol}**: {action_type}"
            
            formatted_lines.append(line)
        
        description_text = "\n".join(formatted_lines) if formatted_lines else "📡 Scanning markets..."
        
        payload = {
            "embeds": [{
                "title": "💓 System Heartbeat",
                "description": f"**Active Session:** {session}\n\n**Market Scan:**\n{description_text}",
                "color": color,
                "footer": {"text": f"Status: Active | Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M')} UTC"}
            }]
        }
        self._post(payload)

    def send_heartbeat_simple(self, text_list, title):
        """Helper for weekly reports or simple text lists."""
        payload = {
            "embeds": [{
                "title": title,
                "description": "\n".join(text_list),
                "color": 15844367,
                "footer": {"text": "Weekly Performance Audit"}
            }]
        }
        self._post(payload)

    def _post(self, payload):
        """Internal helper to handle the request."""
        if not self.webhook_url:
            return
        try:
            requests.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            print(f"Discord Notify Error: {e}")
