import requests
import datetime

class DiscordNotifier:
    def __init__(self, config):
        # Ensure we handle the ${VAR} or direct string from your settings.yaml
        webhook = config['discord']['webhook_url']
        self.webhook_url = os.getenv(webhook.replace("${", "").replace("}", "")) if "${" in webhook else webhook

    def send_signal(self, symbol, signal_type, risk_data, session):
        """Sends a high-priority trade signal alert with session info."""
        color = 3066993 if "BUY" in signal_type else 15158332
        payload = {
            "embeds": [{
                "title": f"🚀 NEW SIGNAL: {symbol}",
                "description": f"**Action:** {signal_type}\n**Session:** {session}",
                "color": color,
                "fields": [
                    {"name": "Entry", "value": f"`{risk_data['entry']}`", "inline": True},
                    {"name": "Stop Loss", "value": f"`{risk_data['sl']}`", "inline": True},
                    {"name": "Take Profit", "value": f"`{risk_data['tp']}`", "inline": True}
                ],
                "footer": {"text": f"Delphi Oracle v1.1 | {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')} UTC"}
            }]
        }
        requests.post(self.webhook_url, json=payload)

    def send_heartbeat(self, active_signals, session):
        """
        Sends a heartbeat with current market scans and price levels.
        'active_signals' should now be a list of dicts: 
        [{'symbol': 'EURUSD', 'type': 'SELL', 'entry': 1.08, 'sl': 1.09, 'tp': 1.07}, ...]
        """
        color = 9807270 
        
        # Build a detailed string for each active signal
        formatted_signals = []
        for sig in active_signals:
            line = (f"🔥 **{sig['symbol']}**: {sig['type']}\n"
                    f"└ `ENT: {sig['entry']}` | `SL: {sig['sl']}` | `TP: {sig['tp']}`")
            formatted_signals.append(line)
        
        # Fallback if no signals are active
        description_text = "\n\n".join(formatted_signals) if formatted_signals else "📡 Scanning markets... No setups found."

        payload = {
            "embeds": [{
                "title": "💓 System Heartbeat",
                "description": f"**Active Session:** {session}\n\n**Market Scan:**\n{description_text}",
                "color": color,
                "footer": {"text": f"Status: Active | Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M')} UTC"}
            }]
        }
        requests.post(self.webhook_url, json=payload)
