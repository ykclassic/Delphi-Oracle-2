
def __init__(self, config):
        # Reach into the 'discord' dictionary to find 'webhook_url'
        # This matches your settings.yaml and main.py logic
        self.webhook_url = config.get('discord', {}).get('webhook_url')
        self.bot_name = config.get('bot_name', 'Delphi Oracle')

        # Extra safety: If the environment variable didn't swap the placeholder
        if self.webhook_url and ("${" in self.webhook_url or self.webhook_url == "EMPTY"):
            self.webhook_url = None
