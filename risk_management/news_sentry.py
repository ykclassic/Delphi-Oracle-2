import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

class NewsSentry:
    def __init__(self, config):
        self.config = config
        self.buffer_min = config.get('news_buffer_before', 30)
        # Using a reliable 2026-compliant free endpoint for economic data
        self.api_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

    def is_market_volatile(self, symbol):
        """
        Checks if a high-impact news event for the currency pair is near.
        Example: If symbol is EURUSD, it checks for EUR and USD news.
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            if response.status_code != 200:
                return False
            
            events = response.json()
            now = datetime.now(timezone.utc)
            
            # Extract relevant currencies for the symbol
            # (e.g., EURUSD -> ['EUR', 'USD'])
            currencies = [symbol[:3], symbol[3:]]
            if symbol == "XAUUSD":
                currencies = ["USD"] # Gold is primarily moved by USD news

            for event in events:
                if event['impact'] in self.config.get('impact_levels', ['High']):
                    if event['country'] in currencies:
                        # Parse event time (Format: "Mar 10, 2026 8:30pm")
                        event_time = datetime.strptime(f"{event['date']} {event['time']}", "%b %d, %Y %I:%M%p").replace(tzinfo=timezone.utc)
                        
                        time_diff = abs((event_time - now).total_seconds() / 60)
                        
                        if time_diff <= self.buffer_min:
                            return True # Block trade
            return False
        except Exception as e:
            # If news API fails, we default to 'Safe' but log the error
            print(f"News Sentry Error: {e}")
            return False
